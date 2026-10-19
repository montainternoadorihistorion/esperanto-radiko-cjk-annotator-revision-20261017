"""Production manual-page rendering, isolated by language to avoid module-cache reuse.

The live-page integration and broad equivalence audit accompany this focused test.
This test runs the page's actual helper AST with real dictionaries and overlays;
only the simulated session correction and optional failure are instrumented.
"""
import argparse
import ast
import gc
import html
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("JA", "ZH", "KO")
FORMATS = {"ruby": "HTML格式_Ruby文字_大小调整",
           "kanji": "HTML格式_Ruby文字_大小调整_汉字替换"}


def plain(value):
    value = re.sub(r"<rt[^>]*>.*?</rt>", "", value, flags=re.S)
    value = re.sub(r"<br\s*/?>\n?", "\n", value)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).replace("\xa0", " ")


def check_language(language):
    logging.disable(logging.WARNING)
    app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    data = app / "app_data"
    sys.path.insert(0, str(app))
    import esp_assignment_edition as editions
    import esp_overlay_module as overlay
    import esp_text_replacement_module as engine

    page = next((app / "pages").glob("1_*.py"))
    tree = ast.parse(page.read_text("utf-8"))
    helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name in ("_load_lists", "_render_probe", "_decompose")]
    assert len(helpers) == 3
    namespace = {
        "editions": editions, "ov": overlay, "re": re, "DATA": str(data),
        "_PS": engine.import_placeholders(str(data / "placeholders_skip.txt")),
        "_PL": engine.import_placeholders(str(data / "placeholders_localcapture.txt")),
        "orchestrate_comprehensive_esperanto_text_replacement":
            engine.orchestrate_comprehensive_esperanto_text_replacement,
    }
    exec(compile(ast.Module(body=helpers, type_ignores=[]), str(page), "exec"), namespace)
    render = namespace["_render_probe"]
    decompose = namespace["_decompose"]
    saved_corrections = (data / "user_corrections.json").read_bytes()
    rows = []

    for edition in ("current", "legacy"):
        namespace["assignment_edition"] = edition
        for mode, fmt in FORMATS.items():
            path = str(editions.resolve_path(data, mode, edition))
            gg, gl, g2 = editions.load_lists_path(path)
            gg = overlay.merge_overlay(gg, overlay.load_overlay_entries(str(data), mode, edition))

            def first_pass(source):
                return engine.orchestrate_comprehensive_esperanto_text_replacement(
                    " " + source + " ", namespace["_PS"], gl, namespace["_PL"], gg, g2, fmt,
                    reviewed_local_decompositions=True,
                )

            # These three normal words need the main page's existing second pass.
            for word, expected_decomposition, kanji in (
                    ("greganta", "greg/ant/a", "群ᴳ在a"),
                    ("preganta", "preg/ant/a", "压ᴾᴳ在a"),
                    ("kordonita", "kordonita", "kordonita")):
                first = first_pass(word)
                final = render(word, path, fmt, mode)
                assert final != first, (language, edition, mode, word)
                assert plain(final).strip() == (word if mode == "ruby" else kanji)
                diagnostic = decompose(word, path, fmt, mode, final)
                assert diagnostic == (expected_decomposition if mode == "ruby" else
                                      {"greganta": "群ᴳ/在/a", "preganta": "压ᴾᴳ/在/a",
                                       "kordonita": "kordonita"}[word]), diagnostic
                # A displayed result is reused directly, without a hidden third conversion.
                with patch.dict(namespace, {"_render_probe": lambda *args: (_ for _ in ()).throw(
                        AssertionError("diagnostic unexpectedly re-rendered"))}):
                    assert decompose(word, path, fmt, mode, final) == diagnostic
                rows.append({"edition": edition, "mode": mode, "word": word,
                             "decomposition": diagnostic, "plain": plain(final).strip()})

            # Existing @ semantics, protection, and correctly segmented controls stay as-is.
            source = "@greganta@ @preganta@ @kordonita@ semajno sportisto lasis %群ᴳ@%"
            assert render(source, path, fmt, mode) == first_pass(source)
            if mode == "kanji":
                body = plain(render(source, path, fmt, mode))
                assert "群ᴳ在a 压ᴾᴳ在a 带ᴷ受a" in body
                assert ("放is" if edition == "current" else "留is") in body
                assert "群ᴳ@" in body

            # Existing session corrections keep priority and case variants, without disk writes.
            correction = overlay.build_correction("gre/gant/a", str(data), edition)
            with patch.object(overlay, "load_corrections", return_value=[correction]):
                for word in ("greganta", "Greganta", "GREGANTA"):
                    expected = dict(correction[mode])[word]
                    result = render(word, path, fmt, mode)
                    assert plain(result).strip() == plain(expected), (word, result, expected)
                assert render("@greganta@", path, fmt, mode) == first_pass("@greganta@")

            # Match main.py's optional-autofix failure behavior exactly.
            with patch.object(overlay, "auto_overlay_entries", side_effect=RuntimeError("optional")):
                assert render("greganta", path, fmt, mode) == first_pass("greganta")
            editions._load_lists_cached.clear()
            del gg, gl, g2
            gc.collect()

    assert (data / "user_corrections.json").read_bytes() == saved_corrections
    # All links point to the approved revision endpoints; other main logic is audited separately.
    main = (app / "main.py").read_text("utf-8")
    for lang in ("ja", "zh", "ko"):
        assert main.count(f"https://esperanto-cjk-revision-{lang}-20261017.streamlit.app/") == 1
    assert "https://esperanto-radiko-cjk-annotator.streamlit.app/" not in main
    assert "https://esperanto-radiko-cjk-annotator-zh.streamlit.app/" not in main
    assert "https://esperanto-radiko-cjk-annotator-ko.streamlit.app/" not in main
    return {"passed": True, "language": language, "rows": rows,
            "normal_diagnostic_checks": len(rows), "unchanged_corrections_file": True}


class ManualDiagnosticConsistencyTests(unittest.TestCase):
    def test_all_languages_in_fresh_processes(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                result = subprocess.run(
                    [sys.executable, "-B", "-X", "utf8", __file__, "--language", language],
                    cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=600,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)["passed"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=LANGUAGES)
    parser.add_argument("--report", type=Path)
    args, remaining = parser.parse_known_args()
    if args.language:
        result = check_language(args.language)
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(encoded, "utf-8")
        print(encoded, end="")
    else:
        unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
