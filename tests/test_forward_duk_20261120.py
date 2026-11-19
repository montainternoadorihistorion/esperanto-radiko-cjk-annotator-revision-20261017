"""Check the distinction between duk and baron across bundled forward data."""
import csv
import json
import re
import unittest
from pathlib import Path

APPS = Path(__file__).resolve().parents[1]
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.DOTALL)
BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


class DukeAndBaronAssignments(unittest.TestCase):
    def test_normal_localized_and_manual(self):
        expected = {"duk": "爵ᴰ", "baron": "爵"}
        for language in ("JA", "ZH", "KO"):
            with self.subTest(language=language):
                data = APPS / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
                with (data / "世界语词根-汉字对应列表_参照2新割当_7791.csv").open(
                    encoding="utf-8-sig", newline=""
                ) as table:
                    manual = dict(csv.reader(table))
                self.assertEqual({root: manual[root] for root in expected}, expected)
                payload = json.loads((data / "置換リスト_漢字.json").read_bytes())
                for prefix in ("全域", "局部"):
                    rows = next(rows for group, rows in payload.items() if group.startswith(prefix))
                    # In free text baron can also be bar+on; the bundled noun
                    # rule uses barono. Explicit @baron@ selects the bare root.
                    spellings = {}
                    for root, glyph in expected.items():
                        ending = "o" if prefix == "全域" and root == "baron" else ""
                        for form in (str.lower, str.title, str.upper):
                            spellings[form(root + ending)] = (form(root), glyph)
                    found = {}
                    for key, html, *_ in rows:
                        if key in spellings:
                            pieces = [(BREAK.sub("", label), glyph) for glyph, label in RUBY.findall(html)]
                            self.assertEqual(pieces, [spellings[key]])
                            found[key] = pieces[0]
                    self.assertEqual(found, spellings)


if __name__ == "__main__":
    unittest.main()
