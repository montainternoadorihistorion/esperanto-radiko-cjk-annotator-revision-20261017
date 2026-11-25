"""Whole-root display approvals and established readings of identical letter sequences."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {'strob': ('木ˢᵀ', '松ˢ'), 'miceli': ('菌ᴹᴱ', '菌丝体'), 'bradip': ('兽ᴮᴿ', '树懒ᴮ')}
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
                    for root, written in display.items():
                        self.assertEqual(segments(normal[root]), [(written, root)])
                    for root, written in (("ake", "树懒"), ("hif", "菌丝"), ("strobil", "锥ˢ")):
                        self.assertEqual(segments(local[root]), [(written, root)])
                        self.assertEqual(segments(normal[root]), [(written, root)])
                    self.assertEqual(segments(normal["bradiped"]), [(display["bradip"], "bradip"), ("科ᴱ", "ed")])
                    self.assertEqual(segments(normal["strobo"]), [(display["strob"], "strob")])
                    self.assertEqual(segments(local["strobo"]), [("闪ˢ", "strobo")])

    @staticmethod
    def group(data, prefix):
        items, = (rows for key, rows in data.items() if key.startswith(prefix))
        return {key: markup for key, markup, *_ in items}
