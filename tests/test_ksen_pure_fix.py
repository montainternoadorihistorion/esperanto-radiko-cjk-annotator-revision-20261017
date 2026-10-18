"""Narrow, edition-aware repair of eight reviewed lowercase pure surfaces.

The full current/legacy tables exercise the real engine. Small fixtures expose
word-boundary, longer-rule and manual-overlay precedence independently of the
dictionary's current contents. No private repository is required.
"""
import ast
import gzip
import json
import logging
from pathlib import Path
import sys
import tempfile
from typing import List, Tuple
import unittest

logging.disable(logging.WARNING)
ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "Esperanto-Kanji-Ruby-JA"
sys.path.insert(0, str(APP))
# A normal import allows spawned multiprocessing workers to find the function.
import esp_text_replacement_module as engine
import esp_assignment_edition as editions
import esp_overlay_module as overlay

WORDS = ("ksenas", "kseno", "ksenoj", "ksenojn", "ksenos", "ksenu", "ksenulo", "ksenus")
EXPECTED = ("外ᴷˢas", "外ᴷˢo", "外ᴷˢoj", "外ᴷˢojn", "外ᴷˢos", "外ᴷˢu", "外ᴷˢ者o", "外ᴷˢus")
CONTROLS = (
    "sene", "@sene@", "semajn", "@semajn@tagoj", "testikito", "orkidita",
    "ksen", "kseni", "ksenis", "ksena", "ksene", "ksenon", "ksenulojn",
    "Kseno", "KSENO", "Ksenu", "KSENU", "fok-seno", "foksenojn",
    "pont-eŭksenojn", "novkseno", "ksenox", "3kseno", "kseno3", "ükseno",
    "%kseno%", "%@kseno@%", "@kseno@", "@ksen@o", "@ksenulo@",
    "@kseno@x", "x@kseno@", "xkseno", "kseno's", "kseno’s",
)


def read_raw(path):
    with (gzip.open if path.suffix == ".gz" else open)(path, "rt", encoding="utf-8") as stream:
        payload = json.load(stream)
    return tuple(payload[key] for key in (editions.GLOBAL, editions.LOCAL, editions.TWO))


def render(text, lists, parallel=False):
    global_rules, local_rules, two_rules = lists
    args = (engine.import_placeholders(str(APP / "app_data/placeholders_skip.txt")),
            local_rules, engine.import_placeholders(str(APP / "app_data/placeholders_localcapture.txt")),
            global_rules, two_rules, "替换后文字列のみ(仅)保留(简单替换)")
    if parallel:
        return engine.parallel_process(text, 2, *args)
    return engine.orchestrate_comprehensive_esperanto_text_replacement(text, *args)


class KsenPureTests(unittest.TestCase):
    def test_exact_scope_and_all_language_loaders(self):
        self.assertEqual(tuple(d.replace("/", "") for d in editions.REVIEWED_PURE_DECOMPOSITIONS), WORDS)
        helper_bytes = (APP / "esp_assignment_edition.py").read_bytes()
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            self.assertEqual((app / "esp_assignment_edition.py").read_bytes(), helper_bytes)
            for page, name in ((app / "main.py", "load_replacements_lists"),
                               (next((app / "pages").glob("1_*.py")), "_load_lists")):
                tree = ast.parse(page.read_text(encoding="utf-8"))
                functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
                namespace = {"editions": editions, "List": List, "Tuple": Tuple}
                exec(compile(ast.Module(body=functions, type_ignores=[]), str(page), "exec"), namespace)
                # An arbitrary file, even with the built-in basename, is not
                # opted in. Uploads use json.load and bypass this loader too.
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "置換リスト_漢字_純粋置換.json"
                    original = ([['kseno', 'CUSTOM', '$1$']], [], [])
                    path.write_text(json.dumps(dict(zip((editions.GLOBAL, editions.LOCAL, editions.TWO), original))), encoding="utf-8")
                    got = namespace[name](path)
                    self.assertEqual(got, original if name == "load_replacements_lists" else (original[1], original[2], original[0]))
        for edition in editions.EDITIONS:
            self.assertTrue(editions._is_bundled_pure_path(editions.resolve_path(APP / "app_data", "pure", edition)))
            self.assertFalse(editions._is_bundled_pure_path(editions.resolve_path(APP / "app_data", "kanji", edition)))
        editions._load_lists_cached.clear()

    def test_boundary_only_rules_and_user_overlay_priority(self):
        before = [["kseno-long", "LONG", "$1$"], ["seno", "无o", "$2$"], ["senu", "无u", "$3$"]]
        local = [["ksen", "外ᴷˢ", "@1@"], ["ul", "者", "@2@"]]
        after = editions._with_reviewed_pure_corrections(before, local)
        self.assertEqual([row for row in after if row[2].strip() not in {f"${9120000 + i}$" for i in range(8)}], before)
        self.assertEqual(before, [["kseno-long", "LONG", "$1$"], ["seno", "无o", "$2$"], ["senu", "无u", "$3$"]])
        for row in after:
            if row[2].strip().startswith("$912000"):
                self.assertTrue(row[0].startswith(" ") and row[0].endswith(" "))
        manual = overlay.merge_overlay(after, [["kseno", "MANUAL", "$9000000$"]])
        self.assertEqual(render("kseno kseno-long @kseno@ %kseno%", (manual, local, [])),
                         "MANUAL LONG 外ᴷˢo kseno")
        # The glyph is read from selected data, not hard-coded into the fix.
        changed = editions._with_reviewed_pure_corrections(before, [["ksen", "OTHER", "@1@"], ["ul", "PERSON", "@2@"]])
        self.assertEqual(render("ksenulo", (changed, local, [])), "OTHERPERSONo")

    def test_complete_current_and_legacy_tables(self):
        source = "\n".join(WORDS + CONTROLS)
        for edition in editions.EDITIONS:
            with self.subTest(edition=edition):
                path = editions.resolve_path(APP / "app_data", "pure", edition)
                before = read_raw(path)
                after = editions.load_lists_path(path)
                added = {f"${9120000 + index}$" for index in range(8)}
                if edition == "legacy":
                    added.update(f"${9130000 + index}$" for index in range(3))
                self.assertEqual([row for row in after[0] if row[2].strip() not in added], before[0])
                self.assertEqual(after[1:], before[1:])
                old_output = render(source, before).splitlines()
                output = render(source, after).splitlines()
                self.assertEqual(tuple(output[:8]), EXPECTED)
                self.assertEqual(output[8:], old_output[8:])
                self.assertEqual(output[8], "s内e")
                # Applying the existing stored/session overlay follows the
                # exact same main-page order and still wins for this word.
                session = overlay.build_correction("k/sen/o", str(APP / "app_data"), edition)
                # Strip rt before remaining tags, as the UI does.
                import re
                manual_rows = [[old, re.sub(r'</?ruby>', '', re.sub(r'<rt[^>]*>.*?</rt>', '', new, flags=re.S)), '$9000090$']
                               for old, new in session['kanji'][:1]]
                manual_global = overlay.merge_overlay(after[0], manual_rows)
                self.assertEqual(render("kseno", (manual_global, after[1], after[2])), "k无o")
                # Marker handling happens before the new boundary rules.
                contexts = "kseno kseno\n(kseno), ksenu!\n%kseno% @kseno@\n@ksen@o ksenulo"
                expected = "外ᴷˢo 外ᴷˢo\n(外ᴷˢo), 外ᴷˢu!\nkseno 外ᴷˢo\n外ᴷˢo 外ᴷˢ者o"
                self.assertEqual(render(contexts, after), expected)
                self.assertEqual(render(contexts, after, parallel=True), expected)
                del before, after, manual_global
                editions._load_lists_cached.clear()


if __name__ == "__main__":
    unittest.main(verbosity=2)
