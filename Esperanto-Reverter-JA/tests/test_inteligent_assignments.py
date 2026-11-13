"""Adopted inteligent assignment, old compatibility, and unaffected shared identifiers."""
import json
import pandas as pd
import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html
CURRENT='pejvo-piv-20260620';LEGACY='pre-las-20261017'
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','igi','ant','ita')

def index(edition):return app.build_mapping_index_cached(app.effective_mapping_records(edition,app.load_dictionary_source(edition)))
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_current_new_key_safe_old_key_and_unchanged_owners(suffix):
    for body,root in [('智ᴵᴳ','inteligent'),('聪','inteligent'),('智','saĝ'),('智ᴵ','intelekt'),('智ˢᴾ','sprit'),('神智','teozof'),('淹','inund'),('洪','inund'),('洪ᴰ','diluv')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==root+suffix
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_original_owners(suffix):
    for body,root in [('聪','inteligent'),('智','saĝ'),('智ᴵ','intelekt'),('智ˢᴾ','sprit'),('淹','inund'),('洪','diluv')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('智ᴵᴳ'+suffix,index(LEGACY))=='智ᴵᴳ'+suffix

def test_identifier_continuations_do_not_consume_shorter_prefixes():
    for edition in (CURRENT,LEGACY):
        idx=index(edition);flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
        for body in ('智ᴵᴳ','聪','智ᴵ','智','智ˢᴾ'):
            for tail in app._IDENTIFIER_CONTINUATION_CHARS:
                key=body+tail;got=app.convert_kanji_esperanto_to_alphabet(key+'o',idx)
                if key in flat:assert got==flat[key]+'o'
                else:assert got==key+'o',(edition,key,got)
    assert app.convert_kanji_esperanto_to_alphabet('智ᴵᴳᴺo',index(CURRENT))=='智ᴵᴳᴺo'

def test_alias_generator_uses_reviewed_assignment_and_rejects_conflicts():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,root='inteligent':dict(body=body,sourceRoot=root)
    assert [r['kanji'] for r in rows([item('聪')])]==['聪']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('智ᴵᴳ')])}=={'聪','智ᴵᴳ'}
    assert len(rows([item('智ᴵᴳ'),item('聪')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('智ᴵᴳ'),item('聪','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('智ᴵᴳ'),item('智ᴵᴳ')])

def test_custom_mapping_is_not_overwritten():
    df=pd.DataFrame([('own','智ᴵᴳ','0'),('other','智ᴵ','0'),('old','聪','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('智ᴵᴳo 智ᴵo 聪o',idx)=='owno othero oldo'
@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_recorded_source_and_edition_are_preserved(edition,mode):
    display='智ᴵᴳ' if edition=='current' else '聪'
    content='<ruby>'+(display+'<rt>inteligent' if mode=='kanji' else 'inteligent<rt>賢い')+'</rt></ruby>a'
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-13T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n  '+content+'<br>\n&lt;literal&gt; &amp; 聪a</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='  inteligenta\n<literal> & 聪a'
    assert result['assignment_edition']==edition

def test_current_revision_no_ownership_transfer_or_extra_edition():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='masag-pauz-20261114'
    assert source['current_item_count']==10640 and source['current_csv_count']==10692
    assert source['reverse_only_aliases']['聪']=='inteligent'
    assert all(key not in source['ownership_transfers'] for key in ('智','智ᴵ','智ᴵᴳ','聪','淹'))
