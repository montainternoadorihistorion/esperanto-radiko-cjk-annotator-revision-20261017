"""Approved frog spelling, reverse-only former key, and unchanged top/legacy/custom."""
import csv
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json, current_rows_from_all_json

CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
SUFFIXES = ('', 'o', 'ojn', 'a', 'aj', 'i', 'as', 'is', 'os', 'us', 'u', 'igi', 'ita')

def index(edition):
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, app.load_dictionary_source(edition)))

@pytest.mark.parametrize('suffix', SUFFIXES)
def test_current_new_and_previous_spelling_restore_same_root(suffix):
    idx = index(CURRENT)
    for body in ('轨叉', '辙叉'):
        assert app.convert_kanji_esperanto_to_alphabet(body + suffix, idx) == 'frog' + suffix
    assert app.convert_kanji_esperanto_to_alphabet('轨叉翼ᴬ' + suffix, idx) == 'frogal' + suffix

@pytest.mark.parametrize('suffix', SUFFIXES)
def test_legacy_and_both_top_meanings_remain_unchanged(suffix):
    old = index(LEGACY)
    assert app.convert_kanji_esperanto_to_alphabet('辙叉' + suffix, old) == 'frog' + suffix
    assert app.convert_kanji_esperanto_to_alphabet('轨叉' + suffix, old) == 'relfork' + suffix
    for edition in (CURRENT, LEGACY):
        idx = index(edition)
        for body, root in [('帆楼', 'top'), ('境ᵀ', 'top'), ('轨', 'rel'), ('叉', 'fork')]:
            assert app.convert_kanji_esperanto_to_alphabet(body + suffix, idx) == root + suffix

def test_longer_identifier_cannot_match_shorter_frog_key():
    idx = index(CURRENT)
    flat = {k: v for bucket in idx.by_length.values() for k, v in bucket.items()}
    for body in ('轨叉', '辙叉'):
        for continuation in app._IDENTIFIER_CONTINUATION_CHARS:
            key = body + continuation
            if key not in flat:
                assert not app.convert_kanji_esperanto_to_alphabet(key + 'o', idx).startswith('frog')

def test_downloaded_csv_snippet_and_generation_include_only_reverse_alias():
    source = json.loads((app.ROOT / 'data/current_dictionary_source.json').read_bytes())
    manifest = json.loads((app.ROOT / 'data/frog_20261107.json').read_bytes())
    data = json.loads((app.ROOT / 'data/monaco_source_20261017.json').read_bytes())
    assert source['revision'] == 'sakristi-sambuk-svarm-20261114'
    assert manifest['revision'] == 'frog-20261107'
    assert source['reverse_only_aliases']['辙叉'] == 'frog'
    assert manifest['safe_reverse_aliases'] == {'辙叉': 'frog'}
    assert manifest['explicit_retained']['top'] == '帆楼'
    assert app.dictionary_options() == [CURRENT, LEGACY]
    assert [x['body'] for x in data['items'] if x['sourceRoot'] == 'frog'] == ['轨叉']
    rows = current_rows_from_all_json(data)
    assert len(rows) == source['current_csv_count'] == 10697
    assert sorted(r['kanji'] for r in rows if r['source_root'] == 'frog') == ['轨叉', '辙叉']
    assert hashlib.sha256(app.PEJVO_PIV_20260620_CSV.read_bytes()).hexdigest() == source['current_csv_sha256']
    snippet = app.ROOT / 'エスペラント語根-漢字対応表_スニペット用最小限.csv'
    assert hashlib.sha256(snippet.read_bytes()).hexdigest() == source['current_snippet_csv_sha256']

def test_previous_custom_owners_are_not_changed_and_alias_collision_rejected():
    assert rows_from_all_json({'items': [{'sourceRoot': 'frog', 'body': '辙叉'}]})[0]['kanji'] == '辙叉'
    assert rows_from_all_json({'items': [{'sourceRoot': 'frog', 'body': 'custom'}]})[0]['kanji'] == 'custom'
    with pytest.raises(ValueError, match='conflicts'):
        rows_from_all_json({'items': [{'sourceRoot': 'frog', 'body': '轨叉'}, {'sourceRoot': 'someone', 'body': '辙叉'}]})
    frame = pd.DataFrame([('customroot', '轨叉', '0')], columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom', frame) == app.dataframe_to_mapping_records(frame)
    idx = app.build_mapping_index_cached(app.effective_mapping_records('custom', frame))
    assert app.convert_kanji_esperanto_to_alphabet('轨叉o', idx) == 'customrooto'
    assert app.convert_kanji_esperanto_to_alphabet('辙叉o', idx) == '辙叉o'
