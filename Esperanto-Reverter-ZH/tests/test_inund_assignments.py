"""Explicitly adopted flood-character sharing and edition-specific inverse owners."""
import json
import pandas as pd
import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html
CURRENT='pejvo-piv-20260620';LEGACY='pre-las-20261017'
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','igi','ant','ita')
def index(edition):return app.build_mapping_index_cached(app.effective_mapping_records(edition,app.load_dictionary_source(edition)))
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_current_adopted_owners_safe_alias_and_preserved_inteligent(suffix):
    for body,root in [('洪','inund'),('洪ᴰ','diluv'),('淹','inund'),('智ᴵᴳ','inteligent'),('聪','inteligent'),('智','saĝ'),('智ᴵ','intelekt'),('智ˢᴾ','sprit')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==root+suffix
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_original_owners(suffix):
    for body,root in [('洪','diluv'),('淹','inund'),('聪','inteligent'),('智','saĝ'),('智ᴵ','intelekt'),('智ˢᴾ','sprit')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('洪ᴰ'+suffix,index(LEGACY))=='洪ᴰ'+suffix

def test_long_identifier_boundaries():
    for edition in (CURRENT,LEGACY):
        idx=index(edition);flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
        for body in ('洪','洪ᴰ','淹','智ᴵᴳ','聪'):
            for tail in app._IDENTIFIER_CONTINUATION_CHARS:
                key=body+tail;got=app.convert_kanji_esperanto_to_alphabet(key+'o',idx)
                if key in flat:assert got==flat[key]+'o'
                else:assert got==key+'o',(edition,key,got)
    assert app.convert_kanji_esperanto_to_alphabet('洪ᴰᴸo',index(CURRENT))=='洪ᴰᴸo'

def test_generator_only_adds_safe_old_inund_key():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,root='inund':dict(body=body,sourceRoot=root)
    assert [r['kanji'] for r in rows([item('淹')])]==['淹']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('洪')])}=={'淹','洪'}
    assert len(rows([item('洪'),item('淹')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('洪'),item('淹','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('洪'),item('洪')])
    assert [r['kanji'] for r in rows([item('洪ᴰ','diluv')])]==['洪ᴰ']

def test_custom_mapping_is_not_overwritten():
    df=pd.DataFrame([('own','洪','0'),('other','洪ᴰ','0'),('old','淹','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('洪o 洪ᴰo 淹o',idx)=='owno othero oldo'
@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_recovers_original_despite_changed_plain_key_owner(edition,mode):
    pairs=[('inund','洪' if edition=='current' else '淹'),('diluv','洪ᴰ' if edition=='current' else '洪')]
    content='  '.join('<ruby>'+(display+'<rt>'+root if mode=='kanji' else root+'<rt>水に覆われる')+'</rt></ruby>o' for root,display in pairs)
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-13T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 洪o</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='inundo  diluvo\n<literal> & 洪o'
    assert result['assignment_edition']==edition

def test_current_revision_and_explicit_owner_transfer():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='sakristi-sambuk-svarm-20261114'
    assert source['current_item_count']==10640 and source['current_csv_count']==10697
    assert source['reverse_only_aliases']['淹']=='inund' and source['reverse_only_aliases']['聪']=='inteligent'
    assert '洪' not in source['reverse_only_aliases']
    assert source['ownership_transfers']['洪']=={'old':'diluv','current':'inund','old_profile':LEGACY}
