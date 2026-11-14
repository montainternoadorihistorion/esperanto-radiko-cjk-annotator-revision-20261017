"""Adopted gajn/sor, unambiguous old keys, fixed legacy and identifier boundaries."""
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
def test_current_new_and_safe_old_keys_and_unchanged_shared_owners(suffix):
    for body,root in [('获ᴳ','gajn'),('赢','gajn'),('升ˢ','sor'),('腾','sor'),('胞ˢ','sor'),('获','akir'),('获ᴿ','rikolt'),('获ᴼ','obten'),('升','litr'),('升ᴴ','his'),('升ᴰ','dies'),('升ᴾ','promoci'),('升ᴾⱽ','parvenu'),('揉','kned'),('揉ᵀ','taŭz'),('停','halt'),('停ᴷ','kape'),('停ˢ','suspend'),('停ˢᵀ','stop'),('摩','masaĝ'),('揉ᴹ','masaĝ'),('歇','paŭz'),('停ᴾ','paŭz'),('智ᴵᴳ','inteligent'),('洪','inund'),('洪ᴰ','diluv')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==root+suffix
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_original_keys_and_shared_owners(suffix):
    for body,root in [('赢','gajn'),('腾','sor'),('胞ˢ','sor'),('获','akir'),('获ᴿ','rikolt'),('获ᴼ','obten'),('升','litr'),('升ᴴ','his'),('升ᴰ','dies'),('升ᴾ','promoci'),('升ᴾⱽ','parvenu'),('揉','kned'),('揉ᵀ','taŭz'),('停','halt'),('停ᴷ','kape'),('停ˢ','suspend'),('停ˢᵀ','stop'),('洪','diluv'),('聪','inteligent')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==root+suffix
    for body in ('获ᴳ','升ˢ'):
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==body+suffix

def test_unknown_long_identifiers_do_not_consume_shorter_prefixes():
    for edition in (CURRENT,LEGACY):
        idx=index(edition);flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
        for body in ('获ᴳ','赢','升ˢ','腾','获','获ᴿ','获ᴼ','升','升ᴴ','升ᴰ','升ᴾ','升ᴾⱽ'):
            for tail in app._IDENTIFIER_CONTINUATION_CHARS:
                key=body+tail;got=app.convert_kanji_esperanto_to_alphabet(key+'o',idx)
                if key in flat:assert got==flat[key]+'o'
                else:assert got==key+'o',(edition,key,got)
    for body in ('获ᴳᴺ','升ˢᴿ'):
        assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(CURRENT))==body+'o'

@pytest.mark.parametrize('root,new,old',[('gajn','获ᴳ','赢'),('sor','升ˢ','腾')])
def test_generator_only_adds_reviewed_safe_old_key(root,new,old):
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,owner=root:dict(body=body,sourceRoot=owner)
    assert [r['kanji'] for r in rows([item(old)])]==[old]
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item(new)])}=={old,new}
    assert len(rows([item(new),item(old)]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item(new),item(old,'other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item(new),item(new)])

def test_custom_dictionary_is_not_overwritten():
    df=pd.DataFrame([('own','获ᴳ','0'),('other','升ˢ','0'),('old1','赢','0'),('old2','腾','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('获ᴳo 升ˢo 赢o 腾o',idx)=='owno othero old1o old2o'
@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_preserves_recorded_source_spaces_and_protected_text(edition,mode):
    pairs=[('gajn','获ᴳ' if edition=='current' else '赢'),('sor','升ˢ' if edition=='current' else '腾')]
    content='  '.join('<ruby>'+(display+'<rt>'+root if mode=='kanji' else root+'<rt>注釈')+'</rt></ruby>o' for root,display in pairs)
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-14T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 赢 腾</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='gajno  soro\n<literal> & 赢 腾'
    assert result['assignment_edition']==edition

def test_revision_adds_no_new_owner_transfer_or_third_edition():
    for edition in (CURRENT,LEGACY):
        records=app.effective_mapping_records(edition,app.load_dictionary_source(edition))
        assert [tuple(row) for row in records if row[1]=='胞ˢ']==[('sor','胞ˢ','1')]
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='sakristi-sambuk-svarm-20261114'
    assert source['current_item_count']==10640 and source['current_csv_count']==10697
    assert source['reverse_only_aliases']['赢']=='gajn' and source['reverse_only_aliases']['腾']=='sor'
    for body in ('赢','获','获ᴳ','腾','升','升ˢ'):assert body not in source['ownership_transfers']
    assert source['ownership_transfers']['洪']=={'old':'diluv','current':'inund','old_profile':LEGACY}
