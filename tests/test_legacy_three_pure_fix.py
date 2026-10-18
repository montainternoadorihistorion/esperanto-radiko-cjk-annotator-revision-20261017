"""Three reviewed lowercase legacy pure words; all other routes stay intact."""
import gzip
import json
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

WORDS = ("greganta", "preganta", "kordonita")
EXPECTED = ("群ᴳ在a", "压ᴾᴳ在a", "kordonita")
TOKENS = {f"${9130000 + index}$" for index in range(3)}


def read_raw(path):
    with (gzip.open if path.suffix == ".gz" else open)(path, "rt", encoding="utf-8") as stream:
        payload = json.load(stream)
    return tuple(payload[key] for key in (editions.GLOBAL, editions.LOCAL, editions.TWO))


def prior_pure(path):
    global_rules, local_rules, two_rules = read_raw(path)
    return editions._with_reviewed_pure_corrections(global_rules, local_rules), local_rules, two_rules


def render(text, lists, parallel=False):
    global_rules, local_rules, two_rules = lists
    args = (engine.import_placeholders(str(DATA / "placeholders_skip.txt")), local_rules,
            engine.import_placeholders(str(DATA / "placeholders_localcapture.txt")),
            global_rules, two_rules, "替换后文字列のみ(仅)保留(简单替换)")
    if parallel:
        return engine.parallel_process(text, 2, *args)
    return engine.orchestrate_comprehensive_esperanto_text_replacement(text, *args)


class LegacyThreePureTests(unittest.TestCase):
    def tearDown(self):
        editions._load_lists_cached.clear()

    def test_legacy_bundled_path_only_and_language_parity(self):
        self.assertEqual(tuple(d.replace("/", "") for d in editions.LEGACY_REVIEWED_PURE_DECOMPOSITIONS), WORDS)
        helper = (APP / "esp_assignment_edition.py").read_bytes()
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            self.assertEqual((app / "esp_assignment_edition.py").read_bytes(), helper)
            for edition in editions.EDITIONS:
                for mode in ("pure", "kanji", "ruby"):
                    path = editions.resolve_path(app / "app_data", mode, edition)
                    self.assertEqual(editions._is_bundled_legacy_pure_path(path),
                                     edition == "legacy" and mode == "pure")
        # Neither a filename nor a matching legacy directory tail opts a
        # custom input into the bundled corrections.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assignment_editions/legacy/JA/pure.json.gz"
            path.parent.mkdir(parents=True)
            original = ([["greganta", "CUSTOM", "$1$"]], [], [])
            payload = dict(zip((editions.GLOBAL, editions.LOCAL, editions.TWO), original))
            path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
            self.assertFalse(editions._is_bundled_legacy_pure_path(path))
            self.assertEqual(editions.load_lists_path(path), original)

    def test_boundary_insertion_longer_rules_identity_and_manual_priority(self):
        before = [["greganta-long", "LONG", "$1$"], ["reganta", "BAD-G", "$2$"],
                  ["ordonit", "BAD-K", "$3$"]]
        local = [["greg", "GROUP", "@1@"], ["preg", "PRESS", "@2@"], ["ant", "ACTIVE", "@3@"]]
        snapshot = json.dumps((before, local))
        after = editions._with_legacy_reviewed_pure_corrections(before, local)
        self.assertEqual([row for row in after if row[2].strip() not in TOKENS], before)
        self.assertEqual(json.dumps((before, local)), snapshot)
        for old, new, token in after:
            if token.strip() in TOKENS:
                self.assertTrue(old.startswith(" ") and old.endswith(" "))
        self.assertEqual(render("greganta preganta kordonita greganta-long", (after, local, [])),
                         "GROUPACTIVEa PRESSACTIVEa kordonita LONG")
        manual = overlay.merge_overlay(after, [[word, f"MANUAL{i}", f"$900009{i}$"]
                                                for i, word in enumerate(WORDS)])
        self.assertEqual(render(" ".join(WORDS), (manual, local, [])), "MANUAL0 MANUAL1 MANUAL2")

    def test_invalid_roots_or_placeholder_collisions_fail_closed(self):
        local = [["greg", "群ᴳ", "@1@"], ["preg", "压ᴾᴳ", "@2@"], ["ant", "在", "@3@"]]
        for invalid in (local[:-1], local + [["greg", "OTHER", "@4@"]]):
            with self.assertRaises(ValueError):
                editions._with_legacy_reviewed_pure_corrections([], invalid)
        for global_rules, local_rules in (([["x", "x", " $9130001$ "]], local),
                                          ([], local + [["x", "x", "$9130002$"]])):
            with self.assertRaises(ValueError):
                editions._with_legacy_reviewed_pure_corrections(global_rules, local_rules)

    def test_real_tables_only_three_legacy_words_change(self):
        controls = []
        for word in WORDS:
            controls.extend((word.upper(), word.capitalize(), "x" + word, word + "x",
                             "3" + word, word + "3", "ü" + word, word + "j", word + "n",
                             word + "jn", word + "'s", word + "’s", "%" + word + "%",
                             "@" + word + "@", "%@" + word + "@%"))
        controls.extend(("g@dominant@a", "p@dominant@a", "k@komandit@a", "sene", "@sene@",
                         "kseno", "@kseno@", "semajn", "@semajn@tagoj", "testikito",
                         "orkidita", "reganta", "ordoni", "pregant", "kordon", "kordono",
                         "@kordon@ita", "gregantoj", "preganto", "kordonitaj"))
        source = "\n".join(WORDS + tuple(controls))
        for edition in editions.EDITIONS:
            with self.subTest(edition=edition):
                path = editions.resolve_path(DATA, "pure", edition)
                before = prior_pure(path)
                after = editions.load_lists_path(path)
                self.assertEqual([row for row in after[0] if row[2].strip() not in TOKENS], before[0])
                self.assertEqual(after[1:], before[1:])
                previous = render(source, before).splitlines()
                actual = render(source, after).splitlines()
                self.assertEqual(actual[3:], previous[3:])
                if edition == "legacy":
                    self.assertEqual(tuple(previous[:3]), ("g治在a", "p治在a", "k令受a"))
                    self.assertEqual(tuple(actual[:3]), EXPECTED)
                    self.assertEqual(sum(a != b for a, b in zip(actual, previous)), 3)
                else:
                    self.assertEqual(after, before)
                    self.assertEqual(actual, previous)
                editions._load_lists_cached.clear()

    def test_spacing_protection_parallel_and_existing_inverse_collisions(self):
        lists = editions.load_lists(DATA, "pure", "legacy")
        source = ("greganta greganta\n(preganta), kordonita!\n"
                  "greganta  preganta\nnov-kordonita\n"
                  "%greganta% @greganta@\ng@dominant@a p@dominant@a k@komandit@a")
        expected = ("群ᴳ在a 群ᴳ在a\n(压ᴾᴳ在a), kordonita!\n"
                    "群ᴳ在a  压ᴾᴳ在a\nn卵-kordonita\n"
                    "greganta g再手套a\ng治在a p治在a k令受a")
        self.assertEqual(render(source, lists), expected)
        self.assertEqual(render(source, lists, parallel=True), expected)
        # Direct inverse remains unchanged, including intentional collisions.
        sys.path.insert(0, str(ROOT / "Esperanto-Reverter-JA"))
        import esperanto_converter as inverse
        edition_id = "pre-las-20261017"
        mapping = inverse.effective_mapping_records(edition_id, inverse.load_dictionary_source(edition_id))
        index = inverse.build_mapping_index_cached(mapping)
        for word, converted in zip(WORDS, EXPECTED):
            self.assertEqual(inverse.convert_kanji_esperanto_to_alphabet(converted, index), word)
        for source, recovered in (("g治在a", "gdominanta"), ("p治在a", "pdominanta"), ("k令受a", "kkomandita")):
            self.assertEqual(inverse.convert_kanji_esperanto_to_alphabet(source, index), recovered)

    def test_matches_existing_kanji_ruby_correction_without_new_segmentation(self):
        for word, decomp, expected in zip(WORDS, editions.LEGACY_REVIEWED_PURE_DECOMPOSITIONS, EXPECTED):
            self.assertEqual(overlay.autofix_decomp(word, str(DATA)), decomp)
            correction = overlay.build_correction(decomp, str(DATA), "legacy")
            old, html = correction["kanji"][0]
            visible = re.sub(r"</?ruby>", "", re.sub(r"<rt[^>]*>.*?</rt>", "", html, flags=re.S))
            self.assertEqual(old, word)
            self.assertEqual(visible, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
