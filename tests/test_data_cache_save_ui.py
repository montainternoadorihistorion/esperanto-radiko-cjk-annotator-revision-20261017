"""Existing UI smoke plus actual session-only manual-save flow for one language.

Run each language in a separate process. No user correction file is written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from app_ui_smoke import ROOT, run_language, run_from_root, public_message


def check(language):
    from streamlit.testing.v1 import AppTest
    app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    manual = next((app / "pages").glob("1_*.py"))
    source_paths = [app / "main.py", manual, app / "esp_overlay_module.py"]
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    baseline_file = app / "app_data/user_corrections.json"
    baseline_bytes = baseline_file.read_bytes()
    assert json.loads(baseline_bytes) == [], "Bundled correction baseline was expected empty"
    smoke = run_language(language)
    at = run_from_root(AppTest.from_file((app / "main.py").relative_to(ROOT), default_timeout=120))
    page = run_from_root(at.switch_page(manual.relative_to(app).as_posix()))
    page.text_input(key="word_probe").set_value("lasi")
    page.button[0].click()  # Populate both page JSON caches before saving.
    run_from_root(page)
    saves = []
    for decomposition, word, display in (("las/i", "lasi", "放"), ("emancip/o", "emancipo", "放ᴱ")):
        page.text_input(key="decomp_in").set_value(decomposition)
        run_from_root(page)
        button = next(button for button in page.button if str(button.label).startswith("✅"))
        button.click()
        run_from_root(page)
        assert page.success, "The save action did not report success"
        entries = page.session_state["user_corrections_session"]
        entry = next(entry for entry in entries if entry.get("word") == word)
        assert entry["decomp"] == decomposition
        assert display in entry["kanji"][0][1]
        assert baseline_file.read_bytes() == baseline_bytes, "AppTest changed the bundled correction file"
        saves.append({"decomposition": decomposition, "word": word, "passed": True,
                      "session_entry": entry, "baseline_file_unchanged": True,
                      "success_message": page.success[0].value})
    run_from_root(at.switch_page("main.py"))
    at.radio[0].set_value(at.radio[0].options[2])
    run_from_root(at)
    at.text_area(key="text0_value").set_value("lasi emancipo")
    next(button for button in at.button if str(button.key).startswith("FormSubmitter:profile_form-")).click()
    run_from_root(at)
    assert at.session_state["result_html"] == "放i 放ᴱo"
    assert baseline_file.read_bytes() == baseline_bytes
    assert hashes == {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    return {"passed": True, "language": language, "smoke": smoke, "manual_saves": saves,
            "after_save_main_pure": at.session_state["result_html"],
            "bundled_corrections": [], "bundled_correction_file_unchanged": True,
            "source_sha256": hashes, "method": "Streamlit AppTest; isolated session, no browser or Cloud operation"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", required=True, choices=("JA", "ZH", "KO"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check(args.language)
    except Exception as exc:
        result = {"passed": False, "language": args.language, "error": public_message(exc)}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"language": args.language, "passed": result["passed"],
                      "error": result.get("error")}, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)
