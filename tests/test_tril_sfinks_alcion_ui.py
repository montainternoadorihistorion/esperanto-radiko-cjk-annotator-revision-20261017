"""Local AppTest checks for tril, sfinks, alcion and alced reviewed assignments, editions and download bytes.

The --before-root must be an immutable pre-change application snapshot.
Only file-upload and download transport is observed or supplied; conversion and Streamlit state are real.
Reports are explicit local evidence, never observations of Streamlit Cloud.
"""
import argparse
import gc
import hashlib
import io
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback
from unittest.mock import patch

logging.disable(logging.WARNING)
SOURCE = (
    "Triloj kaj SFINKSOJ. Alcionoj kaj ALCEDOJ.\n"
    "@tril@o @sfinks@o @alcion@o @alced@o\n"
    "trila sfinksa alciona alceda trili sfinksi alcioni alcedi\n"
    "trile sfinkse alciono alcedo; @tril@ @sfinks@ @alcion@ @alced@\n"
    "trilobito sfinktero; grifelo brava frivola animalo\n"
    "mikrobiologio @mikrobiologi@o semajno @semajn@o testikito orkidito\n"
    "%trilo% & du  spacoj"
)
CUSTOM_SOURCE = "trilo sfinkso alciono alcedo\n@tril@o @sfinks@o @alcion@o @alced@o"
VALUES = {
    "tril": ("颤歌", "颤音"),
    "sfinks": ("狮面", "人面狮"),
    "alcion": ("翠鸟", "鸟ᴬᴸ"),
    "alced": ("鸟ᴬᴸ", "鸟ᴬᴰ"),
}
CONTROLS = {"grifel": "石笔", "brav": "勇ᴮ", "frivol": "轻浮", "animal": "兽ᴬ"}
FORMATS = {
    "pure": "替换后文字列のみ(仅)保留(简单替换)",
    "kanji": "HTML格式_Ruby文字_大小调整_汉字替换",
    "ruby": "HTML格式_Ruby文字_大小调整",
}
LABELS = {
    "JA": "置換結果のダウンロード（編集を反映）",
    "ZH": "下载转换结果（已反映编辑）",
    "KO": "치환 결과 다운로드(편집 반영)",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def prepare_baseline(root, language):
    app = root / f"Esperanto-Kanji-Ruby-{language}"
    sys.path.insert(0, str(app))
    data = app / "app_data"
    ed = load(app / "esp_assignment_edition.py", "tsa_baseline_ed")
    rt = load(app / "esp_text_replacement_module.py", "tsa_baseline_rt")
    ov = load(app / "esp_overlay_module.py", "tsa_baseline_ov")
    skip = rt.import_placeholders(str(data / "placeholders_skip.txt"))
    local = rt.import_placeholders(str(data / "placeholders_localcapture.txt"))
    rows = []

    def strip(value):
        return re.sub(r"</?ruby>", "", re.sub(r"<rt[^>]*>.*?</rt>", "", value, flags=re.S))

    for edition in ("current", "legacy"):
        for mode in ("pure", "kanji", "ruby"):
            global_rules, local_rules, two_rules = ed.load_lists(data, mode, edition)
            overlay_mode = "kanji" if mode == "pure" else mode
            overlay = ov.load_overlay_entries(str(data), overlay_mode, edition)
            if mode == "pure":
                overlay = [[a, strip(b), c] for a, b, c in overlay]
            global_rules = ov.merge_overlay(global_rules, overlay)

            def convert(rules):
                return rt.orchestrate_comprehensive_esperanto_text_replacement(
                    SOURCE, skip, local_rules, local, rules, two_rules, FORMATS[mode],
                    reviewed_local_decompositions=True,
                )

            first = convert(global_rules)
            automatic = ov.auto_overlay_entries(first, str(data), overlay_mode, edition)
            if mode == "pure":
                automatic = [[a, strip(b), c] for a, b, c in automatic]
            value = convert(ov.merge_overlay(global_rules, automatic)) if automatic else first
            rendered = rt.apply_ruby_html_header_and_footer(value, FORMATS[mode])
            if mode == "pure":
                for root in VALUES:
                    assert VALUES[root][0] in rendered, (edition, root, rendered)
                assert all(value not in rendered for value in ("颤音", "人面狮", "鸟ᴬᴰ")), "Snapshot is not before the change"
                assert all(value in rendered for value in CONTROLS.values())
            rows.append({"edition": edition, "mode": mode, "output": rendered})
            del global_rules, local_rules, two_rules
            ed._load_lists_cached.clear()
            gc.collect()
    # Also retain the original bundled pure JSON as an explicitly custom upload.
    # Loading it under a bundled filename must not opt into the selected edition.
    custom_path = Path(ed.resolve_path(data, "pure", "current"))
    global_rules, local_rules, two_rules = ed.load_lists(data, "pure", "current")
    custom_output = rt.orchestrate_comprehensive_esperanto_text_replacement(
        CUSTOM_SOURCE, skip, local_rules, local, global_rules, two_rules, FORMATS["pure"],
        reviewed_local_decompositions=False,
    )
    for old, _ in VALUES.values():
        assert old in custom_output
    return {"language": language, "input": SOURCE, "rows": rows, "baseline_root": str(root),
            "custom": {"input": CUSTOM_SOURCE, "output": custom_output,
                       "path": str(custom_path), "sha256": sha(custom_path.read_bytes())}}


def changed_expected(text, mode):
    if mode == "pure":
        # A single pass avoids changing newly assigned alcion=鸟ᴬᴸ again
        # into alced=鸟ᴬᴰ. This mapping is confined to this fixed fixture.
        pairs = dict(VALUES.values())
        pattern = "|".join(re.escape(old) for old in sorted(pairs, key=lambda old: -len(old)))
        return re.sub(pattern, lambda match: pairs[match[0]], text)
    if mode == "ruby":
        return text

    def replace(match):
        root = re.sub(r"<[^>]*>", "", match[3]).lower()
        if root not in VALUES:
            return match[0]
        old, new = VALUES[root]
        assert match[1] == old, (root, match[1], old)
        return "<ruby>" + new + match[2] + match[3] + "</rt></ruby>"

    return re.sub(r"<ruby>(.*?)(<rt[^>]*>)(.*?)</rt></ruby>", replace, text, flags=re.S)


def normalize_reviewed_kanji(text, after):
    seen = {root: 0 for root in VALUES}

    def replace(match):
        spelling = re.sub(r"<[^>]*>", "", match[2])
        root = spelling.lower()
        if root not in VALUES:
            return match[0]
        assert match[1] == VALUES[root][int(after)], (root, match[1])
        seen[root] += 1
        # New glyph widths legitimately change the target ruby class and
        # internal <br>. Preserve the exact recovered spelling and all
        # markup outside these four root fragments.
        return "<reviewed-root>" + spelling + "</reviewed-root>"

    neutral = re.sub(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", replace, text, flags=re.S)
    assert all(value >= 1 for value in seen.values()), seen
    return neutral


def run_ui(root, language, baseline, report_dir):
    from streamlit.testing.v1 import AppTest
    import streamlit as st

    app = root / f"Esperanto-Kanji-Ruby-{language}"
    sys.path.insert(0, str(app))
    os.chdir(root)
    import esp_assignment_edition as editions

    baseline_rows = {(r["edition"], r["mode"]): r["output"] for r in baseline["rows"]}
    correction_path = app / "app_data/user_corrections.json"
    correction_bytes = correction_path.read_bytes()
    captured = []
    original_download = st.download_button
    at = AppTest.from_file(app / "main.py", default_timeout=90)

    def download(label, data, *args, **kwargs):
        if label == LABELS[language]:
            raw = data if isinstance(data, bytes) else data.encode("utf-8")
            captured.append({"raw": raw, "filename": kwargs["file_name"],
                             "mime": kwargs["mime"], "on_click": kwargs.get("on_click")})
        return original_download(label, data, *args, **kwargs)

    def run():
        captured.clear()
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        assert not at.error, [e.value for e in at.error]
        assert Path.cwd() == root

    cases, guards = [], []
    with patch.object(st, "download_button", side_effect=download):
        run()
        for edition in ("current", "legacy"):
            at.selectbox(key="_assignment_edition_widget").set_value(edition)
            run()
            if edition == "legacy":
                assert at.text_area(key="text0_value").value == SOURCE
                assert not any(x.key == "edited_html" for x in at.text_area)
                assert not captured
                guards.append({"reason": "edition switch", "source_preserved": True,
                               "previous_result_hidden": True, "previous_download_absent": True})
            for mode, option in (("pure", 2), ("kanji", 1), ("ruby", 0)):
                at.radio(key="_conversion_mode_widget").set_value(
                    at.radio(key="_conversion_mode_widget").options[option])
                run()
                if cases:
                    assert at.text_area(key="text0_value").value == SOURCE
                    assert at.selectbox(key="_assignment_edition_widget").value == edition
                    assert not captured
                    guards.append({"reason": "mode switch", "edition": edition, "mode": mode,
                                   "source_and_edition_preserved": True, "download_absent": True})
                at.text_area(key="text0_value").set_value(SOURCE)
                at.button(key="convert_text").click()
                run()
                result = at.session_state["result_html"]
                old = baseline_rows[edition, mode]
                expected = old if edition == "legacy" else changed_expected(old, mode)
                if edition == "current" and mode == "kanji":
                    assert normalize_reviewed_kanji(result, True) == normalize_reviewed_kanji(old, False), (
                        language, edition, mode, "Unexpected change outside reviewed glyph/ruby-size fragments")
                else:
                    assert result == expected, (language, edition, mode, result, expected)
                metadata = dict(at.session_state["result_assignment_metadata"])
                assert metadata["edition_id"] == edition
                assert metadata["assignment_signature"] == editions.edition_signature(app / "app_data", edition)
                assert at.text_area(key="edited_html").value == result
                assert not captured, "Save confirmation must precede the download"
                at.button(key="confirm_download").click()
                run()
                assert len(captured) == 1
                item = captured[0]
                prefix = "" if mode == "pure" else editions.html_download_metadata(metadata)
                body = result
                if mode in ("kanji", "ruby"):
                    direction = "kanji" if mode == "kanji" else "annotation"
                    body = body.replace("</head>",
                        f'<meta name="esperanto-ruby-mode" content="{direction}">\n</head>', 1)
                assert item["raw"] == (prefix + body).encode("utf-8")
                ext = "txt" if mode == "pure" else "html"
                assert item["filename"].endswith(f'_{edition}_{metadata["signature"][:12]}.{ext}')
                assert item["mime"] == ("text/plain" if mode == "pure" else "text/html")
                assert item["on_click"] == "ignore"
                assert at.session_state["result_html"] == result
                filename = f"{language}_{edition}_{mode}.{ext}"
                (report_dir / filename).write_bytes(item["raw"])
                cases.append({"language": language, "edition": edition, "mode": mode,
                              "input": SOURCE, "output": result, "metadata": metadata,
                              "download_filename": item["filename"], "saved_evidence": filename,
                              "download_sha256": sha(item["raw"]), "output_sha256": sha(result.encode()),
                              "exact_expected_output": mode != "kanji" or edition == "legacy",
                              "reviewed_target_displays_and_other_markup_unchanged": mode == "kanji" and edition == "current",
                              "exact_download_bytes": True,
                              "legacy_unchanged": edition == "legacy",
                              "annotations_unchanged": mode == "ruby"})
                print(language, edition, mode, "PASS", flush=True)
                run()
                assert not captured
        assert correction_path.read_bytes() == correction_bytes
    custom_cases = run_custom_ui(root, language, baseline, report_dir)
    assert correction_path.read_bytes() == correction_bytes
    return {"passed": True, "language": language, "method": "Local real Streamlit AppTest",
            "custom_cases": custom_cases,
            "cases": cases, "state_guards": guards, "correction_file_unchanged": True,
            "scope": "No Cloud claim. Normal and @ conversion, related and derived forms, exact baseline annotation and legacy outputs. Existing trilobit, sfinkter and mikro/bio/logi fragments and four unchanged assignment controls remain unchanged."}


def run_custom_ui(root, language, baseline, report_dir):
    """Observe upload/download transport while executing the real application."""
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    app = root / f"Esperanto-Kanji-Ruby-{language}"
    source = baseline["custom"]
    raw = Path(source["path"]).read_bytes()
    assert sha(raw) == source["sha256"]
    original_upload, original_download = st.file_uploader, st.download_button
    captured = []
    def upload(label, *args, **kwargs):
        if kwargs.get("key") is None:
            value = io.BytesIO(raw)
            value.name = "置換リスト_漢字_純粋置換.json"
            value.file_id = "tril-sfinks-alcion-immutable-before"
            value.size = len(raw)
            return value
        return original_upload(label, *args, **kwargs)
    def download(label, data, *args, **kwargs):
        if label == LABELS[language]:
            captured.append({"raw": data if isinstance(data, bytes) else data.encode("utf-8"),
                             "filename": kwargs["file_name"], "mime": kwargs["mime"]})
        return original_download(label, data, *args, **kwargs)
    at = AppTest.from_file(app / "main.py", default_timeout=90)
    def run():
        captured.clear(); at.run()
        assert not at.exception, [e.message for e in at.exception]
        assert not at.error, [e.value for e in at.error]
    cases = []
    with patch.object(st, "file_uploader", side_effect=upload), patch.object(st, "download_button", side_effect=download):
        run()
        mode = at.radio(key="_conversion_mode_widget")
        mode.set_value(mode.options[3]); run()
        fmt = next(item for item in at.selectbox if item.key != "_assignment_edition_widget")
        fmt.set_value(fmt.options[-1]); run()
        for edition in ("current", "legacy"):
            at.selectbox(key="_assignment_edition_widget").set_value(edition); run()
            at.text_area(key="text0_value").set_value(CUSTOM_SOURCE)
            at.button(key="convert_text").click(); run()
            result = at.session_state["result_html"]
            assert result == source["output"], (language, edition, result, source["output"])
            metadata = dict(at.session_state["result_assignment_metadata"])
            assert metadata["source_id"] == "custom_json" and metadata["edition_id"] is None
            assert metadata["custom_json_sha256"] == source["sha256"]
            assert metadata["requested_edition"] == edition
            assert not captured
            at.button(key="confirm_download").click(); run()
            assert len(captured) == 1 and captured[0]["raw"] == result.encode("utf-8")
            assert captured[0]["filename"].endswith(f'_custom_json_{metadata["signature"][:12]}.txt')
            assert captured[0]["mime"] == "text/plain"
            evidence = f"{language}_{edition}_custom.txt"
            (report_dir / evidence).write_bytes(captured[0]["raw"])
            cases.append({"language": language, "selected_edition": edition, "input": CUSTOM_SOURCE,
                          "output": result, "metadata": metadata, "saved_evidence": evidence,
                          "download_sha256": sha(captured[0]["raw"]), "exact_download_bytes": True,
                          "unchanged_uploaded_before_bundle": True})
            print(language, edition, "custom upload PASS", flush=True)
    return cases


def aggregate_reports(report_dir):
    reports = [json.loads((report_dir / f"app_ui_{lang}.json").read_text("utf-8"))
               for lang in ("JA", "ZH", "KO")]
    cases = [case for report in reports for case in report["cases"]]
    assert len(cases) == 18 and all(report["passed"] for report in reports)
    assert len({(row["language"], row["edition"], row["mode"]) for row in cases}) == 18
    for row in cases:
        assert sha((report_dir / row["saved_evidence"]).read_bytes()) == row["download_sha256"]
    for report in reports:
        assert len(report["custom_cases"]) == 2
        for row in report["custom_cases"]:
            assert sha((report_dir / row["saved_evidence"]).read_bytes()) == row["download_sha256"]
        assert len({row["output"] for row in report["cases"] if row["mode"] == "ruby"}) == 1
    result = {
        "passed": True, "conversion_download_routes": 18, "download_files_rehashed": 18,
        "annotation_results_identical_between_editions": True,
        "custom_upload_routes": 6, "custom_downloads": 6,
        "method": "Local Streamlit AppTest; upload/download transport observed, no browser or Cloud claim",
        "test_script_sha256": sha(Path(__file__).read_bytes()), "reports": reports,
    }
    cloud = {"kind": "local expected values only, not Cloud observations", "source": SOURCE,
             "cases": [{k: row[k] for k in ("language", "edition", "mode", "input", "output", "metadata", "download_filename", "saved_evidence", "download_sha256")}
                       for row in cases]}
    (report_dir / "cloud_expected.json").write_bytes((json.dumps(cloud, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    (report_dir / "app_ui_all.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--before-root", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--language", choices=("JA", "ZH", "KO"))
    parser.add_argument("--phase", choices=("before", "after"))
    args = parser.parse_args()
    args.root = args.root.resolve()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    if args.language:
        try:
            if args.phase == "before":
                result = prepare_baseline(args.before_root, args.language)
            else:
                baseline = json.loads((args.report_dir / f"baseline_{args.language}.json").read_text("utf-8"))
                result = run_ui(args.root, args.language, baseline, args.report_dir)
        except Exception:
            (args.report_dir / f"failure_{args.language}_{args.phase}.txt").write_text(
                traceback.format_exc(), encoding="utf-8")
            raise
        filename = f"baseline_{args.language}.json" if args.phase == "before" else f"app_ui_{args.language}.json"
        (args.report_dir / filename).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    for language in ("JA", "ZH", "KO"):
        for phase in ("before", "after"):
            command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                       "--root", str(args.root), "--before-root", str(args.before_root),
                       "--report-dir", str(args.report_dir), "--language", language, "--phase", phase]
            completed = subprocess.run(command, cwd=args.root, text=True, encoding="utf-8", capture_output=True)
            (args.report_dir / f"{language}_{phase}.log").write_text(
                completed.stdout + completed.stderr, encoding="utf-8")
            if completed.returncode:
                raise RuntimeError((language, phase, completed.stdout[-1000:], completed.stderr[-3000:]))
            print(language, phase, "PASS", flush=True)
    aggregate_reports(args.report_dir)


if __name__ == "__main__":
    main()
