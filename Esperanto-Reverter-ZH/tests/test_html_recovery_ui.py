"""HTML input stays separate from dictionary conversion and stale downloads."""
from pathlib import Path
from unittest.mock import patch
import io
import re

import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter_zh as app


FIXTURES = Path(__file__).parent / "fixtures" / "html_recovery"
EXPECTED = (
    "dekdu etilo magneto sene\n"
    "semajno 再见 @literala@ <b>&amp;</b>\n"
    "Ĉapelo ĉapelo ĉapelo  fino\nFino\n"
)


def fixture(direction="kanji", edition="current"):
    source = (FIXTURES / f"standard_{direction}.html").read_text(encoding="utf-8")
    if edition == "unknown":
        return re.sub(r"\A<!--.*?-->\n", "", source, count=1)
    return source.replace("assignment-edition:current", f"assignment-edition:{edition}", 1)


def start_html():
    at = AppTest.from_file(app.__file__, default_timeout=30).run()
    assert not at.exception
    assert at.radio(key="reverter_input_mode").value == "plain"
    assert at.sidebar.selectbox[0].options == ["新版（更新中）", "旧版（固定）"]
    at.radio(key="reverter_input_mode").set_value("html").run()
    assert not at.exception
    assert not at.sidebar.selectbox
    assert not at.get("download_button")
    return at


def convert(at, source, direction="kanji"):
    at.radio(key="html_recovery_direction").set_value(direction).run()
    at.text_area(key="html_recovery_paste").set_value(source)
    at.button(key="html_recovery_submit").click().run()
    assert not at.exception
    return at.session_state["html_recovery_result"]


@pytest.mark.parametrize("direction", ["kanji", "annotation"])
@pytest.mark.parametrize("edition", ["current", "legacy", "unknown"])
def test_actual_standard_html_and_download_preserve_source(direction, edition):
    captured = []
    original = app.st.download_button

    def capture(*args, **kwargs):
        if kwargs.get("key") == "html_recovery_download":
            captured.append(kwargs)
        return original(*args, **kwargs)

    with patch.object(app.st, "download_button", side_effect=capture):
        at = start_html()
        result = convert(at, fixture(direction, edition), direction)
    assert result["text"] == EXPECTED
    assert result["assignment_edition"] == edition
    assert result["mode"] == direction
    assert result["ruby_count"] > 0
    assert len(at.get("download_button")) == 1
    assert at.text_area[-1].value == EXPECTED and at.text_area[-1].disabled
    assert captured[-1]["data"] == EXPECTED.encode("utf-8")
    assert captured[-1]["file_name"].startswith(f"esperanto_html_{edition}_{direction}_")
    edition_words = {"current": ("新版",), "legacy": ("旧版",), "unknown": ("不明", "未知")}[edition]
    assert any(any(word in caption.value for word in edition_words) for caption in at.caption)


def test_input_direction_source_and_mode_changes_remove_html_download():
    at = start_html()
    convert(at, fixture())
    assert at.get("download_button")
    at.text_area(key="html_recovery_paste").set_value(fixture(edition="legacy")).run()
    assert not at.get("download_button")
    at.button(key="html_recovery_submit").click().run()
    assert at.session_state["html_recovery_result"]["assignment_edition"] == "legacy"
    at.radio(key="html_recovery_direction").set_value("annotation").run()
    assert not at.get("download_button")
    convert(at, fixture("annotation"), "annotation")
    at.radio(key="html_recovery_source_kind").set_value("upload").run()
    assert not at.get("download_button") and not at.text_area
    at.radio(key="html_recovery_source_kind").set_value("paste").run()
    assert not at.get("download_button")
    convert(at, fixture())
    at.radio(key="reverter_input_mode").set_value("plain").run()
    assert not at.exception
    assert not any(button.proto.label in ("復元した原語をダウンロード", "下载还原的原文") for button in at.get("download_button"))
    at.radio(key="reverter_input_mode").set_value("html").run()
    assert not at.get("download_button")


def upload_file(raw):
    file = io.BytesIO(raw)
    file.name = "same_name.html"
    file.size = len(raw)
    return file


def test_upload_content_switch_and_invalid_utf8_cannot_reuse_result():
    at = start_html()
    at.text_area(key="html_recovery_paste").set_value("ignored paste").run()
    at.radio(key="html_recovery_source_kind").set_value("upload").run()
    current = upload_file(b"\xef\xbb\xbf" + fixture().encode("utf-8"))
    with patch.object(app.st, "file_uploader", return_value=current):
        at.run()
        at.button(key="html_recovery_submit").click().run()
    assert not at.exception
    assert at.session_state["html_recovery_result"]["text"] == EXPECTED
    assert at.get("download_button")
    old = upload_file(b"\xef\xbb\xbf" + fixture(edition="legacy").replace(" signature:", "  signature:", 1).encode("utf-8"))
    assert old.size == current.size and old.name == current.name
    with patch.object(app.st, "file_uploader", return_value=old):
        at.run()
        assert not at.get("download_button")
        at.button(key="html_recovery_submit").click().run()
    assert at.session_state["html_recovery_result"]["assignment_edition"] == "legacy"
    with patch.object(app.st, "file_uploader", return_value=upload_file(b"\xff")):
        at.run()
    assert not at.exception and at.error
    assert at.button(key="html_recovery_submit").disabled
    assert not at.get("download_button")


def test_parse_failure_does_not_offer_previous_success():
    at = start_html()
    convert(at, fixture())
    at.text_area(key="html_recovery_paste").set_value("This is plain text")
    at.button(key="html_recovery_submit").click().run()
    assert not at.exception and at.error
    assert not at.get("download_button")


def test_html_mode_bypasses_dictionary_sidebar_loading_and_conversion():
    # Execute the actual main() with its default independent HTML branch.
    source = f"import {app.__name__} as app\napp.main()"
    at = AppTest.from_string(source, default_timeout=30)
    at.session_state["reverter_input_mode"] = "html"
    with patch.object(app, "render_sidebar", side_effect=AssertionError("dictionary sidebar used")), \
         patch.object(app, "load_selected_dataframe", side_effect=AssertionError("dictionary loaded")), \
         patch.object(app, "convert_kanji_esperanto_to_alphabet", side_effect=AssertionError("plain inverse used")):
        at.run()
        convert(at, fixture())
    assert not at.exception
    assert at.session_state["html_recovery_result"]["text"] == EXPECTED
