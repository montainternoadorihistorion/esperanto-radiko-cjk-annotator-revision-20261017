"""Approved root-level drawing/art distinction and explicit current owner transfer."""
import json
from functools import lru_cache
import pandas as pd
import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html
CURRENT='pejvo-piv-20260620';LEGACY='pre-las-20261017'
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','aĵo','ado','ant','ita')
@lru_cache(maxsize=2)
def index(edition):return app.build_mapping_index_cached(app.effective_mapping_records(edition,app.load_dictionary_source(edition)))

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_root_assignments_are_kept_across_endings_and_derivatives(suffix):
    assert app.convert_kanji_esperanto_to_alphabet('描'+suffix,index(CURRENT))=='pentr'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('描ᴰ'+suffix,index(CURRENT))=='desegn'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('绘'+suffix,index(CURRENT))=='piktur'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('描ᴾᴷ'+suffix,index(CURRENT))=='piktur'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('描'+suffix,index(LEGACY))=='pentr'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('绘'+suffix,index(LEGACY))=='desegn'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('描ᴾᴷ'+suffix,index(LEGACY))=='piktur'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('描ᴰ'+suffix,index(LEGACY))=='描ᴰ'+suffix

@pytest.mark.parametrize('edition',[CURRENT,LEGACY])
def test_known_and_unknown_identifier_boundaries_and_other_keys(edition):
    for body in ('描ᴰᴬ','描ᴾ','描ᴾᴷᴬ','绘ᴬ','绘ᴰ','描ᴰᴾᴷ'):
        assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(edition))==body+'o'
    for body,root in [('浮世绘','ukij'),('足数','kvorum'),('吾','ego'),('己ᴱ','egoist'),('沫','ŝaŭm')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(edition))==root+'o'
    assert app.convert_kanji_esperanto_to_alphabet('够数o 泡o 泡ᴬo',index(edition))==('kvorumo ŝaŭmo ampolo' if edition==CURRENT else 'sufiĉnombro ampolo 泡ᴬo')

def test_generator_retains_only_the_safe_alias_and_rejects_conflicts():
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,owner='piktur':dict(body=body,sourceRoot=owner)
    assert [r['kanji'] for r in rows([item('描ᴾᴷ')])]==['描ᴾᴷ']
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item('绘')])}=={'绘','描ᴾᴷ'}
    assert len(rows([item('绘'),item('描ᴾᴷ')]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item('绘'),item('描ᴾᴷ','other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item('绘'),item('绘')])
    # An old/custom source with 绘 owned by desegn is never rewritten.
    assert rows([item('绘','desegn')])[0]['esperanto']=='desegn'

def test_custom_dictionary_remains_in_control_of_its_own_owners():
    df=pd.DataFrame([('own','绘','0'),('other','描ᴰ','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('绘o 描ᴰo',idx)=='owno othero'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_original_bearing_html_preserves_all_roots_and_protected_text(edition,mode):
    pairs=[('pentr','描'),('desegn','描ᴰ' if edition=='current' else '绘'),('piktur','绘' if edition=='current' else '描ᴾᴷ')]
    content=' '.join('<ruby>'+(display+'<rt>'+root if mode=='kanji' else root+'<rt>絵を描く')+'</rt></ruby>o' for root,display in pairs)
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-16T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 描ᴾᴷ 绘</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='pentro desegno pikturo\n<literal> & 描ᴾᴷ 绘'
    assert result['assignment_edition']==edition

def test_manifest_records_accepted_bare_owner_change_and_safe_alias():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['assignment_changes']['desegn']=={'old':'绘','current':'描ᴰ'}
    assert source['assignment_changes']['piktur']=={'old':'描ᴾᴷ','current':'绘'}
    assert source['reverse_only_aliases']['描ᴾᴷ']=='piktur'
    assert '绘' not in source['reverse_only_aliases']
    assert source['ownership_transfers']['绘']=={'old':'desegn','current':'piktur','old_profile':LEGACY}
    adoption=json.loads((app.ROOT/'data/desegn_piktur_20261116.json').read_bytes())
    assert adoption['fixed_legacy_unchanged'] and adoption['new_edition_profiles']==0
