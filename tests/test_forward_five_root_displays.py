"""Reviewed independent roots and productive sea-animal compounds in both editions."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "impertinent": ("放肆", "无礼"), "supermarkt": ("市ˢ", "超市"),
    "manat": ("兽ᴹᴬ", "海牛"), "dugong": ("兽ᴰᴳ", "海牛ᴰ"),
    "rosmar": ("海豹ᴿ", "海象"), "gink": ("木ᴳᴷ", "木ᴳᴷ"),
    "mar": ("海", "海"), "bov": ("牛", "牛"), "elefant": ("象", "象"),
    "fok": ("海豹", "海豹"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)
BREAK = re.compile(r"<br\s*/?>", re.I)


class FiveRootDisplays(unittest.TestCase):
    def test_normal_local_and_manual(self):
        for language in ("JA", "ZH", "KO"):
            current = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            frozen = ROOT / "assignment_editions" / "legacy" / language
            for version, folder in enumerate((frozen, current)):
                with self.subTest(language=language, edition=folder):
                    expected = {word: forms[version] for word, forms in SPELLINGS.items()}
                    if folder == frozen:
                        csv_path = folder / "kanji.csv"
                        raw = gzip.decompress((folder / "kanji.json.gz").read_bytes())
                    else:
                        csv_path = folder / "世界语词根-汉字对应列表_参照2新割当_7791.csv"
                        raw = (folder / "置換リスト_漢字.json").read_bytes()
                    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                        manual = dict(csv.reader(stream))
                    self.assertEqual({r: manual[r] for r in expected}, expected)
                    tables = json.loads(raw)
                    variants = {form for r in expected for form in (r, r.title(), r.upper())}
                    for prefix in ("全域", "局部"):
                        rows = next(group for name, group in tables.items() if name.startswith(prefix))
                        seen = set()
                        for word, markup, *_ in rows:
                            if word in variants:
                                ruby = RUBY.fullmatch(markup)
                                self.assertIsNotNone(ruby, word)
                                self.assertEqual((ruby[1], BREAK.sub("", ruby[2])), (expected[word.lower()], word))
                                seen.add(word)
                            if prefix == "全域" and word == "marelefant":
                                self.assertEqual([(glyph, BREAK.sub("", root)) for glyph, root in RUBY.findall(markup)],
                                                 [("海", "mar"), ("象", "elefant")])
                        self.assertEqual(seen, variants)
