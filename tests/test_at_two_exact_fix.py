"""Exact, bundled @ payloads; default/custom APIs retain their prior behavior."""
import ast
import gc
import html
import importlib.util
import inspect
import logging
from pathlib import Path
import re
import sys
import tempfile
import unittest

logging.disable(logging.WARNING)
ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "Esperanto-Kanji-Ruby-JA"
DATA = APP / "app_data"
sys.path.insert(0, str(APP))
import esp_assignment_edition as editions
import esp_overlay_module as overlay
import esp_text_replacement_module as engine

FLAG = "reviewed_local_decompositions"
FORMATS = {"pure": "替换后文字列のみ(仅)保留(简单替换)",
           "kanji": "HTML格式_Ruby文字_大小调整_汉字替换",
           "ruby": "HTML格式_Ruby文字_大小调整"}
TARGETS = ("greganta", "preganta")
LOCAL = [["gant", "GLOVE", "@1@"], ["greg", "GROUP", "@2@"],
         ["preg", "PRESS", "@3@"], ["ant", "ACTIVE", "@4@"],
         ["pre", "BEFORE", "@6@"], ["re", "AGAIN", "@5@"]]
SKIP = ["%901%", "%902%", "%903%"]
CAPTURE = ["@901@", "@902@", "@903@"]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def plain(value):
    value = re.sub(r"<rt[^>]*>.*?</rt>", "", value, flags=re.S)
    value = re.sub(r"</?ruby>", "", value)
    value = re.sub(r"<br\s*/?>\n?", "\n", value)
    return html.unescape(value).replace("\xa0", " ")


def render(source, enabled=False, local=LOCAL, global_rules=(), two=(), mode="pure", parallel=None):
    args = (SKIP, local, CAPTURE, global_rules, two, FORMATS[mode])
    if parallel is not None:
        return engine.parallel_process(source, parallel, *args, **{FLAG: enabled})
    return engine.orchestrate_comprehensive_esperanto_text_replacement(source, *args, **{FLAG: enabled})


class AtTwoExactTests(unittest.TestCase):
    def tearDown(self):
        editions._load_lists_cached.clear()
        gc.collect()

    def test_default_and_custom_scope(self):
        for name in ("_protect_input_regions", "create_replacements_list_for_localized_replacement",
                     "orchestrate_comprehensive_esperanto_text_replacement", "process_segment", "parallel_process"):
            self.assertIs(inspect.signature(getattr(engine, name)).parameters[FLAG].default, False)
        paths = set()
        for language in editions.LABELS:
            data = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            for edition in editions.EDITIONS:
                for mode in FORMATS:
                    path = editions.resolve_path(data, mode, edition)
                    paths.add(Path(path))
                    self.assertTrue(editions.supports_reviewed_local_decompositions(path))
        self.assertEqual(len(paths), 11)
        with tempfile.TemporaryDirectory() as directory:
            for path in paths:
                self.assertFalse(editions.supports_reviewed_local_decompositions(Path(directory) / path.name))
        self.assertEqual(render("@greganta@ @preganta@"), "gAGAINGLOVEa BEFOREGLOVEa")
        self.assertEqual(render("@greganta@ @preganta@", True), "GROUPACTIVEa PRESSACTIVEa")
        # A caller may explicitly opt in, but a custom/default API never does so implicitly.
        self.assertEqual(render("@greganta@", local=[["greganta", "CUSTOM", "@1@"]]), "CUSTOM")

    def test_atoms_are_selected_not_hardcoded_and_fail_closed(self):
        self.assertEqual(set(engine._REVIEWED_LOCAL_DECOMPOSITIONS), set(TARGETS))
        local = [row[:] for row in LOCAL]
        local[1][1], local[2][1], local[3][1] = "NEW-G", "NEW-P", "NEW-A"
        before = repr(local)
        self.assertEqual(render("@greganta@ @preganta@", True, local), "NEW-GNEW-Aa NEW-PNEW-Aa")
        self.assertEqual(repr(local), before)
        for invalid in ([row for row in local if row[0] != "ant"],
                        local + [["greg", "CONFLICT", "@99@"]],
                        [[old, "" if old == "greg" else new, token] for old, new, token in local]):
            with self.assertRaises(ValueError):
                engine._reviewed_local_renderings(["greganta"], invalid, True)
        # Do not inspect irrelevant or disabled local tables at all.
        self.assertEqual(engine._reviewed_local_renderings(["greganta"], None), {})
        self.assertEqual(engine._reviewed_local_renderings(["kordonita"], None, True), {})
        self.assertEqual(engine._reviewed_local_renderings(["greganta"], local + [local[1]], True),
                         {"greganta": "NEW-GNEW-Aa"})

    def test_exact_payload_boundaries_percent_and_email_protection(self):
        controls = ("greganta preganta", "@ greganta @", "@greganta preganta@", "@gregantaj@",
                    "@pregantajn@", "@agreganta@", "@xpreganta@", "@pregantax@", "@Greganta@",
                    "@PREGANTA@", "@greganta!@", "%@greganta@%", "@%preganta%@",
                    "greganta@example.com", "@kordonita@", "@greg@anta", "@preg@anta")
        for value in controls:
            with self.subTest(value=value):
                self.assertEqual(render(value, True), render(value))
        for value, expected in (("@greganta@@preganta@", "GROUPACTIVEaPRESSACTIVEa"),
                                ("x@greganta@y", "xGROUPACTIVEay"),
                                ("(@preganta@),", "(PRESSACTIVEa),"),
                                ("%@greganta@% @preganta@", "@greganta@ PRESSACTIVEa"),
                                ("@@greganta@@", "@GROUPACTIVEa@"),
                                # Existing syntax recognizes the leading @ pair here;
                                # this is distinct from the ordinary email control above.
                                ("@greganta@example.com", "GROUPACTIVEaexample.com")):
            self.assertEqual(render(value, True), expected)
        # The existing marker allocator must still avoid literal placeholder collisions.
        source = "%901% @901@ @greganta@ @greganta@ @preganta@"
        self.assertEqual(render(source, True).replace("GROUPACTIVEa", "gAGAINGLOVEa")
                         .replace("PRESSACTIVEa", "BEFOREGLOVEa"), render(source))

    def test_compatibility_global_allowlist_and_existing_manual_priority(self):
        source = "@greganta@ @preganta@ @ddt@"
        globals_ = [["greganta", "MANUAL-G", "$1$"], ["preganta", "MANUAL-P", "$2$"],
                    ["ddt", "REVIEWED-DDT", "$3$"]]
        selected = engine.create_replacements_list_for_localized_replacement(
            source, CAPTURE, LOCAL, globals_, **{FLAG: True})
        self.assertEqual([row[2] for row in selected], ["GROUPACTIVEa", "PRESSACTIVEa", "REVIEWED-DDT"])
        self.assertEqual(render(source, True, global_rules=globals_), "GROUPACTIVEa PRESSACTIVEa REVIEWED-DDT")
        # Manual global entries continue to govern normal text, while @ has always selected local rules.
        self.assertEqual(render("greganta preganta @greganta@", True, global_rules=globals_),
                         "MANUAL-G MANUAL-P GROUPACTIVEa")
        self.assertEqual(render("greganta preganta", True, global_rules=globals_),
                         render("greganta preganta", global_rules=globals_))

    def test_parallel_all_execution_paths(self):
        for source, workers in (("@greganta@", 2), ("@preganta@\n@greganta@", 1),
                                ("@greganta@\n@preganta@\n%@greganta@%\n@kordonita@", 2)):
            for enabled in (False, True):
                self.assertEqual(render(source, enabled, parallel=workers), render(source, enabled))

    def test_actual_editions_languages_annotations_inverse_and_html(self):
        inverse = module(ROOT / "Esperanto-Reverter-JA/esperanto_converter.py", "at_two_test_inverse")
        recovery = module(ROOT / "Esperanto-Reverter-JA/html_source_recovery.py", "at_two_test_html")
        indices = {edition: inverse.build_mapping_index_cached(inverse.effective_mapping_records(
            key, inverse.load_dictionary_source(key))) for edition, key in
            (("current", "pejvo-piv-20260620"), ("legacy", "pre-las-20261017"))}
        source = "@greganta@ @preganta@ @kordonita@"
        for language in editions.LABELS:
            data = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            for edition in editions.EDITIONS:
                for mode in FORMATS:
                    with self.subTest(language=language, edition=edition, mode=mode):
                        gg, gl, g2 = editions.load_lists(data, mode, edition)
                        roots = {old: new for old, new, _ in gl if old in ("greg", "preg", "ant", "kordon", "it")}
                        expected = " ".join((roots["greg"] + roots["ant"] + "a",
                                             roots["preg"] + roots["ant"] + "a",
                                             roots["kordon"] + roots["it"] + "a"))
                        actual = render(source, True, gl, gg, g2, mode)
                        self.assertEqual(actual, expected)
                        self.assertEqual(render("@kordonita@", True, gl, gg, g2, mode),
                                         render("@kordonita@", False, gl, gg, g2, mode))
                        if mode != "ruby":
                            self.assertEqual(plain(actual), "群ᴳ在a 压ᴾᴳ在a 带ᴷ受a")
                        self.assertEqual(inverse.convert_kanji_esperanto_to_alphabet(plain(actual), indices[edition]),
                                         "greganta preganta kordonita")
                        if mode != "pure":
                            document = engine.apply_ruby_html_header_and_footer(actual, FORMATS[mode])
                            self.assertEqual(recovery.recover_standard_html(document,
                                "annotation" if mode == "ruby" else "kanji")["text"], "greganta preganta kordonita")
                        editions._load_lists_cached.clear()
                        del gg, gl, g2
                        gc.collect()

    def test_actual_two_pass_normal_text_and_manual_overlay(self):
        for edition in editions.EDITIONS:
            gg, gl, g2 = editions.load_lists(DATA, "kanji", edition)
            gg = overlay.merge_overlay(gg, overlay.load_overlay_entries(str(DATA), "kanji", edition))
            source = "greganta\n@greganta@\npreganta\n@preganta@\nkordonita\n@kordonita@"
            first = render(source, True, gl, gg, g2, "kanji")
            auto = overlay.auto_overlay_entries(first, str(DATA), "kanji", edition)
            final = render(source, True, gl, overlay.merge_overlay(gg, auto), g2, "kanji") if auto else first
            previous = render(source, False, gl, gg, g2, "kanji")
            previous_auto = overlay.auto_overlay_entries(previous, str(DATA), "kanji", edition)
            previous = render(source, False, gl, overlay.merge_overlay(gg, previous_auto), g2, "kanji") if previous_auto else previous
            # Individual normal words, including their ruby markup, stay byte-identical after the second pass.
            self.assertEqual(final.split("<br>\n")[::2], previous.split("<br>\n")[::2])
            roots = {old: new for old, new, _ in gl if old in ("greg", "preg", "ant")}
            self.assertIn(roots["greg"] + roots["ant"] + "a", final)
            self.assertIn(roots["preg"] + roots["ant"] + "a", final)
            editions._load_lists_cached.clear()

    def test_all_application_calls_explicitly_propagate_bundled_opt_in(self):
        for language in editions.LABELS:
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            main = ast.parse((app / "main.py").read_text(encoding="utf-8"))
            calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id in
                     ("orchestrate_comprehensive_esperanto_text_replacement", "parallel_process")]
            self.assertEqual(len(calls), 4)
            for call in calls:
                flag = next(keyword.value for keyword in call.keywords if keyword.arg == FLAG)
                self.assertIsInstance(flag, ast.Name)
                self.assertEqual(flag.id, FLAG)
            manual = ast.parse(next((app / "pages").glob("1_*.py")).read_text(encoding="utf-8"))
            calls = [node for node in ast.walk(manual) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == "orchestrate_comprehensive_esperanto_text_replacement"]
            self.assertEqual(len(calls), 2)
            for call in calls:
                flag = next(keyword.value for keyword in call.keywords if keyword.arg == FLAG)
                self.assertIsInstance(flag, ast.Call)
                self.assertEqual(flag.func.attr, "supports_reviewed_local_decompositions")


if __name__ == "__main__":
    unittest.main(verbosity=2)
