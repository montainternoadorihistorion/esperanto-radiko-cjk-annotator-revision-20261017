"""Approved whole roots and controls whose ordinary and marked readings differ."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "banjan": ("木ᴮᴺ", "榕ᴮ"), "koriz": ("炎ᴷᴿ", "鼻炎"),
    "knot": ("结ᴷᵀ", "节ᴷ"), "farmaci": ("药ᶠᶜ", "药学"),
    "eksterm": ("歼", "灭ᴱᴷ"), "fizik": ("物理", "物理"),
    "kinu": ("麦ᴷ", "麦ᴷ"), "kvino": ("草ᴷⱽ", "草ᴷⱽ"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


def segments(markup):
    return [(match[1], re.sub(r"<br\s*/?>", "", match[2], flags=re.I))
            for match in RUBY.finditer(markup)]


class ReviewedRoots(unittest.TestCase):
    def test_each_edition_language_and_route(self):
        for lang in ("JA", "ZH", "KO"):
            app_data = ROOT / f"Esperanto-Kanji-Ruby-{lang}" / "app_data"
            legacy = ROOT / "assignment_editions" / "legacy" / lang
            for edition, (csv_path, payload) in enumerate((
                (legacy / "kanji.csv", gzip.decompress((legacy / "kanji.json.gz").read_bytes())),
                (app_data / "世界语词根-汉字对应列表_参照2新割当_7791.csv",
                 (app_data / "置換リスト_漢字.json").read_bytes()),
            )):
                displays = {r: variants[edition] for r, variants in SPELLINGS.items()}
                with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                    manual = dict(csv.reader(stream))
                self.assertEqual({r: manual[r] for r in displays}, displays)
                for name, items in json.loads(payload).items():
                    if not name.startswith(("全域", "局部")):
                        continue
                    with self.subTest(language=lang, edition=edition, group=name):
                        rows = {word: markup for word, markup, *_ in items}
                        for root, glyph in displays.items():
                            if root == "kvino" and name.startswith("全域"):
                                self.assertEqual(segments(rows[root]), [("五", "kvin")])
                                self.assertTrue(rows[root].endswith("o"))
                                continue
                            self.assertEqual(segments(rows[root]), [(glyph, root)])
                        if name.startswith("全域"):
                            self.assertEqual(segments(rows["farmaciist"]),
                                             [(displays["farmaci"], "farmaci"), ("家", "ist")])

