"""Verify the pharmacy, its pharmacist derivative and other medicine roots."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOTS = {
    "apotek": ("药ᴬ", "药店"),
    "medikament": ("药", "药"), "farmaci": ("药ᶠᶜ", "药学"),
    "drog": ("药ᴰ", "药ᴰ"), "butik": ("店", "店"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)
BREAK = re.compile(r"<br\s*/?>", re.I)


class Pharmacy(unittest.TestCase):
    def test_normal_local_and_manual_rendering(self):
        for language in ("JA", "ZH", "KO"):
            current = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            frozen = ROOT / "assignment_editions" / "legacy" / language
            for edition, folder in enumerate((frozen, current)):
                with self.subTest(language=language, edition=folder):
                    if folder == frozen:
                        csv_path = frozen / "kanji.csv"
                        payload = gzip.decompress((frozen / "kanji.json.gz").read_bytes())
                    else:
                        csv_path = current / "世界语词根-汉字对应列表_参照2新割当_7791.csv"
                        payload = (current / "置換リスト_漢字.json").read_bytes()
                    expected = {r: forms[edition] for r, forms in ROOTS.items()}
                    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                        manual = dict(csv.reader(stream))
                    self.assertEqual({r: manual[r] for r in ROOTS}, expected)
                    forms = {form: glyph for root, glyph in expected.items()
                             for form in (root, root.upper(), root.title())}
                    groups = json.loads(payload)
                    for prefix in ("全域", "局部"):
                        rows = next(items for key, items in groups.items() if key.startswith(prefix))
                        if prefix == "全域":
                            derivative = next(text for word, text, *_ in rows if word == "apotekist")
                            self.assertEqual(
                                [(r[1], BREAK.sub("", r[2])) for r in RUBY.finditer(derivative)],
                                [(expected["apotek"], "apotek"), ("家", "ist")],
                            )
                        found = {}
                        for word, markup, *_ in rows:
                            if word in forms:
                                ruby = RUBY.fullmatch(markup)
                                self.assertIsNotNone(ruby, (prefix, word))
                                self.assertEqual(BREAK.sub("", ruby[2]), word)
                                found[word] = ruby[1]
                        self.assertEqual(found, forms)
