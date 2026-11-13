"""Approved noodle/axis assignments; deliberate ownership transfer and two editions."""
import json
import pandas as pd
import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'; LEGACY='pre-las-20261017'
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','igi','ant','ita')

def index(edition):
    return app.build_mapping_index_cached(app.effective_mapping_records(edition,app.load_dictionary_source(edition)))

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_current_ownership_and_safe_complete_former_keys(suffix):
    idx=index(CURRENT)
    for key,root in [('细面','vermiĉel'),('粉丝','vermiĉel'),('轴ᴾ','pivot'),('旋ᴾ','piruet'),('旋ᴾᴿ','piruet'),
                     ('轴','aks'),('轴ˢ̂','ŝaft'),('百叶窗','ŝutr'),('细面ᴺ','delikatnudel')]:
        assert app.convert_kanji_esperanto_to_alphabet(key+suffix,idx)==root+suffix

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_remains_the_original_edition(suffix):
    idx=index(LEGACY)
    for key,root in [('粉丝','vermiĉel'),('旋ᴾ','pivot'),('旋ᴾᴿ','piruet'),('细面','delikatfac'),('细面ᴺ','delikatnudel')]:
        assert app.convert_kanji_esperanto_to_alphabet(key+suffix,idx)==root+suffix

def test_long_identifiers_do_not_match_a_shorter_assignment():
    current=index(CURRENT);legacy=index(LEGACY)
    flat={k:v for bucket in current.by_length.values() for k,v in bucket.items()}
    for body,root in [('细面','vermiĉel'),('轴ᴾ','pivot'),('旋ᴾ','piruet'),('旋ᴾᴿ','piruet')]:
        for tail in app._IDENTIFIER_CONTINUATION_CHARS:
            key=body+tail; got=app.convert_kanji_esperanto_to_alphabet(key+'o',current)
            if key in flat: assert got==flat[key]+'o'
            else: assert not got.startswith(root),(key,got)
    for tail in ('ᴺ','ᴺᴿ','ᴺᶠ'):
        assert app.convert_kanji_esperanto_to_alphabet('细面'+tail+'o',current)==app.convert_kanji_esperanto_to_alphabet('细面'+tail+'o',legacy)
    assert app.convert_kanji_esperanto_to_alphabet('旋ᴾᴿo',current)=='pirueto'
    assert app.convert_kanji_esperanto_to_alphabet('旋ᴾᴿᴬo',current)!='pirueto'

def test_generator_aliases_are_conditional_unicode_safe_and_conflict_safe():
    for raw,unicode,new,old in [('vermic^el','vermiĉel','细面','粉丝'),('piruet','piruet','旋ᴾ','旋ᴾᴿ')]:
        rows=lambda items:rows_from_all_json({'items':items})
        item=lambda body,root=raw:dict(sourceRoot=root,body=body)
        assert [(x['kanji'],x['esperanto']) for x in rows([item(old)])]==[(old,unicode)]
        assert {x['kanji'] for x in rows([item(new)])}=={new,old}
        assert len(rows([item(new),item(old)]))==2
        with pytest.raises(ValueError,match='conflicts'):rows([item(new),item(old,'other')])
        with pytest.raises(ValueError,match='Expected one'):rows([item(new),item(new)])
    assert {r['kanji'] for r in rows_from_all_json({'items':[{'sourceRoot':'pivot','body':'轴ᴾ'}]})}=={'轴ᴾ'}

def test_custom_dictionary_owners_are_not_replaced_by_bundled_assignments():
    df=pd.DataFrame([('custom','细面','0'),('customaxis','轴ᴾ','0'),('oldpivot','旋ᴾ','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('细面o 轴ᴾo 旋ᴾo',idx)=='customo customaxiso oldpivoto'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_source_recovery_uses_recorded_source_not_new_dictionary_owner(edition,mode):
    pairs=[('vermiĉel','细面' if edition=='current' else '粉丝'),('pivot','轴ᴾ' if edition=='current' else '旋ᴾ'),('piruet','旋ᴾ' if edition=='current' else '旋ᴾᴿ')]
    content='  '.join('<ruby>'+ (display+'<rt>'+root if mode=='kanji' else root+'<rt>注釈')+'</rt></ruby>o' for root,display in pairs)
    text='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-12T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 旋ᴾo</p></body></html>'
    recovered=recover_standard_html(text,mode)
    assert recovered['text']=='vermiĉelo  pivoto  pirueto\n<literal> & 旋ᴾo'
    assert recovered['assignment_edition']==edition

def test_reviewed_current_source_metadata_and_no_third_edition():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='inteligent-20261113'
    assert source['current_item_count']==10640 and source['current_csv_count']==10689
    assert source['reverse_only_aliases']['粉丝']=='vermiĉel'
    assert source['reverse_only_aliases']['旋ᴾᴿ']=='piruet'
    assert '旋ᴾ' not in source['reverse_only_aliases']
