"""One adopted infest body, stable shared owners, identifiers and fixed legacy."""
import hashlib
import io
import json
import pandas as pd
import pytest
import esperanto_converter as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'
OLD='pre-las-20261017'
CHANGES={'infest':('患','侵ᴵᶠ')}
CONTROLS={'侵':'invad','娇':'lind','迟':'tard','讥':'rikan','援':'sponsor'}
PRIOR_ADOPTIONS={'kompuls':('逼','迫ᴷ'),'langvor':('倦','疲ᴸᴺ'),'setl':('居','住ˢ')}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_infest_and_preserved_owners_with_endings(source):
    mapping=index(source)
    selected={pair[source==CURRENT]:root for root,pair in (CHANGES|PRIOR_ADOPTIONS).items()}
    for body,root in (selected|CONTROLS).items():
        for suffix in SUFFIXES:
            for ending in (suffix,suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
        assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  '+root+'o\n\t'+root+'as & <x>  '

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_identifier_continuations_not_partially_consumed(source):
    mapping=index(source)
    flat={key:owner for bucket in mapping.by_length.values() for key,owner in bucket.items()}
    for root,pair in CHANGES.items():
        for continuation in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
            key=pair[source==CURRENT]+continuation
            actual=app.convert_kanji_esperanto_to_alphabet(key+'o',mapping)
            if key in flat:assert actual==flat[key]+'o'
            else:assert not actual.startswith(root),(key,actual)
    if source==CURRENT:
        assert app.convert_kanji_esperanto_to_alphabet('侵o 侵ᴵᶠo 侵ᴵᶠᴬo 侵ᴵo 侵ᴵᶠ̂o',mapping)=='invado infesto 侵ᴵᶠᴬo 侵ᴵo 侵ᴵᶠ̂o'

def test_two_editions_without_new_old_key_aliases():
    assert app.dictionary_options()==[CURRENT,OLD]
    assert len(app.DICTIONARY_SOURCES)==8
    records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
    for root,(old,new) in CHANGES.items():
        assert not [r for r in records if r[1]==old]
        assert {r[0] for r in records if r[1]==new}=={root}
        assert old not in app.CURRENT_INVERSE_ALIAS_PAIRS
        assert new not in app.CURRENT_INVERSE_ALIAS_PAIRS

def test_manifest_and_downloads_preserve_frozen_edition():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    path=app.ROOT/source['infest_assignment_20261107_manifest']
    manifest=json.loads(path.read_bytes())
    assert source['revision']==manifest['revision']=='infest-20261107'
    assert manifest['changes']=={r:list(p) for r,p in CHANGES.items()}
    assert manifest['safe_reverse_aliases']=={}
    assert manifest['user_adopted_roots']==list(CHANGES)
    assert manifest['identifier_propagated_roots']==[]
    assert manifest['metadata_only_changes']=={}
    assert set(manifest['documentation_only_changes'])=={'invad'}
    assert manifest['assignment_unchanged_item_count']==10639
    assert manifest['current_item_count']==manifest['baseline_item_count']==10640
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['infest_assignment_20261107_manifest_sha256']
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy,legacy_two=app.edition_download_data(OLD)
    assert hashlib.sha256(legacy).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(legacy_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_standard_html_spaces_newlines_protection(edition,mode):
    pieces=[]
    for root,pair in CHANGES.items():
        body=pair[edition=='current']
        gloss={'infest':'群がって侵入する'}[root]
        ruby=f'<ruby>{body}<rt>{root}</rt></ruby>' if mode=='kanji' else f'<ruby>{root}<rt>{gloss}</rt></ruby>'
        pieces.append(ruby+'o')
    content='  '+' '.join(pieces)+'<br>\n\t&lt;保護&gt; &amp;  '
    html=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-11-07T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='  infesto\n\t<保護> &  '
    assert result['assignment_edition']==edition

def test_custom_dictionary_keeps_its_selected_owner():
    for _,body in CHANGES.values():
        frame=pd.DataFrame([('custom',body,'0')],columns=['esperanto','kanji','priority'])
        records=app.effective_mapping_records('custom',frame)
        assert records==app.dataframe_to_mapping_records(frame)
        assert app.convert_kanji_esperanto_to_alphabet(body+'o',app.build_mapping_index_cached(records))=='customo'
