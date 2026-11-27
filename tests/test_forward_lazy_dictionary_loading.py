"""First paint, saved results and uploads must not fetch a bundled conversion table."""
import hashlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def exercise_language(language):
    # Each app has same-named sibling modules and distinct local data.
    app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    sys.path.insert(0, str(app))
    import esp_assignment_edition as editions
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    real_download = st.download_button
    with patch.object(editions, "load_lists_path", wraps=editions.load_lists_path) as load, \
            patch.object(editions, "file_hash", wraps=editions.file_hash) as hash_file, \
            patch.object(st, "download_button", wraps=real_download) as download:
        screen = AppTest.from_file(str(app / "main.py"), default_timeout=120)
        screen.run()
        mode = screen.radio(key="_conversion_mode_widget")
        mode.set_value(mode.options[2])
        screen.selectbox(key="_assignment_edition_widget").set_value("legacy")
        screen.run()
        source = "futbalo @futbal@o %futbalo%"
        screen.text_area(key="text0_value").set_value(source).run()
        assert not screen.exception
        load.assert_not_called()
        hash_file.assert_not_called()

        if language == "ZH":
            expected_path = editions.resolve_path(app / "app_data", "ruby", "current")
            expected_digest = hashlib.sha256(expected_path.read_bytes()).digest()
            captured = []

            def capture_sample(*args, **kwargs):
                if kwargs.get("key") == "download_sample_json":
                    data = kwargs["data"]
                    captured.append((kwargs["file_name"], hashlib.file_digest(data, "sha256").digest()))
                    data.seek(0)
                return real_download(*args, **kwargs)

            with patch.object(st, "download_button", side_effect=capture_sample):
                for edition in ("current", "legacy"):
                    screen.selectbox(key="_assignment_edition_widget").set_value(edition).run()
                    assert not screen.get("download_button")
                    screen.button(key="prepare_sample_json").click().run()
                    assert captured[-1] == ("示例_替换用JSON文件.json", expected_digest)
                    selector = screen.radio(key="_conversion_mode_widget")
                    selector.set_value(selector.options[1]).run()
                    assert not screen.get("download_button")
                    selector.set_value(selector.options[2]).run()
                assert len(captured) == 2
                load.assert_not_called()

        for edition, expected in (("legacy", "球ᶠo 球ᶠo futbalo"), ("current", "足球o 足球o futbalo")):
            screen.selectbox(key="_assignment_edition_widget").set_value(edition).run()
            assert "confirm_download" not in {button.key for button in screen.button}
            assert screen.text_area(key="text0_value").value == source
            load.assert_not_called()
            screen.button(key="convert_text").click().run()
            assert not screen.exception
            assert screen.session_state["result_html"] == expected
            assert screen.session_state["result_assignment_metadata"]["edition_id"] == edition
            expected_path = editions.resolve_path(app / "app_data", "pure", edition)
            assert Path(load.call_args.args[0]) == expected_path
            assert load.call_count == 1
            load.reset_mock()

            edited = expected + "!"
            screen.text_area(key="edited_html").set_value(edited).run()
            screen.button(key="confirm_download").click().run()
            assert not screen.exception
            params = next(call.kwargs for call in reversed(download.call_args_list)
                          if call.kwargs.get("key") == "confirmed_result_download")
            assert params["data"] == edited.encode("utf-8")
            assert edition in params["file_name"] and params["mime"] == "text/plain"
            load.assert_not_called()

        # The upload is validated immediately and is independent of both editions.
        payload = json.dumps({editions.GLOBAL: [["saluton", "CUSTOM", "$987654$"]]}).encode()
        real_uploader = st.file_uploader

        def custom_upload(*args, **kwargs):
            if kwargs.get("key") == "main_cor_upload":
                return real_uploader(*args, **kwargs)
            return io.BytesIO(payload)

        with patch.object(st, "file_uploader", side_effect=custom_upload):
            radio = screen.radio(key="_conversion_mode_widget")
            radio.set_value(radio.options[3]).run()
            screen.text_area(key="text0_value").set_value("saluton").run()
            screen.button(key="convert_text").click().run()
            assert not screen.exception
            assert "CUSTOM" in screen.session_state["result_html"]
            assert screen.session_state["result_assignment_metadata"]["source_id"] == "custom_json"
            load.assert_not_called()


class LazyDictionaryTests(unittest.TestCase):
    def test_language_apps(self):
        for language in ("JA", "ZH", "KO"):
            with self.subTest(language=language):
                subprocess.run([sys.executable, str(Path(__file__).resolve()), language], check=True)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("JA", "ZH", "KO"):
        exercise_language(sys.argv[1])
    else:
        unittest.main()

