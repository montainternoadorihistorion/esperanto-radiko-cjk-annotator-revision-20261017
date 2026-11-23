"""Check reviewed hectare and dike assignments across bundled forward data."""
import csv
import json
import re
import unittest
from pathlib import Path

APPS = Path(__file__).resolve().parents[1]
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.DOTALL)
BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


class HectareAndDikeAssignments(unittest.TestCase):
    def test_normal_localized_and_manual(self):
        expected = {
            "dig": "堤", "ĝet": "堤ᴳ̂", "izatis": "狐ᴵ", "mug": "松ᴹ",
            "klementin": "橘ᴷ", "hektar": "百亩", "mole": "堤ᴹ",
            "flan": "饼ᶠ", "sufle": "蛋奶酥",
        }
        for language in ("JA", "ZH", "KO"):
            with self.subTest(language=language):
                data = APPS / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
                with (data / "世界语词根-汉字对应列表_参照2新割当_7791.csv").open(
                    encoding="utf-8-sig", newline=""
                ) as table:
                    manual = {root.replace("g^", "ĝ"): value for root, value in csv.reader(table)}
                self.assertEqual({root: manual[root] for root in expected}, expected)
                payload = json.loads((data / "置換リスト_漢字.json").read_bytes())
                for prefix in ("全域", "局部"):
                    rules = next(rows for group, rows in payload.items() if group.startswith(prefix))
                    spellings = {
                        form: glyph for root, glyph in expected.items()
                        for form in (root, root.title(), root.upper())
                    }
                    observed = {}
                    for key, markup, *_ in rules:
                        if key in spellings:
                            label = key
                            glyph = spellings[key]
                            if prefix == "全域" and key.lower() == "mole":
                                label = key[:-1]
                                glyph = "软"
                            parts = [(BREAK.sub("", word), body) for body, word in RUBY.findall(markup)]
                            self.assertEqual(parts, [(label, glyph)], (language, prefix, key))
                            observed[key] = glyph
                        if prefix == "全域" and key in (" Klementino ", " klementino "):
                            self.assertEqual(markup, key)
                    self.assertEqual(observed.keys(), spellings.keys())


if __name__ == "__main__":
    unittest.main()
