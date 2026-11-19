"""Approved flan spelling, safe historical alias and longer pastry keys."""
from functools import lru_cache
import json
import pandas as pd
import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html
CURRENT='pejvo-piv-20260620';LEGACY='pre-las-20261017'
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','igi','ant','ita')
SHARED={'饼':'tort','饼ᴮ':'biskvit','饼ᴾ':'pic','饼ⱽ':'vafl','饼ᴼ':'oblat','饼ᴷ':'kresp','饼ᴷᴷ':'kraken','饼ᴷˢ':'keks','圣饼':'hosti','蛋奶酥':'sufle'}
@lru_cache(maxsize=None)
def index(edition):return app.build_mapping_index_cached(app.effective_mapping_records(edition,app.load_dictionary_source(edition)))
@pytest.mark.parametrize('edition',(CURRENT,LEGACY))
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_new_old_and_longer_pastry_keys(edition,suffix):
    assert app.convert_kanji_esperanto_to_alphabet('蛋奶'+suffix,index(edition))=='flan'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('饼ᶠ'+suffix,index(edition))==('flan'+suffix if edition==CURRENT else '饼ᶠ'+suffix)
    for body,root in SHARED.items():assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(edition))==root+suffix
def test_long_identifier_does_not_consume_shorter_prefix():
    for edition in (CURRENT,LEGACY):
        idx=index(edition);flat={key:value for bucket in idx.by_length.values() for key,value in bucket.items()}
        for body in ('饼ᶠ',*SHARED):
            for tail in app._IDENTIFIER_CONTINUATION_CHARS:
                given=body+tail+'o';key=body+tail;got=app.convert_kanji_esperanto_to_alphabet(given,idx)
                if key in flat:assert got==flat[key]+'o'
                elif body.startswith('饼'):assert got==given
        for given in ('饼ᶠᴬo','饼ᶠᴷo','饼ᴷᴷᴬo','饼ᴷˢᴾo'):
            assert app.convert_kanji_esperanto_to_alphabet(given,idx)==given
@pytest.mark.parametrize('edition',(CURRENT,LEGACY))
def test_fruit_tart_compounds_and_longest_old_key(edition):
    idx=index(edition)
    assert app.convert_kanji_esperanto_to_alphabet('果o蛋奶o 蛋奶酥o 蛋奶o',idx)=='fruktoflano sufleo flano'
    if edition==CURRENT:assert app.convert_kanji_esperanto_to_alphabet('果o饼ᶠo 饼ᶠojn 蛋奶酥o',idx)=='fruktoflano flanojn sufleo'
def test_generator_safe_alias_is_conditional_and_conflicts_fail():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,root='flan':dict(body=body,sourceRoot=root)
    assert [r['kanji'] for r in rows([item('蛋奶')])]==['蛋奶']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('饼ᶠ')])}=={'饼ᶠ','蛋奶'}
    assert len(rows([item('饼ᶠ'),item('蛋奶'),item('蛋奶酥','sufle')]))==3
    with pytest.raises(ValueError,match='conflicts'):rows([item('饼ᶠ'),item('蛋奶','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('饼ᶠ'),item('饼ᶠ')])
def test_new_complete_key_in_unregistered_compound_is_explicit():
    assert app.convert_kanji_esperanto_to_alphabet('圣饼o',index(CURRENT))=='hostio'
    assert app.convert_kanji_esperanto_to_alphabet('圣饼ᶠo',index(CURRENT))=='sanktflano'
    assert app.convert_kanji_esperanto_to_alphabet('圣饼ᶠo',index(LEGACY))=='sankt饼ᶠo'
    assert app.convert_kanji_esperanto_to_alphabet('饼ᶠᴬo',index(CURRENT))=='饼ᶠᴬo'
def test_custom_input_stays_user_defined():
    df=pd.DataFrame([('own','饼ᶠ','0'),('old','蛋奶','0'),('long','蛋奶酥','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('饼ᶠo 蛋奶酥o 蛋奶o',idx)=='owno longo oldo'
@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_html_source_spaces_protected_characters_and_compound(edition,mode):
    body='饼ᶠ' if edition=='current' else '蛋奶'
    content='<ruby>'+('果<rt>frukt' if mode=='kanji' else 'frukt<rt>果実')+'</rt></ruby>o<ruby>'+(body+'<rt>flan' if mode=='kanji' else 'flan<rt>タルト')+'</rt></ruby>o'
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-18T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n  &lt;literal&gt; &amp; 蛋奶 饼ᶠ</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='fruktoflano\n  <literal> & 蛋奶 饼ᶠ'
    assert result['assignment_edition']==edition
def test_current_metadata_keeps_two_editions_and_existing_owners():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='duk-20261120' and source['current_csv_count']==10711 and source['current_item_count']==10640
    assert source['reverse_only_aliases']['蛋奶']=='flan'
    assert not ({'饼ᶠ','蛋奶','蛋奶酥'} & source['ownership_transfers'].keys())
    assert source['ownership_transfers']['绘']=={'old':'desegn','current':'piktur','old_profile':LEGACY}
