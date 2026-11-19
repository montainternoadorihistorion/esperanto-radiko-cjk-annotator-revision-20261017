"""Check the whole-root and split displays for the reviewed botanical names."""
import csv
import json
import re
import unittest
from pathlib import Path

APPS = Path(__file__).resolve().parents[1]
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.DOTALL)
BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


def pieces(text):
    return [(BREAK.sub("", root).lower(), glyph) for glyph, root in RUBY.findall(text)]


class BotanicalAssignments(unittest.TestCase):
    def test_bundled_word_boundaries_and_manual_displays(self):
        for lang in ("JA", "ZH", "KO"):
            with self.subTest(language=lang):
                data = APPS / f"Esperanto-Kanji-Ruby-{lang}" / "app_data"
                payload = json.loads((data / "置換リスト_漢字.json").read_bytes())
                expected = {
                    "halofit": "盐ᴴ植ᶠ", "deodar": "雪松ᴰ", "cedr": "雪松",
                    "duk": "公爵", "alumet": "柴", "aŭtism": "自ᴬ主义",
                    "halo": "晕", "fit": "植ᶠ", "sal": "盐", "plant": "植",
                }
                with (data / "世界语词根-汉字对应列表_参照2新割当_7791.csv").open(encoding="utf-8-sig", newline="") as table:
                    manual = dict(csv.reader(table))
                self.assertEqual({r: manual[r] for r in expected}, expected)
                normal = next(rows for key, rows in payload.items() if key.startswith("全域"))
                local = next(rows for key, rows in payload.items() if key.startswith("局部"))
                for rows, targets in (
                    (normal, {"halofit": [("halo", "盐ᴴ"), ("fit", "植ᶠ")],
                              "salplant": [("sal", "盐"), ("plant", "植")],
                              "deodar": [("deodar", "雪松ᴰ")], "cedr": [("cedr", "雪松")]}),
                    (local, {r: [(r, glyph)] for r, glyph in expected.items()}),
                ):
                    for variant in (str.lower, str.title, str.upper):
                        forms = {variant(r): segments for r, segments in targets.items()}
                        actual = {key: pieces(html) for key, html, *_ in rows if key in forms}
                        self.assertEqual(actual, forms)


if __name__ == "__main__":
    unittest.main()
