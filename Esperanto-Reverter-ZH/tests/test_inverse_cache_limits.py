"""Bounded bundled dictionary caches and conversion-only lookup construction."""
from io import BytesIO
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import esperanto_converter_zh as app


def test_two_latest_indices_and_csv_reads_are_reused_and_clearable(tmp_path):
    app.read_assignment_csv_from_path.clear()
    app.build_mapping_index_cached.clear()
    try:
        paths = []
        for i in range(3):
            path = tmp_path / f"{i}.csv"
            path.write_text(f"owner{i},木\n", encoding="utf-8")
            paths.append(str(path))
        with patch.object(app, "read_assignment_csv", wraps=app.read_assignment_csv) as parse:
            for i in (0, 1, 1, 2, 1):
                assert app.read_assignment_csv_from_path(paths[i], 0).iloc[0]["esperanto"] == f"owner{i}"
            assert parse.call_count == 3
            app.read_assignment_csv_from_path(paths[0], 0)
            assert parse.call_count == 4
            app.read_assignment_csv_from_path.clear(paths[1], 0)
            app.read_assignment_csv_from_path(paths[1], 0)
            assert parse.call_count == 5

        records = [((f"owner{i}", "木", "1"),) for i in range(3)]
        with patch.object(app, "build_mapping_index", wraps=app.build_mapping_index) as build:
            for i in (0, 1, 1, 2, 1):
                idx = app.build_mapping_index_cached(records[i])
                assert app.convert_kanji_esperanto_to_alphabet("木o", idx) == f"owner{i}o"
            assert build.call_count == 3
            app.build_mapping_index_cached(records[0])
            assert build.call_count == 4
            app.build_mapping_index_cached.clear(records[1])
            app.build_mapping_index_cached(records[1])
            assert build.call_count == 5
    finally:
        app.build_mapping_index_cached.clear()
        app.read_assignment_csv_from_path.clear()


def test_ui_builds_index_only_on_conversion_and_custom_files_use_no_global_index():
    # Calling the real main through an import lets the test observe its index calls on each rerun.
    at = AppTest.from_string(f"import {app.__name__} as app\napp.main()", default_timeout=40)
    upload_bytes = b"aaa,\xe8\xb6\xb3\nbbb,\xe8\xb6\xb3\n"
    def upload(*args, **kwargs):
        file = BytesIO(upload_bytes)
        file.name = "custom.csv"
        file.size = len(upload_bytes)
        return file

    with (patch.object(app, "build_mapping_index_cached", wraps=app.build_mapping_index_cached) as cached,
          patch.object(app.st, "file_uploader", side_effect=upload)):
        at.run()
        at.sidebar.selectbox(key="plain_edition").set_value(app.LEGACY_INVERSE_SOURCE_ID).run()
        at.text_area(key="plain_input_text").set_value("足球o").run()
        assert cached.call_count == 0
        at.button[0].click().run()
        assert at.text_area[1].value == "piedpilko"
        assert cached.call_count == 1
        stats = [(m.label, m.value) for m in at.metric]
        assert len(stats) == 4
        at.run()
        assert [(m.label, m.value) for m in at.metric] == stats
        assert cached.call_count == 1

        at.sidebar.selectbox(key="plain_edition").set_value(app.CURRENT_INVERSE_SOURCE_ID).run()
        assert at.button(key="plain_prepare_save").disabled
        at.button[0].click().run()
        assert at.text_area[1].value == "futbalo"
        at.button(key="plain_prepare_save").click().run()
        assert at.text_area(key="result_save_preview").value == "futbalo"
        at.button(key="close_result_save_dialog").click().run()
        assert cached.call_count == 2

        at.checkbox(key="use_custom_csv").check().run()
        with patch.object(app, "build_mapping_index", wraps=app.build_mapping_index) as build:
            at.text_area(key="plain_input_text").set_value("足o").run()
            assert build.call_count == 0
            at.button[0].click().run()
            assert at.text_area[1].value == "aaao"
            upload_bytes = upload_bytes.replace(b"aaa", b"ccc")
            at.run()
            assert at.button(key="plain_prepare_save").disabled
            at.button[0].click().run()
            assert at.text_area[1].value == "ccco"
            assert build.call_count == 2
            assert cached.call_count == 2
        at.checkbox(key="use_custom_csv").uncheck().run()
        assert at.button(key="plain_prepare_save").disabled
        assert cached.call_count == 2
        assert not at.exception

