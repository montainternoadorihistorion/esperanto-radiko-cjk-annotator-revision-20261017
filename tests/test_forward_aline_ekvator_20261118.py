"""Exercise root-labelled assignment changes and their shared-glyph controls."""
import csv
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.DOTALL)
BREAK = re.compile(r"<br\s*/?>", re.I)
ADOPTED = {"aline": "段ᴬ", "ekvator": "赤道"}
CONTROLS = {"etap": "段", "komut": "换", "ad": "行", "ruf": "赤褐",
            "larik": "落松", "orgen": "琴ᴼ", "viadukt": "旱桥"}

class ParagraphAndEquatorAssignments(unittest.TestCase):
    def test_bundled_rules_and_manual_table(self):
        for lang in ("JA", "ZH", "KO"):
            data = ROOT / f"Esperanto-Kanji-Ruby-{lang}" / "app_data"
            with (data / "世界语词根-汉字对应列表_参照2新割当_7791.csv").open(encoding="utf-8-sig", newline="") as source:
                manual = dict(csv.reader(source))
            for name, glyph in (ADOPTED | CONTROLS).items():
                self.assertEqual(manual[name], glyph, (lang, name))
            payload = json.loads((data / "置換リスト_漢字.json").read_bytes())
            for group, rows in payload.items():
                seen = set()
                for key, html, *_ in rows:
                    for glyph, spelling in RUBY.findall(html):
                        root = BREAK.sub("", spelling).lower()
                        if root in ADOPTED:
                            self.assertEqual(glyph, ADOPTED[root], (lang, group, key))
                            seen.add(root)
                if group.startswith(("全域", "局部")):
                    self.assertEqual(seen, set(ADOPTED), (lang, group))

if __name__ == "__main__":
    unittest.main()
