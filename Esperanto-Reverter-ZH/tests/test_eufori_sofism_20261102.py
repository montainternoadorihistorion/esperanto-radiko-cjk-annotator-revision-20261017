"""Approved two-root change, shared owners, identifier boundaries and fixed legacy."""
import hashlib
import io
import json

import pandas as pd
import pytest
import esperanto_converter_zh as app
from html_source_recovery import recover_standard_html

CURRENT = 'pejvo-piv-20260620'
OLD = 'pre-las-20261017'
CHANGES = {'eŭfori': ('欣快', '快ᴱ'), 'sofism': ('诡辩', '伪辩')}
CONTROLS = {'快': 'agrabl', '快ᴬᴸ': 'alegr', '伪': 'fals', '伪ᴾ': 'pseŭdo', '芙蓉': 'hibisk', '残船': 'vrak', '册ᴱ': 'ekzempler'}
SUFFIXES = ('', 'o', 'oj', 'on', 'ojn', 'a', 'aj', 'an', 'ajn', 'e', 'i', 'as', 'is', 'os', 'us', 'u', 'ado', 'ita', 'intajn', 'igi', 'ĉjo')


def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source, app.load_dictionary_source(source)))


@pytest.mark.parametrize('source', (CURRENT, OLD))
def test_changed_roots_and_shared_owners_with_endings(source):
    mapping = index(source)
    selected = {pair[source == CURRENT]: root for root, pair in CHANGES.items()}
    for body, root in (selected | CONTROLS).items():
        for suffix in SUFFIXES:
            for ending in (suffix, suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body + ending, mapping) == root + suffix
        assert app.convert_kanji_esperanto_to_alphabet('  ' + body + 'o\n\t' + body + 'as & <x>  ', mapping) == '  ' + root + 'o\n\t' + root + 'as & <x>  '


@pytest.mark.parametrize('source', (CURRENT, OLD))
def test_long_identifier_is_not_partially_consumed(source):
    mapping = index(source)
    flat = {key: owner for bucket in mapping.by_length.values() for key, owner in bucket.items()}
    for root, pair in CHANGES.items():
        body = pair[source == CURRENT]
        for continuation in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
            key = body + continuation
            actual = app.convert_kanji_esperanto_to_alphabet(key + 'o', mapping)
            if key in flat:
                assert actual == flat[key] + 'o'
            else:
                assert not actual.startswith(root), (key, actual)
    if source == CURRENT:
        assert app.convert_kanji_esperanto_to_alphabet('快o 快ᴬᴸo 快ᴱo 快ᴱᴬo', mapping) == 'agrablo alegro eŭforio 快ᴱᴬo'


def test_two_editions_and_no_obsolete_aliases():
    assert app.dictionary_options() == [CURRENT, OLD]
    assert len(app.DICTIONARY_SOURCES) == 8
    records = app.effective_mapping_records(CURRENT, app.load_dictionary_source(CURRENT))
    for root, (old, new) in CHANGES.items():
        assert not [r for r in records if r[1] == old]
        assert {r[0] for r in records if r[1] == new} == {root}
        assert old not in app.CURRENT_INVERSE_ALIAS_PAIRS
        assert new not in app.CURRENT_INVERSE_ALIAS_PAIRS


def test_approved_manifest_downloads_and_fixed_legacy():
    source = json.loads((app.ROOT / 'data/current_dictionary_source.json').read_bytes())
    path = app.ROOT / source['eufori_sofism_20261102_manifest']
    manifest = json.loads(path.read_bytes())
    assert source['revision'] == manifest['revision'] == '2026-11-02-eufori-sofism'
    assert manifest['changes'] == {'eu^fori': ['欣快', '快ᴱ'], 'sofism': ['诡辩', '伪辩']}
    assert manifest['safe_reverse_aliases'] == {}
    assert manifest['user_adopted_roots'] == ['eu^fori', 'sofism']
    assert manifest['identifier_propagated_roots'] == []
    assert manifest['metadata_only_changes'] == {}
    assert manifest['documentation_only_changes'] == {'agrabl': {'group_count': [2, 3]}, 'alegr': {'group_count': [2, 3]}}
    assert manifest['assignment_unchanged_item_count'] == 10638
    assert manifest['current_item_count'] == manifest['baseline_item_count'] == 10640
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source['eufori_sofism_20261102_manifest_sha256']
    full, two = app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest() == source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest() == source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full))) == app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy, legacy_two = app.edition_download_data(OLD)
    assert hashlib.sha256(legacy).hexdigest() == app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(legacy_two).hexdigest() == app.EDITION_POLICY['fixed_two_column_sha256']


@pytest.mark.parametrize('edition', ('current', 'legacy'))
@pytest.mark.parametrize('mode', ('kanji', 'annotation'))
def test_standard_html_source_and_protected_text(edition, mode):
    def ruby(root):
        body = CHANGES[root][edition == 'current']
        return f'<ruby>{body}<rt>{root}</rt></ruby>' if mode == 'kanji' else f'<ruby>{root}<rt>注釈</rt></ruby>'
    content = '  ' + ruby('eŭfori') + 'o ' + ruby('sofism') + 'a<br>\n\t&lt;保護&gt; &amp;  '
    html = f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-11-02T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result = recover_standard_html(html, mode)
    assert result['text'] == '  eŭforio sofisma\n\t<保護> &  '
    assert result['assignment_edition'] == edition


def test_custom_dictionary_keeps_its_own_assignment():
    frame = pd.DataFrame([('custom', '快ᴱ', '0')], columns=['esperanto', 'kanji', 'priority'])
    records = app.effective_mapping_records('custom', frame)
    assert records == app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet('快ᴱo', app.build_mapping_index_cached(records)) == 'customo'
