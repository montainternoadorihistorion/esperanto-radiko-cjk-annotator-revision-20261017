"""Approved foam/bulb sharing, safe old alias and edition-specific inverse owners."""
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
def index(edition):return app.build_mapping_index_cached(app.effective_mapping_records(edition,app.load_dictionary_source(edition)))
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_current_adopted_owners_safe_alias_and_shared_characters(suffix):
    for body,root in [('泡','ŝaŭm'),('泡ᴬ','ampol'),('沫','ŝaŭm'),('够','sufiĉ'),('泡ᴮ','bobel'),('泡ᴱ','efervesk'),('泡ᴵ','infuz'),('泡ᴮᴸ','blaz'),('脓泡','pustul'),('泡疹','herpet')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==root+suffix
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_original_owners(suffix):
    for body,root in [('泡','ampol'),('沫','ŝaŭm'),('够','sufiĉ'),('泡ᴮ','bobel'),('泡ᴱ','efervesk'),('泡ᴵ','infuz'),('泡ᴮᴸ','blaz'),('脓泡','pustul'),('泡疹','herpet')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('泡ᴬ'+suffix,index(LEGACY))=='泡ᴬ'+suffix

def test_long_identifier_boundaries():
    for edition in (CURRENT,LEGACY):
        idx=index(edition);flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
        for body in ('泡','泡ᴬ','泡ᴮ','泡ᴮᴸ','沫','够'):
            for tail in app._IDENTIFIER_CONTINUATION_CHARS:
                key=body+tail;got=app.convert_kanji_esperanto_to_alphabet(key+'o',idx)
                if key in flat:assert got==flat[key]+'o'
                else:assert got==key+'o',(edition,key,got)
    assert app.convert_kanji_esperanto_to_alphabet('泡ᴬᴬo',index(CURRENT))=='泡ᴬᴬo'

def test_generator_only_adds_safe_old_ŝaŭm_key():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,root='ŝaŭm':dict(body=body,sourceRoot=root)
    assert [r['kanji'] for r in rows([item('沫')])]==['沫']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('泡')])}=={'沫','泡'}
    assert len(rows([item('泡'),item('沫')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('泡'),item('沫','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('泡'),item('泡')])
    assert [r['kanji'] for r in rows([item('泡ᴬ','ampol')])]==['泡ᴬ']

def test_custom_mapping_is_not_overwritten():
    df=pd.DataFrame([('own','泡','0'),('other','泡ᴬ','0'),('old','沫','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('泡o 泡ᴬo 沫o',idx)=='owno othero oldo'
@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_recovers_original_despite_changed_plain_key_owner(edition,mode):
    pairs=[('ŝaŭm','泡' if edition=='current' else '沫'),('ampol','泡ᴬ' if edition=='current' else '泡')]
    content='  '.join('<ruby>'+(display+'<rt>'+root if mode=='kanji' else root+'<rt>'+('泡' if root=='ŝaŭm' else '電球;アンプル'))+'</rt></ruby>o' for root,display in pairs)
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-15T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 泡o</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='ŝaŭmo  ampolo\n<literal> & 泡o'
    assert result['assignment_edition']==edition

def test_current_revision_and_explicit_owner_transfer():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='strob-miceli-bradip-20261125'
    assert source['current_item_count']==10640 and source['current_csv_count']==10775
    assert source['reverse_only_aliases']['沫']=='ŝaŭm' and source['reverse_only_aliases']['聪']=='inteligent'
    assert '泡' not in source['reverse_only_aliases']
    assert source['ownership_transfers']['泡']=={'old':'ampol','current':'ŝaŭm','old_profile':LEGACY}


def test_unknown_compound_identifiers_preserve_existing_fallback_rules():
    # Unknown IDs on a whole compound already fall back to component matches.
    # The approved new component owner/key affects this fallback; no short
    # identifier may swallow a longer continuation.
    for text,current,legacy in [
        ('脓泡ᴬo','pusampolo','pus泡ᴬo'),
        ('泡疹ᴬo','ŝaŭm疹ᴬo','ampol疹ᴬo'),
        ('泡ᴬᴬo','泡ᴬᴬo','泡ᴬᴬo'),
        ('泡ᴮᴸo','blazo','blazo'),
        ('脓泡o','pustulo','pustulo'),
        ('泡疹o','herpeto','herpeto'),
    ]:
        assert app.convert_kanji_esperanto_to_alphabet(text,index(CURRENT))==current
        assert app.convert_kanji_esperanto_to_alphabet(text,index(LEGACY))==legacy
