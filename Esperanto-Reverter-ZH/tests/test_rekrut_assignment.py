"""Approved rekrut display, old alias and the accepted compositional ambiguity."""
import json
from functools import lru_cache
import pandas as pd
import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html
CURRENT='pejvo-piv-20260620';LEGACY='pre-las-20261017'
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','igi','ant','ita')
@lru_cache(maxsize=2)
def records(edition):return app.effective_mapping_records(edition,app.load_dictionary_source(edition))
@lru_cache(maxsize=2)
def index(edition):return app.build_mapping_index_cached(records(edition))

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_new_display_old_alias_and_fixed_legacy(suffix):
    assert app.convert_kanji_esperanto_to_alphabet('新兵'+suffix,index(CURRENT))=='rekrut'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('征募'+suffix,index(CURRENT))=='rekrut'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('征募'+suffix,index(LEGACY))=='rekrut'+suffix
    # The old profile keeps the former composition; its assignments never change.
    assert app.convert_kanji_esperanto_to_alphabet('新兵'+suffix,index(LEGACY))=='novsoldat'+suffix

def test_shared_components_and_previous_ego_aliases_are_not_reassigned():
    pairs=[('新','nov'),('兵','soldat'),('吾','ego'),('己ᴱ','egoist')]
    for edition in (CURRENT,LEGACY):
        for body,root in pairs:
            assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(edition))==root+'o'
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱo 我ᴱ家o 吾家o',index(CURRENT))=='egoo egoisto egoisto'

def test_new_key_does_not_match_inside_longer_identifiers():
    current=index(CURRENT)
    previous=app.build_mapping_index_cached(tuple(r for r in records(CURRENT) if r[1]!='新兵'))
    flat={k:v for bucket in current.by_length.values() for k,v in bucket.items()}
    for tail in app._IDENTIFIER_CONTINUATION_CHARS:
        text='新兵'+tail+'o'
        if '新兵'+tail not in flat:
            assert app.convert_kanji_esperanto_to_alphabet(text,current)==app.convert_kanji_esperanto_to_alphabet(text,previous)

def test_generator_retains_alias_only_for_approved_current_assignment():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,owner='rekrut':dict(body=body,sourceRoot=owner)
    assert [r['kanji'] for r in rows([item('征募')])]==['征募']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('新兵')])}=={'新兵','征募'}
    assert len(rows([item('新兵'),item('征募')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('新兵'),item('征募','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('新兵'),item('新兵')])

def test_custom_dictionary_keeps_its_own_mappings():
    df=pd.DataFrame([('own','新兵','0'),('other','征募','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('新兵o 征募o',idx)=='owno othero'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_retains_rekrut_and_compositional_originals(edition,mode):
    body='新兵' if edition=='current' else '征募'
    content='<ruby>'+(body+'<rt>rekrut' if mode=='kanji' else 'rekrut<rt>新兵;新加入者')+'</rt></ruby>o'
    for source,display in [('nov','新'),('soldat','兵')]:
        content+='<ruby>'+(display+'<rt>'+source if mode=='kanji' else source+'<rt>'+display)+'</rt></ruby>'
    content+='o'
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-15T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 新兵 征募</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='rekrutonovsoldato\n<literal> & 新兵 征募'
    assert result['assignment_edition']==edition

def test_source_records_the_new_key_without_claiming_existing_owner_transfer():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['assignment_changes']['rekrut']=={'old':'征募','current':'新兵'}
    assert source['reverse_only_aliases']['征募']=='rekrut'
    assert '新兵' not in source['ownership_transfers'] and '征募' not in source['ownership_transfers']
    adoption=json.loads((app.ROOT/'data/rekrut_20261115.json').read_bytes())
    assert adoption['accepted_compositional_ambiguity']=={'display':'新兵o','before':'novsoldato','current':'rekruto','fixed_legacy':'novsoldato'}
