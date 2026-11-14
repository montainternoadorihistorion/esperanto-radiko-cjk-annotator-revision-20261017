"""Reviewed admir/aprez ownership and original legacy protection."""
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
def test_current_adopted_owners_and_nonconflicting_old_key(suffix):
    for body,root in [('赏','admir'),('佩','admir'),('赏ᴬᴾ','aprez'),('赏ᴬᶜ','aprec'),('赏ᴳ','gratifik'),('赏ᴳᴿ','gratif'),('赏ᴳᶜ','gratifikaci')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==root+suffix
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_original_owners(suffix):
    for body,root in [('佩','admir'),('赏','aprez'),('赏ᴬᶜ','aprec')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==root+suffix
def test_identifier_continuations_do_not_consume_shorter_prefixes():
    for edition in (CURRENT,LEGACY):
        idx=index(edition);flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
        for body in ('赏','佩','赏ᴬᴾ','赏ᴬᶜ'):
            for tail in app._IDENTIFIER_CONTINUATION_CHARS:
                key=body+tail;got=app.convert_kanji_esperanto_to_alphabet(key+'o',idx)
                if key in flat:assert got==flat[key]+'o'
                else:assert got==key+'o',(edition,key,got)
    assert app.convert_kanji_esperanto_to_alphabet('赏ᴬᴾo',index(CURRENT))=='aprezo'
    assert app.convert_kanji_esperanto_to_alphabet('赏ᴬᴾᴿo',index(CURRENT))=='赏ᴬᴾᴿo'
def test_alias_generator_uses_reviewed_assignment_and_rejects_conflicts():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,root='admir':dict(body=body,sourceRoot=root)
    assert [r['kanji'] for r in rows([item('佩')])]==['佩']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('赏')])}=={'佩','赏'}
    assert len(rows([item('赏'),item('佩')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('赏'),item('佩','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('赏'),item('赏')])
    assert [r['kanji'] for r in rows([item('赏ᴬᴾ','aprez')])]==['赏ᴬᴾ']
def test_custom_mapping_is_not_overwritten():
    df=pd.DataFrame([('own','赏','0'),('ownid','赏ᴬᴾ','0'),('old','佩','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('赏o 赏ᴬᴾo 佩o',idx)=='owno ownido oldo'
@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_uses_recorded_source_while_plain_edition_owners_differ(edition,mode):
    pairs=[('admir','赏' if edition=='current' else '佩'),('aprez','赏ᴬᴾ' if edition=='current' else '赏')]
    content='  '.join('<ruby>'+(display+'<rt>'+root if mode=='kanji' else root+'<rt>注釈')+'</rt></ruby>o' for root,display in pairs)
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-13T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 赏o</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='admiro  aprezo\n<literal> & 赏o'
    assert result['assignment_edition']==edition
def test_current_revision_no_conflicting_alias_or_extra_edition():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='sakristi-sambuk-svarm-20261114'
    assert source['current_item_count']==10640 and source['current_csv_count']==10697
    assert source['reverse_only_aliases']['佩']=='admir'
    assert '赏' not in source['reverse_only_aliases']
    assert source['ownership_transfers']['赏']=={'old':'aprez','current':'admir','old_profile':LEGACY}
