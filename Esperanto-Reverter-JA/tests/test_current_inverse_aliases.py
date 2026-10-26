"""Reviewed current inverse aliases, immutable canonical data and explicit revision pins."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import importlib.util
import io
import json
import shutil

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app

CURRENT = 'pejvo-piv-20260620'
OLD = 'pre-las-20261017'
CURRENT_SHA = 'adb8ef79a751242fe9361825ce10e0b1b2025a594426ebf03542d1dde8688a9d'
CURRENT_TWO_SHA = 'f5c87d7ad640a570245b4afffcf93de3a711134354676a4aeb870dc306035f64'
OLD_EFFECTIVE_SHA = '0f861144f2b5dc81334ca684e7798e6abfa3fc4f62e3474c6775920159fa02d0'
OLD_SUPPLEMENT_SHA = '59e2c3cd9f69a1b4d41b4729039a5ac903973dc198d2b20d006e8326819ec4ee'
SUFFIXES = ('', 'o', 'oj', 'on', 'ojn', 'a', 'aj', 'an', 'ajn', 'e', 'i', 'as', 'is', 'os', 'us', 'u', 'igi', 'igxi', 'A')


def effective_index(source, frame=None):
    frame = app.load_dictionary_source(source) if frame is None else frame
    return app.build_mapping_index_cached(app.effective_mapping_records(source, frame))


def result_save_control(at):
    return at.button(key='plain_prepare_save')


def test_reviewed_current_keys_added_and_every_existing_key_retained():
    frame = app.load_dictionary_source(CURRENT)
    records = app.dataframe_to_mapping_records(frame)
    assert len(records) == 10678
    assert app.effective_mapping_records(CURRENT, frame) == records + tuple((root, key, '0') for key, root in app.CURRENT_INVERSE_ALIAS_PAIRS.items())
    before, after = app.build_mapping_index(frame), effective_index(CURRENT, frame)
    flat_before = {key: value for bucket in before.by_length.values() for key, value in bucket.items()}
    flat_after = {key: value for bucket in after.by_length.values() for key, value in bucket.items()}
    assert len(flat_before) == 10678 and flat_after == dict(flat_before, **app.CURRENT_INVERSE_ALIAS_PAIRS)
    for key in flat_before:
        assert app.convert_kanji_esperanto_to_alphabet(key+'o', after) == app.convert_kanji_esperanto_to_alphabet(key+'o', before)
    for suffix in SUFFIXES:
        assert app.convert_kanji_esperanto_to_alphabet('兰炎ᵀ'+suffix, after) == 'orkidit'+suffix.lower()
    for text in ('兰o', '炎o', '丸ᴼ炎ᵀo', '丸ᵀ炎ᵀa', '藻ᶠᶜoj 金ᴱᵁ̆o 全O'):
        assert app.convert_kanji_esperanto_to_alphabet(text, after) == app.convert_kanji_esperanto_to_alphabet(text, before)


def test_reviewed_old_supplement_metadata_archives_and_custom_are_isolated():
    assert hashlib.sha256((app.ROOT/'data/legacy_inverse_aliases.json').read_bytes()).hexdigest() == OLD_SUPPLEMENT_SHA
    assert hashlib.sha256(app.legacy_effective_download_data(OLD)).hexdigest() == OLD_EFFECTIVE_SHA
    meta = app.source_provenance(OLD)
    assert meta['inverse_compatibility_sha256'] == OLD_SUPPLEMENT_SHA
    assert meta['inverse_compatibility_revision'] == 'legacy-compound-inverse-20261018-v3'
    assert meta['result_filename'] == 'esperanto_old_4c16c8937c60_eed2a8bfc21a_inverse_legacy-compound-inverse-20261018-v3_59e2c3cd9f69.txt'
    old_records = app.dataframe_to_mapping_records(app.load_dictionary_source(OLD))
    assert app.effective_mapping_records(OLD, app.load_dictionary_source(OLD)) == old_records + tuple((root, key, '0') for key, root in app.LEGACY_INVERSE_ALIAS_PAIRS.items())
    for source in app.DICTIONARY_SOURCES:
        if source not in (CURRENT, OLD):
            frame = app.load_dictionary_source(source)
            assert app.effective_mapping_records(source, frame) == app.dataframe_to_mapping_records(frame)
            assert 'inverse_compatibility_sha256' not in app.source_provenance(source)
    custom = pd.DataFrame([('custom_owner', '兰炎ᵀ', '0')], columns=['esperanto', 'kanji', 'priority'])
    assert app.convert_kanji_esperanto_to_alphabet('兰炎ᵀa', effective_index('custom', custom)) == 'custom_ownera'
    assert app.effective_mapping_records('custom', app.load_dictionary_source(CURRENT)) == app.dataframe_to_mapping_records(app.load_dictionary_source(CURRENT))


def test_alias_and_canonical_owner_conflicts_rejected_and_reapplication_idempotent():
    frame = app.load_dictionary_source(CURRENT)
    conflict = pd.concat([frame, pd.DataFrame([{'esperanto': 'wrong', 'kanji': '兰炎ᵀ', 'priority': '-1'}])], ignore_index=True)
    with pytest.raises(ValueError, match='conflicts with an existing root'):
        app.effective_mapping_records(CURRENT, conflict)
    missing_owner = frame[frame.kanji != '丸ᴼ炎ᵀ']
    with pytest.raises(ValueError, match='canonical orkidit owner changed'):
        app.effective_mapping_records(CURRENT, missing_owner)
    effective = app.effective_mapping_records(CURRENT, frame)
    assert app.effective_mapping_records(CURRENT, pd.DataFrame(effective, columns=['esperanto', 'kanji', 'priority'])) == effective


@pytest.mark.parametrize('mutation', ('extra_alias', 'wrong_source', 'wrong_owner', 'revision_mismatch', 'supplement_sha_mismatch', 'metadata_sha_mismatch'))
def test_manifest_closed_scope_and_revision_sha_pins(tmp_path, monkeypatch, mutation):
    data = tmp_path/'data'
    data.mkdir()
    for name in ('current_inverse_aliases.json', 'current_dictionary_source.json'):
        shutil.copy2(app.ROOT/'data'/name, data/name)
    monkeypatch.setattr(app, 'ROOT', tmp_path)
    supplement_path = data/'current_inverse_aliases.json'
    source_path = data/'current_dictionary_source.json'
    supplement, metadata = json.loads(supplement_path.read_bytes()), json.loads(source_path.read_bytes())
    if mutation == 'extra_alias': supplement['aliases'].append({'kanji': '炎ᵀ', 'esperanto': 'orkidit'})
    if mutation == 'wrong_source': supplement['source_id'] = OLD
    if mutation == 'wrong_owner': supplement['required_canonical_owner']['esperanto'] = 'other'
    if mutation == 'revision_mismatch': metadata['revision'] += '-future'
    if mutation == 'supplement_sha_mismatch': supplement['current_csv_sha256'] = '0'*64
    if mutation == 'metadata_sha_mismatch': metadata['current_csv_sha256'] = '0'*64
    supplement_path.write_text(json.dumps(supplement), encoding='utf-8')
    source_path.write_text(json.dumps(metadata), encoding='utf-8')
    message = 'Invalid current inverse alias supplement' if mutation in ('extra_alias', 'wrong_source', 'wrong_owner') else 'requires re-audit'
    with pytest.raises(ValueError, match=message): app.load_current_inverse_aliases()


def test_actual_current_csv_change_is_rejected_without_review(tmp_path, monkeypatch):
    current = tmp_path/'current.csv'
    current.write_bytes(app.DICTIONARY_SOURCES[CURRENT]['path'].read_bytes()+b'\n')
    sources = dict(app.DICTIONARY_SOURCES)
    sources[CURRENT] = {**sources[CURRENT], 'path': current}
    monkeypatch.setattr(app, 'DICTIONARY_SOURCES', sources)
    with pytest.raises(ValueError, match='requires re-audit'): app.source_provenance(CURRENT)


def test_fixed_exports_and_effective_custom_csv_all_key_equivalence():
    full, two = app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest() == CURRENT_SHA
    assert hashlib.sha256(two).hexdigest() == CURRENT_TWO_SHA
    raw = app.current_effective_download_data(CURRENT)
    assert raw.startswith(b'esperanto,kanji,priority\r\n')
    custom = app.read_assignment_csv(io.BytesIO(raw))
    assert len(custom) == 10687 and effective_index('custom', custom) == effective_index(CURRENT)
    meta = app.source_provenance(CURRENT)
    assert meta['dictionary_filename'] == 'dictionary_new_2026-10-26-stal_adb8ef79a751.csv'
    assert meta['snippet_filename'] == 'dictionary_new_2026-10-26-stal_adb8ef79a751_2col.csv'
    for field in ('identity', 'label', 'result_filename', 'effective_dictionary_filename'):
        assert meta['inverse_compatibility_revision'] in meta[field]
        assert meta['inverse_compatibility_sha256'][:12] in meta[field]
    with pytest.raises(ValueError, match='only to the primary current edition'):
        app.current_effective_download_data(OLD)


def test_canonical_generator_rerun_keeps_alias_layer_separate(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(app.ROOT/'tools'))
    path = app.ROOT/'tools/build_reverter_dictionary_from_all_json.py'
    spec = importlib.util.spec_from_file_location('reviewed_generator', path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    rows = builder.rows_from_all_json(json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes()))
    output = tmp_path/'regenerated.csv'
    builder.write_rows(rows, output)
    assert output.read_bytes() == app.DICTIONARY_SOURCES[CURRENT]['path'].read_bytes()
    regenerated = app.read_assignment_csv(output)
    assert app.effective_mapping_records(CURRENT, regenerated) == app.effective_mapping_records(CURRENT, app.load_dictionary_source(CURRENT))


def test_ui_previous_current_result_is_not_relabelled_and_new_download_matches():
    captured = []
    original = app.st.download_button
    def capture(*args, **kwargs):
        captured.append({'file': kwargs.get('file_name'), 'data': kwargs.get('data', args[1] if len(args)>1 else None), 'disabled': kwargs.get('disabled', False)})
        return original(*args, **kwargs)
    with patch.object(app.st, 'download_button', side_effect=capture):
        at = AppTest.from_file(str(Path(app.__file__)), default_timeout=20).run()
        assert not at.exception and len(at.sidebar.selectbox[0].options) == 2
        assert any('9件の復元補助' in item.value or '9条还原补充' in item.value for item in at.sidebar.caption)
        assert len(at.get('download_button')) == 3
        text = '兰炎ᵀ 兰炎ᵀa 兰炎ᵀi 丸ᴼ炎ᵀo 兰o 炎o'
        at.text_area[0].set_value(text); at.button[0].click().run()
        assert not at.exception and at.text_area[1].value == 'orkidit orkidita orkiditi orkidito orkido kataro'
        meta = dict(at.session_state[app.CONVERTED_PROVENANCE_KEY])
        assert any(item['file'] == meta['effective_dictionary_filename'] and item['data'] == app.current_effective_download_data(CURRENT) for item in captured)
        prior = {key: value for key, value in meta.items() if key not in ('inverse_compatibility_revision', 'inverse_compatibility_sha256', 'effective_dictionary_filename')}
        prior['identity'] = f"{CURRENT}:{prior['revision']}:{prior['dictionary_sha256']}"
        prior['label'] = prior['label'].split(' / inverse:')[0]
        prior['result_filename'] = prior['dictionary_filename'].replace('dictionary_', 'esperanto_').replace('.csv', '.txt')
        at.session_state[app.CONVERTED_PROVENANCE_KEY] = prior
        at.session_state[app.CONVERTED_TEXT_KEY] = app.convert_kanji_esperanto_to_alphabet(text, app.build_mapping_index(app.load_dictionary_source(CURRENT)))
        at.run()
        assert not at.exception and at.warning and result_save_control(at).proto.disabled
        assert at.session_state[app.CONVERTED_PROVENANCE_KEY] == prior
        assert not any(b.proto.label in ('テキストをダウンロード', '📥 下载文本') for b in at.get('download_button'))
        at.button[0].click().run()
        assert not at.exception and not result_save_control(at).proto.disabled
        assert at.session_state[app.CONVERTED_PROVENANCE_KEY] == meta
        result_save_control(at).click().run()
        assert not at.exception and captured[-1]['file'] == meta['result_filename']
        assert captured[-1]['data'].decode('utf-8') == at.text_area(key='result_save_preview').value


def test_current_supplement_revision_change_invalidates_result(tmp_path):
    shutil.copytree(app.ROOT/'data', tmp_path/'data')
    target = tmp_path/Path(app.__file__).name
    shutil.copy2(app.__file__, target)
    at = AppTest.from_file(str(target), default_timeout=20).run()
    at.text_area[0].set_value('兰炎ᵀa'); at.button[0].click().run()
    assert not at.exception
    old = dict(at.session_state[app.CONVERTED_PROVENANCE_KEY])
    path = tmp_path/'data/current_inverse_aliases.json'
    value = json.loads(path.read_bytes()); value['revision'] += '-test'
    path.write_text(json.dumps(value), encoding='utf-8')
    at.run()
    assert not at.exception and at.warning and result_save_control(at).proto.disabled
    assert at.session_state[app.CONVERTED_PROVENANCE_KEY] == old
    at.button[0].click().run()
    assert not at.exception and not result_save_control(at).proto.disabled
    new = at.session_state[app.CONVERTED_PROVENANCE_KEY]
    assert new['inverse_compatibility_sha256'] != old['inverse_compatibility_sha256']
    assert new['result_filename'] != old['result_filename']
    assert new['dictionary_filename'] == old['dictionary_filename']


def test_current_effective_csv_custom_ui_conversion():
    raw = app.current_effective_download_data(CURRENT)
    upload = io.BytesIO(raw); upload.name = 'current-effective.csv'; upload.size = len(raw)
    at = AppTest.from_file(str(Path(app.__file__)), default_timeout=20).run()
    at.checkbox[0].check().run()
    with patch.object(app.st, 'file_uploader', side_effect=lambda *a, **k: (upload.seek(0), upload)[1]):
        at.run(); at.text_area[0].set_value('兰炎ᵀ 兰炎ᵀa 兰炎ᵀi 放is'); at.button[0].click().run()
        assert not at.exception and at.text_area[1].value == 'orkidit orkidita orkiditi lasis'
        assert at.session_state[app.CONVERTED_PROVENANCE_KEY]['edition_id'] == 'custom'
        assert not result_save_control(at).proto.disabled
