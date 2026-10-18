"""Real forward AppTests; each language runs in an isolated Python process.

Only source-file upload and download transport are instrumented. The app's
conversion functions, dictionaries, overlays and Streamlit state run unchanged.
"""

import argparse
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("JA", "ZH", "KO")
DOWNLOAD_LABELS = {
    "JA": "置換結果のダウンロード（編集を反映）",
    "ZH": "下载转换结果（已反映编辑）",
    "KO": "치환 결과 다운로드(편집 반영)",
}


def check_language(language):
    logging.disable(logging.WARNING)
    from streamlit.testing.v1 import AppTest
    import streamlit as st

    app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    sys.path.insert(0, str(app))
    sys.path.insert(1, str(ROOT / "Esperanto-Reverter-JA"))
    os.chdir(ROOT)
    import esp_assignment_edition as editions
    from html_source_recovery import recover_standard_html

    fixture = json.loads((ROOT / "tests/ksen_pure_fix/cloud_fixture.json").read_text("utf-8"))
    fixture_rows = {(r["edition"], r["mode"]): r for r in fixture["rows"]
                    if r["forward_language"] == language}
    source = next(iter(fixture_rows.values()))["input"]
    normalized_source = source.replace("@", "").replace("%", "")
    corrections = app / "app_data/user_corrections.json"
    correction_bytes = corrections.read_bytes()
    uploads = {"file": None}
    captured = []
    checks = []
    conversions = []
    original_download = st.download_button
    original_upload = st.file_uploader

    def upload(label, *args, **kwargs):
        if kwargs.get("key") == "_source_text_upload":
            return uploads["file"]
        return original_upload(label, *args, **kwargs)

    def download(label, data, *args, **kwargs):
        if label == DOWNLOAD_LABELS[language]:
            captured.append({"data": data if isinstance(data, bytes) else data.encode("utf-8"),
                             "filename": kwargs["file_name"], "mime": kwargs["mime"],
                             "on_click": kwargs.get("on_click")})
        return original_download(label, data, *args, **kwargs)

    def file(raw, identity):
        result = io.BytesIO(raw)
        result.file_id = identity
        result.name = identity + ".txt"
        result.size = len(raw)
        return result

    at = AppTest.from_file(app / "main.py", default_timeout=180)

    def run(allow_errors=False):
        captured.clear()
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        if not allow_errors:
            assert not at.error, [e.value for e in at.error]
        assert Path.cwd() == ROOT

    def no_download(reason):
        assert not captured, (reason, captured)
        assert not any(w.key == "edited_html" for w in at.text_area), reason
        assert not any(w.key == "confirm_download" for w in at.button), reason
        checks.append(reason)

    def verify_download(edition, mode, expected=None):
        assert not captured, "The editing page must never contain a native result download"
        at.button(key="confirm_download").click()
        run()
        assert len(captured) == 1, (edition, mode, captured)
        assert captured[0]["on_click"] == "ignore"
        result = at.session_state["result_html"]
        if expected is not None:
            assert result == expected, (language, edition, mode, result, expected)
        metadata = dict(at.session_state["result_assignment_metadata"])
        assert metadata["edition_id"] == edition
        edited = at.text_area(key="edited_html").value
        prefix = "" if mode == "pure" else editions.html_download_metadata(metadata)
        assert captured[0]["data"] == (prefix + edited).encode("utf-8")
        extension = "txt" if mode == "pure" else "html"
        assert captured[0]["mime"] == ("text/plain" if mode == "pure" else "text/html")
        assert captured[0]["filename"].endswith(f'_{edition}_{metadata["signature"][:12]}.{extension}')
        conversions.append({"edition": edition, "mode": mode,
                            "input": at.text_area(key="text0_value").value,
                            "result_sha256": hashlib.sha256(result.encode()).hexdigest(),
                            "download_sha256": hashlib.sha256(captured[0]["data"]).hexdigest(),
                            "mime": captured[0]["mime"], "filename": captured[0]["filename"]})
        # A full rerun on dismissal removes the dialog and its immutable download.
        run()
        assert not captured, "Closing confirmation must require preparing again"

    with patch.object(st, "download_button", side_effect=download), patch.object(st, "file_uploader", side_effect=upload):
        run()
        assert not at.get("form"), "Input must synchronize before a separate download action"
        for edition in ("current", "legacy"):
            at.selectbox(key="_assignment_edition_widget").set_value(edition)
            run()
            for mode, option in (("pure", 2), ("kanji", 1), ("ruby", 0)):
                mode_options = at.radio(key="_conversion_mode_widget").options
                at.radio(key="_conversion_mode_widget").set_value(mode_options[option])
                run()
                at.text_area(key="text0_value").set_value(source)
                at.button(key="convert_text").click()
                run()
                expected = fixture_rows[(edition, mode)]["rendered"] if mode != "ruby" else None
                verify_download(edition, mode, expected)
                if mode == "ruby":
                    assert recover_standard_html(at.session_state["result_html"], "annotation")["text"] == normalized_source
                # Edited output is kept while hidden, and its bytes are actually saved.
                edited = at.text_area(key="edited_html").value + "\nSAVED EDIT"
                at.text_area(key="edited_html").set_value(edited)
                run()
                verify_download(edition, mode)
                next(b for b in at.button if b.label.startswith("📝")).click()
                run()
                assert at.text_area(key="text0_value").value.startswith("Saluton!")
                no_download(f"{edition}/{mode}: sample invalidates previous input")
                at.text_area(key="text0_value").set_value(source)
                run()
                assert at.text_area(key="edited_html").value == edited
                verify_download(edition, mode)
                at.text_area(key="text0_value").set_value(source + "\n%ALIO%")
                # Send the pending input and the confirmation click together.
                at.button(key="confirm_download").click()
                run()
                no_download(f"{edition}/{mode}: direct edit invalidates previous input")
                assert at.session_state["_text0_keep"] == source + "\n%ALIO%"
                print(language, edition, mode, "conversion/download/input guards PASS", flush=True)

            # Upload transport is instrumented; strict decoding and all app state are real.
            uploads["file"] = file(b"lasis @lasis@", "valid-source")
            source_options = at.radio(key="_source_option_widget").options
            at.radio(key="_source_option_widget").set_value(source_options[1])
            run()
            assert at.text_area(key="text0_value").value == "lasis @lasis@"
            no_download(f"{edition}: valid upload replaces input and invalidates old result")
            at.button(key="convert_text").click()
            run()
            verify_download(edition, "ruby")
            assert recover_standard_html(at.session_state["result_html"], "annotation")["text"] == "lasis lasis"
            at.text_area(key="text0_value").set_value("semajno @semajno@")
            run()
            no_download(f"{edition}: editing uploaded text invalidates download")
            assert at.text_area(key="text0_value").value == "semajno @semajno@", "Unchanged upload must not overwrite an edited draft"
            at.button(key="convert_text").click()
            run()
            verify_download(edition, "ruby")
            assert recover_standard_html(at.session_state["result_html"], "annotation")["text"] == "semajno semajno"

            # Same transport id, different bytes: content identity is checked too.
            uploads["file"] = file(b"testikito @testikito@", "valid-source")
            run()
            assert at.text_area(key="text0_value").value == "testikito @testikito@"
            no_download(f"{edition}: changed upload bytes invalidate result")
            uploads["file"] = file(b"Mi \xff lasis.", "invalid-source")
            run(allow_errors=True)
            assert at.error and at.button(key="convert_text").disabled
            assert at.text_area(key="text0_value").value == "testikito @testikito@"
            no_download(f"{edition}: invalid UTF8 preserves draft and blocks conversion/save")
            uploads["file"] = file(b"", "empty-source")
            run()
            assert at.text_area(key="text0_value").value == ""
            no_download(f"{edition}: valid empty file clears draft and old download")
            at.button(key="convert_text").click()
            run()
            assert at.warning
            no_download(f"{edition}: empty conversion cannot expose old download")

            uploads["file"] = file("Ĉapelo @ĉapelo@".encode("utf-8-sig"), "bom-source")
            run()
            assert at.text_area(key="text0_value").value == "Ĉapelo @ĉapelo@"
            uploads["file"] = None
            run()
            assert at.button(key="convert_text").disabled
            assert at.text_area(key="text0_value").value == "Ĉapelo @ĉapelo@"
            no_download(f"{edition}: removing upload preserves draft and blocks conversion/save")

            # An early stop removes widgets; separate draft/choice keys must survive.
            letters = at.radio(key="_letter_type_widget").options
            at.radio(key="_letter_type_widget").set_value(letters[1])
            at.text_area(key="text0_value").set_value("DRAFT @semajno@")
            at.radio(key="_conversion_mode_widget").set_value(mode_options[3])
            run()
            assert at.session_state["_text0_keep"] == "DRAFT @semajno@"
            assert at.session_state["assignment_edition"] == edition
            assert not any(w.key == "text0_value" for w in at.text_area)
            at.radio(key="_conversion_mode_widget").set_value(mode_options[0])
            run()
            assert at.text_area(key="text0_value").value == "DRAFT @semajno@"
            assert at.radio(key="_source_option_widget").value == source_options[1]
            assert at.radio(key="_letter_type_widget").value == letters[1]
            assert at.selectbox(key="_assignment_edition_widget").value == edition
            no_download(f"{edition}: early-stop mode switch retains input/source/letters/edition")
            at.radio(key="_source_option_widget").set_value(source_options[0])
            at.radio(key="_letter_type_widget").set_value(letters[0])
            run()
            assert at.text_area(key="text0_value").value == "DRAFT @semajno@"
            assert not at.button(key="convert_text").disabled
            no_download(f"{edition}: manual input retains draft after upload switch")
            print(language, edition, "uploads and draft retention PASS", flush=True)
        assert corrections.read_bytes() == correction_bytes
    return {"passed": True, "language": language, "conversions": conversions, "state_checks": checks,
            "bundled_corrections_unchanged": True,
            "method": "Local real Streamlit AppTest; actual engines/data; mocked source-file and download transport only"}


class ForwardInputResultTests(unittest.TestCase):
    def test_all_languages_in_isolated_processes(self):
        for language in LANGUAGES:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                report = Path(folder) / "result.json"
                completed = subprocess.run(
                    [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                     "--language", language, "--report", str(report)],
                    cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=900,
                )
                self.assertEqual(completed.returncode, 0, completed.stdout[-5000:] + completed.stderr[-5000:])
                self.assertTrue(json.loads(report.read_text("utf-8"))["passed"])


if __name__ == "__main__":
    if "--language" not in sys.argv:
        unittest.main()
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--language", required=True, choices=LANGUAGES)
        parser.add_argument("--report", required=True, type=Path)
        args = parser.parse_args()
        try:
            result = check_language(args.language)
        except Exception as exc:
            result = {"passed": False, "language": args.language, "error": str(exc),
                      "traceback": traceback.format_exc()}
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: result[k] for k in ("passed", "language", "error") if k in result}, ensure_ascii=False))
        raise SystemExit(0 if result["passed"] else 1)
