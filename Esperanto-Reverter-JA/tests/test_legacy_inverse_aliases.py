"""Fixed-old restoration supplement: bounded scope, immutable data and truthful downloads."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import io
import json
import shutil

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app

OLD = 'pre-las-20261017'
CURRENT = 'pejvo-piv-20260620'
# The complete adopted set is independently pinned in test_unique_inverse_keys.
ALIASES = app.LEGACY_INVERSE_ALIAS_PAIRS
SUFFIXES = ('', 'o', 'on', 'oj', 'ojn', 'a', 'aj', 'ajn', 'e', 'i', 'is', 'as', 'os', 'us', 'u', 'O')


def effective_index(source, frame=None):
    if frame is None:
        frame = app.load_dictionary_source(source)
    return app.build_mapping_index_cached(app.effective_mapping_records(source, frame))


def result_download(at):
    return next(item for item in at.get('download_button') if item.proto.label in ('テキストをダウンロード', '📥 下载文本'))


def test_reviewed_aliases_and_existing_fixed_keys_are_preserved():
    frame = app.load_dictionary_source(OLD)
    before = app.build_mapping_index(frame)
    after = effective_index(OLD, frame)
    flat_before = {key: root for bucket in before.by_length.values() for key, root in bucket.items()}
    flat_after = {key: root for bucket in after.by_length.values() for key, root in bucket.items()}
    assert len(frame) == len(flat_before) == 10636
    assert {key: value for key, value in flat_after.items() if key not in flat_before} == ALIASES
    assert all(flat_after[key] == value for key, value in flat_before.items())
    for key in flat_before:
        assert app.convert_kanji_esperanto_to_alphabet(key + 'o', after) == app.convert_kanji_esperanto_to_alphabet(key + 'o', before)
    for key, root in ALIASES.items():
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(key + suffix, after) == root + suffix.lower()
    for key, root in {'丸炎ᵀ': 'testikit', '丸炎': 'orkidit'}.items():
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(key + suffix, after) == root + suffix.lower()
    # The newly approved marked component is tested separately; ordinary identifiers stay unchanged.
    for text in ('炎o', '丸ᵀo', '兰o'):
        assert app.convert_kanji_esperanto_to_alphabet(text, after) == app.convert_kanji_esperanto_to_alphabet(text, before)


def test_no_automatic_aliases_in_current_archives_or_custom():
    for source in app.DICTIONARY_SOURCES:
        if source not in (OLD, CURRENT):
            frame = app.load_dictionary_source(source)
            assert app.effective_mapping_records(source, frame) == app.dataframe_to_mapping_records(frame)
            assert 'inverse_compatibility_sha256' not in app.source_provenance(source)
    # The primary current source receives exactly its separately approved set.
    current = app.load_dictionary_source(CURRENT)
    current_records = app.dataframe_to_mapping_records(current)
    assert app.effective_mapping_records(CURRENT, current) == current_records + tuple((root, key, "0") for key, root in app.CURRENT_INVERSE_ALIAS_PAIRS.items())
    assert app.source_provenance(CURRENT)["inverse_compatibility_revision"].startswith("current-compound-inverse-")
    # Even a custom copy of the old original must not silently acquire the supplement.
    frame = app.read_assignment_csv(io.BytesIO(app.edition_download_data(OLD)[0]))
    assert app.effective_mapping_records('custom', frame) == app.dataframe_to_mapping_records(frame)
    assert len(app.effective_mapping_records('custom', frame)) == 10636
    with pytest.raises(ValueError, match='only to the fixed old edition'):
        app.legacy_effective_download_data(CURRENT)


def test_exact_alias_collision_is_rejected_and_reapplication_is_idempotent():
    frame = app.load_dictionary_source(OLD)
    conflicting = pd.concat([frame, pd.DataFrame([{'esperanto': 'wrong', 'kanji': '丸ᵀ炎ᵀ', 'priority': '-999'}])], ignore_index=True)
    with pytest.raises(ValueError, match='conflicts with an existing root'):
        app.effective_mapping_records(OLD, conflicting)
    effective = app.effective_mapping_records(OLD, frame)
    reapplied = pd.DataFrame(effective, columns=['esperanto', 'kanji', 'priority'])
    assert app.effective_mapping_records(OLD, reapplied) == effective


def test_supplement_closed_scope_and_base_hash_are_validated(tmp_path, monkeypatch):
    folder = tmp_path/'data'
    folder.mkdir()
    path = folder/'legacy_inverse_aliases.json'
    original = json.loads((app.ROOT/'data/legacy_inverse_aliases.json').read_bytes())
    monkeypatch.setattr(app, 'ROOT', tmp_path)
    wrong = dict(original, aliases=original['aliases'] + [{'kanji': '炎ᵀ', 'esperanto': 'testikit'}])
    path.write_text(json.dumps(wrong), encoding='utf-8')
    with pytest.raises(ValueError, match='Invalid fixed-old inverse alias supplement'):
        app.load_legacy_inverse_aliases()
    path.write_text(json.dumps(dict(original, fixed_csv_sha256='0'*64)), encoding='utf-8')
    with pytest.raises(ValueError, match='fixed pre-assignment dictionary has changed'):
        app.load_legacy_inverse_aliases()


def test_fixed_download_bytes_and_effective_csv_custom_roundtrip():
    full, snippet = app.edition_download_data(OLD)
    assert hashlib.sha256(full).hexdigest() == app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(snippet).hexdigest() == app.EDITION_POLICY['fixed_two_column_sha256']
    effective = app.legacy_effective_download_data(OLD)
    assert effective.startswith(b'esperanto,kanji,priority\r\n')
    frame = app.read_assignment_csv(io.BytesIO(effective))
    assert len(frame) == 10794
    assert effective_index('custom', frame) == effective_index(OLD)
    meta = app.source_provenance(OLD)
    assert meta['effective_dictionary_filename'] not in (meta['dictionary_filename'], meta['snippet_filename'])
    for field in ('result_filename', 'effective_dictionary_filename', 'identity', 'label'):
        assert meta['inverse_compatibility_revision'] in meta[field]
        assert meta['inverse_compatibility_sha256'][:12] in meta[field]
    assert 'inverse_' not in meta['dictionary_filename']
    assert 'inverse_' not in meta['snippet_filename']


def test_ui_old_result_stays_old_until_reconverted_and_effective_csv_download_matches():
    captures = []
    original = app.st.download_button
    def capture(*args, **kwargs):
        captures.append({'file_name': kwargs.get('file_name'), 'data': kwargs.get('data', args[1] if len(args)>1 else None), 'disabled': kwargs.get('disabled', False)})
        return original(*args, **kwargs)
    with patch.object(app.st, 'download_button', side_effect=capture):
        at = AppTest.from_file(str(Path(app.__file__)), default_timeout=20).run()
        assert not at.exception
        assert len(at.sidebar.selectbox[0].options) == 2
        assert len(at.get('download_button')) == 3
        at.sidebar.selectbox[0].set_value(OLD).run()
        assert not at.exception and len(at.get('download_button')) == 3
        assert any('158件の復元補助' in item.value or '158条还原补充' in item.value for item in at.sidebar.caption)
        text = '丸ᵀ炎ᵀo 丸ᴼ炎ᵀo 兰炎ᵀo 丸炎ᵀo 丸炎o'
        at.text_area[0].set_value(text)
        at.button[0].click().run()
        assert not at.exception
        assert at.text_area[1].value == 'testikito orkidito orkidito testikito orkidito'
        meta = dict(at.session_state[app.CONVERTED_PROVENANCE_KEY])
        assert any(item['file_name'] == meta['effective_dictionary_filename'] and item['data'] == app.legacy_effective_download_data(OLD) for item in captures)
        # Simulate the exact provenance shape of a result made before the supplement.
        old = {key: value for key, value in meta.items() if key not in ('inverse_compatibility_revision', 'inverse_compatibility_sha256', 'effective_dictionary_filename')}
        old['identity'] = f"{OLD}:{old['revision']}:{old['dictionary_sha256']}"
        old['label'] = meta['label'].split(' / inverse:')[0]
        old['result_filename'] = meta['dictionary_filename'].replace('dictionary_', 'esperanto_').replace('.csv', '.txt')
        at.session_state[app.CONVERTED_PROVENANCE_KEY] = old
        at.session_state[app.CONVERTED_TEXT_KEY] = app.convert_kanji_esperanto_to_alphabet(text, app.build_mapping_index(app.load_dictionary_source(OLD)))
        at.run()
        assert not at.exception and at.warning and result_download(at).proto.disabled
        assert at.session_state[app.CONVERTED_PROVENANCE_KEY] == old
        assert any(old['label'] in caption.value and 'inverse:' not in caption.value for caption in at.caption)
        assert captures[-1]['file_name'] == old['result_filename'] and captures[-1]['disabled']
        at.button[0].click().run()
        assert not at.exception and not result_download(at).proto.disabled
        assert at.session_state[app.CONVERTED_PROVENANCE_KEY] == meta
        assert at.text_area[1].value == 'testikito orkidito orkidito testikito orkidito'


def test_supplement_revision_and_hash_invalidate_saved_results(tmp_path):
    shutil.copytree(app.ROOT/'data', tmp_path/'data')
    target = tmp_path/Path(app.__file__).name
    shutil.copy2(app.__file__, target)
    at = AppTest.from_file(str(target), default_timeout=20).run()
    at.sidebar.selectbox[0].set_value(OLD).run()
    at.text_area[0].set_value('丸ᵀ炎ᵀo')
    at.button[0].click().run()
    assert not at.exception
    created = dict(at.session_state[app.CONVERTED_PROVENANCE_KEY])
    path = tmp_path/'data/legacy_inverse_aliases.json'
    manifest = json.loads(path.read_bytes())
    manifest['revision'] += '-test'
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    at.run()
    assert not at.exception and at.warning and result_download(at).proto.disabled
    assert at.session_state[app.CONVERTED_PROVENANCE_KEY] == created
    at.button[0].click().run()
    assert not at.exception and not result_download(at).proto.disabled
    after = at.session_state[app.CONVERTED_PROVENANCE_KEY]
    assert after['inverse_compatibility_revision'] == manifest['revision']
    assert after['inverse_compatibility_sha256'] != created['inverse_compatibility_sha256']
    assert after['result_filename'] != created['result_filename']
    assert after['dictionary_filename'] == created['dictionary_filename']


def test_effective_csv_uploaded_as_custom_uses_the_same_ui_result():
    effective = app.legacy_effective_download_data(OLD)
    upload = io.BytesIO(effective)
    upload.name = app.source_provenance(OLD)['effective_dictionary_filename']
    upload.size = len(effective)
    at = AppTest.from_file(str(Path(app.__file__)), default_timeout=20).run()
    at.checkbox[0].check().run()
    with patch.object(app.st, 'file_uploader', side_effect=lambda *a, **k: (upload.seek(0), upload)[1]):
        at.run()
        at.text_area[0].set_value('丸ᵀ炎ᵀo 丸ᴼ炎ᵀo 兰炎ᵀo 放is 簧o')
        at.button[0].click().run()
        assert not at.exception
        assert at.text_area[1].value == 'testikito orkidito orkidito emancipis anĉo'
        meta = at.session_state[app.CONVERTED_PROVENANCE_KEY]
        assert meta['edition_id'] == 'custom'
        assert 'inverse_compatibility_revision' not in meta
        assert not result_download(at).proto.disabled
