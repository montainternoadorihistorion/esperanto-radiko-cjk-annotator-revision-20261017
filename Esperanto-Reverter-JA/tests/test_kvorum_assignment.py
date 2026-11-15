"""Approved kvorum display, old alias and the accepted compositional ambiguity."""
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
    assert app.convert_kanji_esperanto_to_alphabet('够数'+suffix,index(CURRENT))=='kvorum'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('足数'+suffix,index(CURRENT))=='kvorum'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('足数'+suffix,index(LEGACY))=='kvorum'+suffix
    # The old profile keeps the former composition; its assignments never change.
    assert app.convert_kanji_esperanto_to_alphabet('够数'+suffix,index(LEGACY))=='sufiĉnombr'+suffix

def test_shared_components_and_previous_ego_aliases_are_not_reassigned():
    pairs=[('够','sufiĉ'),('数','nombr'),('足','pied'),('榴','granat'),('榴ᴾ','punik'),('石','ŝton'),('征募','rekrut'),('吾','ego'),('己ᴱ','egoist')]
    for edition in (CURRENT,LEGACY):
        for body,root in pairs:
            assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(edition))==root+'o'
    assert app.convert_kanji_esperanto_to_alphabet('我ᴱo 我ᴱ家o 吾家o',index(CURRENT))=='egoo egoisto egoisto'
    assert app.convert_kanji_esperanto_to_alphabet('新兵o',index(CURRENT))=='rekruto'
    assert app.convert_kanji_esperanto_to_alphabet('新兵o',index(LEGACY))=='novsoldato'

def test_new_key_does_not_match_inside_longer_identifiers():
    current=index(CURRENT)
    previous=app.build_mapping_index_cached(tuple(r for r in records(CURRENT) if r[1]!='够数'))
    flat={k:v for bucket in current.by_length.values() for k,v in bucket.items()}
    for tail in app._IDENTIFIER_CONTINUATION_CHARS:
        text='够数'+tail+'o'
        if '够数'+tail not in flat:
            assert app.convert_kanji_esperanto_to_alphabet(text,current)==app.convert_kanji_esperanto_to_alphabet(text,previous)
    for given,wanted in [('够数ᴬo','sufiĉ数ᴬo'),('够数ᴸᵀo','sufiĉ数ᴸᵀo'),('够数ᴬᴬo','sufiĉ数ᴬᴬo')]:
        assert app.convert_kanji_esperanto_to_alphabet(given,current)==wanted
        assert app.convert_kanji_esperanto_to_alphabet(given,index(LEGACY))==wanted

def test_generator_retains_alias_only_for_approved_current_assignment():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,owner='kvorum':dict(body=body,sourceRoot=owner)
    assert [r['kanji'] for r in rows([item('足数')])]==['足数']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('够数')])}=={'够数','足数'}
    assert len(rows([item('够数'),item('足数')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('够数'),item('足数','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('够数'),item('够数')])

def test_custom_dictionary_keeps_its_own_mappings():
    df=pd.DataFrame([('own','够数','0'),('other','足数','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('够数o 足数o',idx)=='owno othero'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_retains_kvorum_and_compositional_originals(edition,mode):
    body='够数' if edition=='current' else '足数'
    content='<ruby>'+(body+'<rt>kvorum' if mode=='kanji' else 'kvorum<rt>定足数')+'</rt></ruby>o'
    for source,display in [('sufiĉ','够'),('nombr','数')]:
        content+='<ruby>'+(display+'<rt>'+source if mode=='kanji' else source+'<rt>'+display)+'</rt></ruby>'
    content+='o'
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-15T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 够数 足数</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='kvorumosufiĉnombro\n<literal> & 够数 足数'
    assert result['assignment_edition']==edition

def test_source_records_the_new_key_without_claiming_existing_owner_transfer():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['assignment_changes']['kvorum']=={'old':'足数','current':'够数'}
    assert source['reverse_only_aliases']['足数']=='kvorum'
    assert '够数' not in source['ownership_transfers'] and '足数' not in source['ownership_transfers']
    adoption=json.loads((app.ROOT/'data/kvorum_20261115.json').read_bytes())
    assert adoption['accepted_compositional_ambiguity']=={'display':'够数o','before':'sufiĉnombro','current':'kvorumo','fixed_legacy':'sufiĉnombro'}


def test_previous_saum_ampol_ownership_and_old_aliases_remain():
    for text,current,legacy in [
        ('沫o 泡o 泡ᴬo','ŝaŭmo ŝaŭmo ampolo','ŝaŭmo ampolo 泡ᴬo'),
        ('泡ᴮo 泡ᴮᴸo 泡ᴱo 泡ᴵo','bobelo blazo efervesko infuzo','bobelo blazo efervesko infuzo'),
        ('泡ᴬᴬo 泡ᴮᴸᴬo','泡ᴬᴬo 泡ᴮᴸᴬo','泡ᴬᴬo 泡ᴮᴸᴬo'),
        ('榴石o 石榴o','grenato grenato','granatŝtono grenato'),
    ]:
        assert app.convert_kanji_esperanto_to_alphabet(text,index(CURRENT))==current
        assert app.convert_kanji_esperanto_to_alphabet(text,index(LEGACY))==legacy
