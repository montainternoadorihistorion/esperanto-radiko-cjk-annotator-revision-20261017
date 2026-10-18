"""Input persistence does not reactivate results from a different workflow."""
from pathlib import Path
from unittest.mock import patch
import io

import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app


FIXTURES = Path(__file__).parent / "fixtures" / "html_recovery"
EXPECTED_HTML = "dekdu etilo magneto sene\nsemajno 再见 @literala@ <b>&amp;</b>\nĈapelo ĉapelo ĉapelo  fino\nFino\n"


def start():
    at = AppTest.from_file(app.__file__, default_timeout=30).run()
    assert not at.exception
    return at


def plain_save_control(at):
    return at.button(key="plain_prepare_save")


def html_save_controls(at):
    return [b for b in at.button if b.key == "html_recovery_prepare_save"]


@pytest.mark.parametrize("edition,expected", [("pejvo-piv-20260620", "lasis"), ("pre-las-20261017", "emancipis")])
def test_plain_result_is_readonly_and_downloads_the_visible_text(edition, expected):
    captured = []
    original = app.st.download_button

    def capture(*args, **kwargs):
        if kwargs.get("label", args[0] if args else "") in ("テキストをダウンロード", "📥 下载文本"):
            captured.append(kwargs)
        return original(*args, **kwargs)

    with patch.object(app.st, "download_button", side_effect=capture):
        at = start()
        at.sidebar.selectbox(key="plain_edition").set_value(edition).run()
        at.text_area(key="plain_input_text").set_value("放is")
        at.button[0].click().run()
        assert not result_downloads(at)
        at.button(key="plain_prepare_save").click().run()
    assert not at.exception
    assert at.text_area[-1].disabled
    assert at.text_area[-1].value == expected == captured[-1]["data"].decode("utf-8")
    assert not captured[-1].get("disabled", False)
    assert captured[-1]["on_click"] == "ignore"
    assert captured[-1]["file_name"] == at.session_state[app.CONVERTED_PROVENANCE_KEY]["result_filename"]
    at.button(key="close_result_save_dialog").click().run()
    assert not at.exception
    assert at.text_area(key="plain_input_text").value == "放is"
    assert at.sidebar.selectbox(key="plain_edition").value == edition
    assert not result_downloads(at)
    assert not plain_save_control(at).disabled


def result_downloads(at):
    return [b for b in at.get("download_button")
            if b.proto.label in ("テキストをダウンロード", "📥 下载文本",
                                 "復元した原語をダウンロード", "下载还原的原文")]


@pytest.mark.parametrize("edition", ["pejvo-piv-20260620", "pre-las-20261017"])
@pytest.mark.parametrize("change", ["input", "edition"])
def test_plain_save_click_validates_pending_changes_before_opening_dialog(edition, change):
    at = start()
    at.sidebar.selectbox(key="plain_edition").set_value(edition).run()
    at.text_area(key="plain_input_text").set_value("放is")
    at.button[0].click().run()
    prepare = plain_save_control(at)
    assert not prepare.disabled
    if change == "input":
        at.text_area(key="plain_input_text").set_value("留is 新a原稿")
    else:
        other = "pre-las-20261017" if edition == "pejvo-piv-20260620" else "pejvo-piv-20260620"
        at.sidebar.selectbox(key="plain_edition").set_value(other)
    # Simulate the edit and save click arriving together, without an earlier
    # rerun that would already have disabled the old visible save control.
    prepare.click().run()
    assert not at.exception
    assert plain_save_control(at).disabled
    assert not result_downloads(at)
    assert not [t for t in at.text_area if t.key == "result_save_preview"]


@pytest.mark.parametrize("direction", ["kanji", "annotation"])
def test_html_dialog_snapshot_and_close_preserve_source(direction):
    source = (FIXTURES / f"standard_{direction}.html").read_text(encoding="utf-8")
    captured = []
    original = app.st.download_button

    def capture(*args, **kwargs):
        if kwargs.get("key") == "html_recovery_download":
            captured.append(kwargs)
        return original(*args, **kwargs)

    with patch.object(app.st, "download_button", side_effect=capture):
        at = start()
        at.radio(key="reverter_input_mode").set_value("html").run()
        at.radio(key="html_recovery_direction").set_value(direction).run()
        at.text_area(key="html_recovery_paste").set_value(source)
        at.button(key="html_recovery_submit").click().run()
        assert not result_downloads(at)
        at.button(key="html_recovery_prepare_save").click().run()
    assert not at.exception
    assert captured[-1]["data"] == EXPECTED_HTML.encode("utf-8")
    assert captured[-1]["on_click"] == "ignore"
    assert at.text_area(key="result_save_preview").value == EXPECTED_HTML
    assert at.text_area(key="result_save_preview").disabled
    at.button(key="close_result_save_dialog").click().run()
    assert not at.exception
    assert not result_downloads(at)
    assert at.text_area(key="html_recovery_paste").value == source
    assert at.radio(key="html_recovery_direction").value == direction
    assert at.radio(key="html_recovery_source_kind").value == "paste"
    assert html_save_controls(at)


@pytest.mark.parametrize("change", ["source", "direction", "source-kind"])
def test_html_save_click_rejects_pending_source_or_mode_changes(change):
    source = (FIXTURES / "standard_kanji.html").read_text(encoding="utf-8")
    at = start()
    at.radio(key="reverter_input_mode").set_value("html").run()
    at.text_area(key="html_recovery_paste").set_value(source)
    at.button(key="html_recovery_submit").click().run()
    prepare = at.button(key="html_recovery_prepare_save")
    if change == "source":
        at.text_area(key="html_recovery_paste").set_value(source + "\n<!-- source edited -->")
    elif change == "direction":
        at.radio(key="html_recovery_direction").set_value("annotation")
    else:
        at.radio(key="html_recovery_source_kind").set_value("upload")
    prepare.click().run()
    assert not at.exception
    assert not html_save_controls(at)
    assert not result_downloads(at)
    assert not [t for t in at.text_area if t.key == "result_save_preview"]


@pytest.mark.parametrize("edition", ["pejvo-piv-20260620", "pre-las-20261017"])
def test_plain_html_plain_preserves_draft_and_edition_but_invalidates_result(edition):
    at = start()
    at.sidebar.selectbox(key="plain_edition").set_value(edition).run()
    original = "  放is mia frazo.\n\n@restas@  "
    at.text_area(key="plain_input_text").set_value(original)
    at.button[0].click().run()
    converted = at.text_area[-1].value
    assert not plain_save_control(at).proto.disabled
    at.radio(key="reverter_input_mode").set_value("html").run()
    assert not at.sidebar.selectbox
    at.radio(key="reverter_input_mode").set_value("plain").run()
    assert not at.exception
    assert at.sidebar.selectbox(key="plain_edition").value == edition
    assert at.text_area(key="plain_input_text").value == original
    assert plain_save_control(at).proto.disabled
    at.button[0].click().run()
    assert at.text_area[-1].value == converted
    assert not plain_save_control(at).proto.disabled
    # A new, unconverted draft must also survive widget cleanup.
    draft = "未変換の原稿\n  下一行"
    at.text_area(key="plain_input_text").set_value(draft).run()
    assert plain_save_control(at).proto.disabled
    at.radio(key="reverter_input_mode").set_value("html").run()
    at.radio(key="reverter_input_mode").set_value("plain").run()
    assert at.text_area(key="plain_input_text").value == draft
    assert at.sidebar.selectbox(key="plain_edition").value == edition
    assert plain_save_control(at).proto.disabled


def test_html_paste_direction_and_source_choice_survive_hiding():
    source = (FIXTURES / "standard_annotation.html").read_text(encoding="utf-8")
    at = start()
    at.radio(key="reverter_input_mode").set_value("html").run()
    at.radio(key="html_recovery_direction").set_value("annotation").run()
    at.text_area(key="html_recovery_paste").set_value(source)
    at.button(key="html_recovery_submit").click().run()
    assert at.session_state["html_recovery_result"]["text"] == EXPECTED_HTML
    at.radio(key="html_recovery_source_kind").set_value("upload").run()
    assert not html_save_controls(at)
    at.radio(key="reverter_input_mode").set_value("plain").run()
    at.radio(key="reverter_input_mode").set_value("html").run()
    assert at.radio(key="html_recovery_direction").value == "annotation"
    assert at.radio(key="html_recovery_source_kind").value == "upload"
    assert not html_save_controls(at)
    at.radio(key="html_recovery_source_kind").set_value("paste").run()
    assert at.text_area(key="html_recovery_paste").value == source
    assert not html_save_controls(at)
    at.button(key="html_recovery_submit").click().run()
    assert at.session_state["html_recovery_result"]["text"] == EXPECTED_HTML


def file_upload(raw, name="remembered.html"):
    value = io.BytesIO(raw)
    value.name = name
    value.size = len(raw)
    return value


def upload(at, file, changed=True):
    # AppTest does not implement file upload interaction. Invoke the actual
    # registered callback for a file-change event in the Streamlit run context.
    def widget(*args, **kwargs):
        if changed:
            kwargs["on_change"]()
        return file
    with patch.object(app.st, "file_uploader", side_effect=widget):
        at.run()
    assert not at.exception


def test_validated_html_upload_is_restored_and_can_be_explicitly_forgotten():
    source = (FIXTURES / "standard_kanji.html").read_text(encoding="utf-8")
    at = start()
    at.radio(key="reverter_input_mode").set_value("html").run()
    at.radio(key="html_recovery_source_kind").set_value("upload").run()
    upload(at, file_upload(source.encode("utf-8")))
    at.button(key="html_recovery_submit").click().run()
    assert at.session_state["html_recovery_result"]["text"] == EXPECTED_HTML
    at.radio(key="reverter_input_mode").set_value("plain").run()
    at.radio(key="reverter_input_mode").set_value("html").run()
    assert at.radio(key="html_recovery_source_kind").value == "upload"
    assert any("remembered.html" in c.value for c in at.caption)
    assert not html_save_controls(at)
    at.button(key="html_recovery_submit").click().run()
    assert at.session_state["html_recovery_result"]["text"] == EXPECTED_HTML
    at.button(key="html_recovery_forget_upload").click().run()
    assert at.button(key="html_recovery_submit").disabled
    assert not html_save_controls(at)
    assert "saved_html_recovery_file" not in at.session_state


@pytest.mark.parametrize("replacement", [None, b"\xff", b"a" * (10 * 1024 * 1024 + 1)],
                         ids=["removed", "invalid-utf8", "oversized"])
def test_removed_invalid_or_oversized_html_never_falls_back_to_previous_file(replacement):
    source = (FIXTURES / "standard_kanji.html").read_bytes()
    at = start()
    at.radio(key="reverter_input_mode").set_value("html").run()
    at.radio(key="html_recovery_source_kind").set_value("upload").run()
    upload(at, file_upload(source))
    at.button(key="html_recovery_submit").click().run()
    assert html_save_controls(at)
    upload(at, None if replacement is None else file_upload(replacement, "replacement.html"))
    assert at.button(key="html_recovery_submit").disabled
    assert not html_save_controls(at)
    assert "saved_html_recovery_file" not in at.session_state
    at.radio(key="reverter_input_mode").set_value("plain").run()
    at.radio(key="reverter_input_mode").set_value("html").run()
    assert at.button(key="html_recovery_submit").disabled
    assert not html_save_controls(at)


def test_custom_csv_choice_survives_without_silently_using_standard_dictionary():
    at = start()
    at.sidebar.selectbox(key="plain_edition").set_value("pre-las-20261017").run()
    at.checkbox(key="use_custom_csv").check().run()
    custom = file_upload(b"bon,\xe8\x89\xaf\n", "custom.csv")
    with patch.object(app.st, "file_uploader", side_effect=lambda *a, **k: (custom.seek(0), custom)[1]):
        at.run()
        at.text_area(key="plain_input_text").set_value("良a")
        at.button[0].click().run()
    assert at.text_area[-1].value == "bona"
    at.radio(key="reverter_input_mode").set_value("html").run()
    at.radio(key="reverter_input_mode").set_value("plain").run()
    assert not at.exception
    assert at.checkbox(key="use_custom_csv").value
    assert at.sidebar.selectbox(key="plain_edition").value == "pre-las-20261017"
    assert at.sidebar.selectbox(key="plain_edition").disabled
    assert at.text_area(key="plain_input_text").value == "良a"
    assert not at.get("download_button")
    at.checkbox(key="use_custom_csv").uncheck().run()
    assert at.sidebar.selectbox(key="plain_edition").value == "pre-las-20261017"
    assert plain_save_control(at).proto.disabled
