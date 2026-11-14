"""Approved ego/egoist displays, old aliases and identifier boundaries."""
import json
from functools import lru_cache
import pandas as pd
import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html
CURRENT='pejvo-piv-20260620';LEGACY='pre-las-20261017'
CHANGES=[('ego','我ᴱ','吾'),('egoist','我ᴱ家','己ᴱ')]
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','igi','ant','ita')
SHARED=[('我','mi'),('我ᴬ','atm'),('我们','ni'),('己','si'),('己ᴾ','propr'),('己ᴾᵀ','propriet'),('家','ist'),('叶绿','klorofil')]
@lru_cache(maxsize=2)
def records(edition):return app.effective_mapping_records(edition,app.load_dictionary_source(edition))
@lru_cache(maxsize=2)
def index(edition):return app.build_mapping_index_cached(records(edition))

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_current_new_safe_old_shared_owners_and_compositions(suffix):
    for body,root in SHARED+[(b,r) for r,n,o in CHANGES for b in (n,o)]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('吾家'+suffix,index(CURRENT))=='egoist'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱ家'+suffix,index(CURRENT))=='egoist'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱ主义'+suffix,index(CURRENT))=='egoism'+suffix

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_original_alias_and_owners(suffix):
    for body,root in SHARED+[(o,r) for r,n,o in CHANGES]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('吾家'+suffix,index(LEGACY))=='egoist'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱ'+suffix,index(LEGACY))=='我ᴱ'+suffix

def test_unknown_long_identifier_does_not_newly_match_shorter_key():
    newrecords=records(CURRENT);newbodies={n for _,n,_ in CHANGES}
    previous=app.build_mapping_index_cached(tuple(r for r in newrecords if r[1] not in newbodies))
    current=index(CURRENT);flat={k:v for bucket in current.by_length.values() for k,v in bucket.items()}
    for body in newbodies|{'吾','己ᴱ','我','我ᴬ','叶绿'}:
        for tail in app._IDENTIFIER_CONTINUATION_CHARS:
            key=body+tail;given=key+'o'
            # A new bare ego prefix may correctly parse before a blocked unknown
            # suffix on 家; only the longest whole key must not swallow its ID.
            got=app.convert_kanji_esperanto_to_alphabet(given,current)
            if key in flat: assert got==flat[key]+'o'
            elif body=='我ᴱ家': assert got=='ego'+app.convert_kanji_esperanto_to_alphabet('家'+tail+'o',previous)
            else: assert got==app.convert_kanji_esperanto_to_alphabet(given,previous)
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱᴬo',current)=='我ᴱᴬo'
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱ家ᶠo',current)=='egofamilio'
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱ家ᴴo',current)=='egohejmo'

@pytest.mark.parametrize('root,new,old',CHANGES)
def test_generator_safe_old_alias_only_with_approved_current(root,new,old):
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,owner=root:dict(body=body,sourceRoot=owner)
    assert [r['kanji'] for r in rows([item(old)])]==[old]
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item(new)])}=={old,new}
    assert len(rows([item(new),item(old)]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item(new),item(old,'other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item(new),item(new)])

def test_custom_dictionary_owns_its_mappings():
    df=pd.DataFrame([('own','我ᴱ','0'),('other','吾','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱo 吾o',idx)=='owno othero'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_keeps_egoist_source_and_protected_characters(edition,mode):
    body='我ᴱ家' if edition=='current' else '吾家'
    content='<ruby>'+(body+'<rt>egoist' if mode=='kanji' else 'egoist<rt>利己主義者')+'</rt></ruby>o'
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-15T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 吾 我ᴱ</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='egoisto\n<literal> & 吾 我ᴱ'
    assert result['assignment_edition']==edition

def test_approved_source_metadata_keeps_two_editions_and_old_keys():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    for root,new,old in CHANGES:
        assert source['assignment_changes'][root]=={'old':old,'current':new}
        assert source['reverse_only_aliases'][old]==root
        assert old not in source['ownership_transfers'] and new not in source['ownership_transfers']
    assert source['ownership_transfers']['洪']=={'old':'diluv','current':'inund','old_profile':LEGACY}
