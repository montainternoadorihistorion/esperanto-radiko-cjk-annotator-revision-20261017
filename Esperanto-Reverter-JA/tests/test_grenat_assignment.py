"""Approved grenat display, old alias and the accepted compositional ambiguity."""
import json
from functools import lru_cache
import pandas as pd
import pytest
import esperanto_converter as app
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
    assert app.convert_kanji_esperanto_to_alphabet('榴石'+suffix,index(CURRENT))=='grenat'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('石榴'+suffix,index(CURRENT))=='grenat'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('石榴'+suffix,index(LEGACY))=='grenat'+suffix
    # The old profile keeps the former composition; its assignments never change.
    assert app.convert_kanji_esperanto_to_alphabet('榴石'+suffix,index(LEGACY))=='granatŝton'+suffix

def test_shared_components_and_previous_ego_aliases_are_not_reassigned():
    pairs=[('榴','granat'),('榴ᴾ','punik'),('石','ŝton'),('征募','rekrut'),('吾','ego'),('己ᴱ','egoist')]
    for edition in (CURRENT,LEGACY):
        for body,root in pairs:
            assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(edition))==root+'o'
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱo 我ᴱ家o 吾家o',index(CURRENT))=='egoo egoisto egoisto'
    assert app.convert_kanji_esperanto_to_alphabet('新兵o',index(CURRENT))=='rekruto'
    assert app.convert_kanji_esperanto_to_alphabet('新兵o',index(LEGACY))=='novsoldato'

def test_new_key_does_not_match_inside_longer_identifiers():
    current=index(CURRENT)
    previous=app.build_mapping_index_cached(tuple(r for r in records(CURRENT) if r[1]!='榴石'))
    flat={k:v for bucket in current.by_length.values() for k,v in bucket.items()}
    for tail in app._IDENTIFIER_CONTINUATION_CHARS:
        text='榴石'+tail+'o'
        if '榴石'+tail not in flat:
            assert app.convert_kanji_esperanto_to_alphabet(text,current)==app.convert_kanji_esperanto_to_alphabet(text,previous)
    for given,wanted in [('榴石ᴬo','granatagrostemo'),('榴石ᴸᵀo','granatlito'),('榴石ᴬᴬo','granat石ᴬᴬo')]:
        assert app.convert_kanji_esperanto_to_alphabet(given,current)==wanted
        assert app.convert_kanji_esperanto_to_alphabet(given,index(LEGACY))==wanted

def test_generator_retains_alias_only_for_approved_current_assignment():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,owner='grenat':dict(body=body,sourceRoot=owner)
    assert [r['kanji'] for r in rows([item('石榴')])]==['石榴']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('榴石')])}=={'榴石','石榴'}
    assert len(rows([item('榴石'),item('石榴')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('榴石'),item('石榴','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('榴石'),item('榴石')])

def test_custom_dictionary_keeps_its_own_mappings():
    df=pd.DataFrame([('own','榴石','0'),('other','石榴','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('榴石o 石榴o',idx)=='owno othero'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_retains_grenat_and_compositional_originals(edition,mode):
    body='榴石' if edition=='current' else '石榴'
    content='<ruby>'+(body+'<rt>grenat' if mode=='kanji' else 'grenat<rt>ガーネット;柘榴石')+'</rt></ruby>o'
    for source,display in [('granat','榴'),('ŝton','石')]:
        content+='<ruby>'+(display+'<rt>'+source if mode=='kanji' else source+'<rt>'+display)+'</rt></ruby>'
    content+='o'
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-15T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 榴石 石榴</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='grenatogranatŝtono\n<literal> & 榴石 石榴'
    assert result['assignment_edition']==edition

def test_source_records_the_new_key_without_claiming_existing_owner_transfer():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['assignment_changes']['grenat']=={'old':'石榴','current':'榴石'}
    assert source['reverse_only_aliases']['石榴']=='grenat'
    assert '榴石' not in source['ownership_transfers'] and '石榴' not in source['ownership_transfers']
    adoption=json.loads((app.ROOT/'data/grenat_20261115.json').read_bytes())
    assert adoption['accepted_compositional_ambiguity']=={'display':'榴石o','before':'granatŝtono','current':'grenato','fixed_legacy':'granatŝtono'}
