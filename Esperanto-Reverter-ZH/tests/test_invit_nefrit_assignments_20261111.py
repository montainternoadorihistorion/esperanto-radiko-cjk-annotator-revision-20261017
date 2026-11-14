"""Approved invit and explicitly chosen mineral nefrit, with frozen legacy."""
import hashlib
import io
import json

import pandas as pd
import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import (
    current_rows_from_all_json, rows_from_all_json,
)
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'
LEGACY='pre-las-20261017'
MINERAL='软玉ᴺ'
MEDICAL='肾ᴺ炎ᵀ'
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','i','as','is','os','us','u','igi','ita')

def index(edition):
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, app.load_dictionary_source(edition)))

@pytest.mark.parametrize('suffix', SUFFIXES)
def test_new_invitation_and_both_nefrit_senses_restore_same_spelling(suffix):
    idx=index(CURRENT)
    for key,root in [('招','invit'),('邀','invit'),(MINERAL,'nefrit'),(MEDICAL,'nefrit'),('软玉','molgem'),('招魂','nekromanci')]:
        assert app.convert_kanji_esperanto_to_alphabet(key+suffix,idx)==root+suffix

@pytest.mark.parametrize('suffix', SUFFIXES)
def test_frozen_legacy_and_former_text_are_unchanged(suffix):
    idx=index(LEGACY)
    flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
    assert '招' not in flat and MINERAL not in flat
    for key,root in [('邀','invit'),(MEDICAL,'nefrit'),('肾炎','nefrit'),('软玉','molgem'),('招魂','nekromanci')]:
        assert app.convert_kanji_esperanto_to_alphabet(key+suffix,idx)==root+suffix

def test_identifier_boundaries_never_consume_part_of_longer_identifier():
    idx=index(CURRENT)
    flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
    for body,root in [('招','invit'),('邀','invit'),(MINERAL,'nefrit'),(MEDICAL,'nefrit')]:
        for tail in app._IDENTIFIER_CONTINUATION_CHARS:
            key=body+tail
            actual=app.convert_kanji_esperanto_to_alphabet(key+'o',idx)
            if key in flat: assert actual==flat[key]+'o'
            else: assert not actual.startswith(root),(key,actual)
    assert app.convert_kanji_esperanto_to_alphabet('招ᴵᴺo',idx)=='招ᴵᴺo'
    assert app.convert_kanji_esperanto_to_alphabet('软玉ᴺᶠo',idx)!='nefrito'
    old=index(LEGACY)
    for tail in app._IDENTIFIER_CONTINUATION_CHARS:
        text='招魂'+tail+'o'
        assert app.convert_kanji_esperanto_to_alphabet(text,idx)==app.convert_kanji_esperanto_to_alphabet(text,old)

def test_reviewed_prefix_guard_keeps_registered_long_keys_and_other_custom_owners():
    # Fully registered longer forms still win; this is not blanket Han-text protection.
    for owner,expected in [('nekromanci','招魂ᴬo'),('other','invit魂ᴬo')]:
        frame=pd.DataFrame([('invit','招','0'),(owner,'招魂','0')],columns=['esperanto','kanji','priority'])
        assert app.convert_kanji_esperanto_to_alphabet('招魂ᴬo',app.build_mapping_index(frame))==expected
    frame=pd.DataFrame([('invit','招','0'),('nekromanci','招魂','0'),('custom','招魂ᴬ','0')],columns=['esperanto','kanji','priority'])
    assert app.convert_kanji_esperanto_to_alphabet('招魂ᴬo',app.build_mapping_index(frame))=='customo'

def test_current_downloads_include_only_the_distinct_mineral_key():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
    senses=json.loads((app.ROOT/'data/explicit_sense_assignments_20261111.json').read_bytes())
    assert source['revision']=='sakristi-sambuk-svarm-20261114'
    assert len(data['items'])==source['current_item_count']==10640
    assert [x['body'] for x in data['items'] if x['sourceRoot']=='nefrit']==[MEDICAL]
    ordinary=rows_from_all_json(data)
    current=current_rows_from_all_json(data)
    assert len(ordinary)==10696 and len(current)==source['current_csv_count']==10697
    assert [x for x in current if x not in ordinary]==[
        dict(next(x for x in ordinary if x['source_root']=='nefrit'),kanji=MINERAL,
             source_line='explicit-sense:nefrit.mineral:20261111')]
    assert senses['senses'][0]['reserved_bare']=='软玉'
    assert source['reverse_only_aliases']['邀']=='invit'
    assert hashlib.sha256((app.ROOT/'data/explicit_sense_assignments_20261111.json').read_bytes()).hexdigest()==source['explicit_sense_assignments_sha256']
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))

def test_generator_requires_explicit_current_source_for_the_extra_sense():
    custom={'items':[{'sourceRoot':'nefrit','body':MEDICAL}]}
    assert [r['kanji'] for r in rows_from_all_json(custom)]==[MEDICAL]
    with pytest.raises(ValueError,match='exact approved source'):
        current_rows_from_all_json(custom)
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
    data['items'][0]['body']='changed'
    with pytest.raises(ValueError,match='exact approved source'):
        current_rows_from_all_json(data)

def test_invit_alias_is_conditional_and_conflict_safe():
    assert [x['kanji'] for x in rows_from_all_json({'items':[{'sourceRoot':'invit','body':'邀'}]})]==['邀']
    assert sorted(x['kanji'] for x in rows_from_all_json({'items':[{'sourceRoot':'invit','body':'招'}]}))==['招','邀']
    with pytest.raises(ValueError,match='conflicts'):
        rows_from_all_json({'items':[{'sourceRoot':'invit','body':'招'},{'sourceRoot':'other','body':'邀'}]})
    with pytest.raises(ValueError,match='Expected one'):
        rows_from_all_json({'items':[{'sourceRoot':'invit','body':'招'},{'sourceRoot':'invit','body':'招'}]})

def test_custom_csv_keeps_its_own_mineral_and_invitation_owners():
    frame=pd.DataFrame([('mine',MINERAL,'0'),('custom','招','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',frame)==app.dataframe_to_mapping_records(frame)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',frame))
    assert app.convert_kanji_esperanto_to_alphabet(MINERAL+'o 招i',idx)=='mineo customi'
    assert app.convert_kanji_esperanto_to_alphabet('邀o',idx)=='邀o'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_standard_html_keeps_recorded_source_and_literal_text(edition,mode):
    invitation='招' if edition=='current' else '邀'
    if mode=='kanji':
        content=('<ruby>'+invitation+'<rt>invit</rt></ruby>i  '
                 '<ruby>肾ᴺ<rt>nefr</rt></ruby><ruby>炎ᵀ<rt>it</rt></ruby>o '
                 '<ruby>'+MINERAL+'<rt>nefrit</rt></ruby>o<br>\n'
                 '&lt;literal&gt; &amp; 软玉o')
    else:
        content=('<ruby>invit<rt>招待</rt></ruby>i  '
                 '<ruby>nefr<rt>腎</rt></ruby><ruby>it<rt>炎</rt></ruby>o '
                 '<ruby>nefrit<rt>軟玉</rt></ruby>o<br>\n'
                 '&lt;literal&gt; &amp; 软玉o')
    # A standard-shaped test document; actual forward exports are checked separately.
    source=('<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-11T00:00:00Z -->\n'
            '<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head>\n'
            '<body>\n<p class="text-M_M">\n'+content+'</p></body></html>')
    result=recover_standard_html(source,mode)
    assert result['text']=='inviti  nefrito nefrito\n<literal> & 软玉o'
    assert result['assignment_edition']==edition
