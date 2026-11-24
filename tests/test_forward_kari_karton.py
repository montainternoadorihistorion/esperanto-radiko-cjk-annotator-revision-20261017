"""Whole-root display approvals and established readings of identical letter sequences."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "kari": ("蛀牙", "虫牙"),
    "karton": ("板ᴷ", "纸板"),
    "kanin": ("齿ᴷ", "犬齿"),
    "tanka": ("歌ᵀ", "短歌"),
    "tenis": ("网ᵀ", "网球"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


def segments(markup):
    return [(glyph, re.sub(r"<br\s*/?>", "", eo, flags=re.I))
            for glyph, eo in RUBY.findall(markup)]


class ReviewedRootDisplays(unittest.TestCase):
    def test_normal_marked_and_manual_readings(self):
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            frozen = ROOT / "assignment_editions" / "legacy" / language
            editions = (
                (frozen / "kanji.csv", gzip.decompress((frozen / "kanji.json.gz").read_bytes())),
                (app / "世界语词根-汉字对应列表_参照2新割当_7791.csv", (app / "置換リスト_漢字.json").read_bytes()),
            )
            for edition, (manual, payload) in enumerate(editions):
                display = {root: forms[edition] for root, forms in SPELLINGS.items()}
                with self.subTest(language=language, edition=edition):
                    with manual.open(encoding="utf-8-sig", newline="") as stream:
                        mapping = dict(csv.reader(stream))
                    self.assertEqual({r: mapping[r] for r in display}, display)
                    data = json.loads(payload)
                    local = self.group(data, "局部")
                    for root, written in display.items():
                        self.assertEqual(segments(local[root]), [(written, root)])

                    normal = self.group(data, "全域")
                    for root, headword in (
                        ("kari", "kario"), ("karton", "kartono"), ("kanin", "kanin"),
                        ("tanka", "tankao"), ("tenis", "teniso"),
                    ):
                        self.assertEqual(segments(normal[headword]), [(display[root], root)])
                    self.assertEqual(segments(normal["karton"]), [("卡", "kart")])
                    self.assertTrue(normal["karton"].endswith("on"))
                    self.assertEqual(segments(normal["poŝtkart"]), [("邮", "poŝt"), ("卡", "kart")])
                    self.assertEqual(segments(normal["tablotenis"]), [("桌", "tabl"), (display["tenis"], "tenis")])
                    for root, glyph in (("tank", "战车"), ("ten", "持")):
                        self.assertEqual(segments(local[root]), [(glyph, root)])

    @staticmethod
    def group(data, prefix):
        items, = (rows for key, rows in data.items() if key.startswith(prefix))
        return {key: markup for key, markup, *_ in items}
