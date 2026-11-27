"""Bundled editions and labelled readings for the November 27 assignments."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "robur": ("木ᴿᴮ", "橡ᴿ"),
    "aŭrikulari": ("菌ᴬᵁ̆", "木耳"),
    "futbal": ("球ᶠ", "足球"),
    "negund": ("木ᴺᴳ", "枫ᴺ"),
    "citron": ("果ᶜ", "柠ᶜ"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)

def segments(markup):
    return [(glyph, re.sub(r"<br\s*/?>", "", eo, flags=re.I)) for glyph, eo in RUBY.findall(markup)]

def readings(payload, prefix):
    values, = (rows for name, rows in payload.items() if name.startswith(prefix))
    return {key: markup for key, markup, *_ in values}

class ReviewedRootDisplays(unittest.TestCase):
    def test_global_local_manual_and_compounds(self):
        for language in ("JA", "ZH", "KO"):
            data = APP / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            frozen = APP / "assignment_editions" / "legacy" / language
            editions = (
                (frozen / "kanji.csv", gzip.decompress((frozen / "kanji.json.gz").read_bytes())),
                (data / "世界语词根-汉字对应列表_参照2新割当_7791.csv", (data / "置換リスト_漢字.json").read_bytes()),
            )
            for edition, (manual_path, raw_payload) in enumerate(editions):
                with self.subTest(language=language, edition=edition):
                    displays = {root: forms[edition] for root, forms in SPELLINGS.items()}
                    displays.update({"acer": "枫", "horde": "麦ᴴ", "glan": "橡ᴳ", "kverk": "橡"})
                    with manual_path.open(encoding="utf-8-sig", newline="") as stream:
                        manual = dict(csv.reader(stream))
                    payload = json.loads(raw_payload)
                    local = readings(payload, "局部")
                    normal = readings(payload, "全域")
                    for root, display in displays.items():
                        self.assertEqual(manual[root], display)
                        self.assertEqual(segments(local[root]), [(display, root)])
                        self.assertEqual(segments(normal[root]), [(display, root)])
                    lemon = ("柠檬", "柠")[edition]
                    self.assertEqual(manual["limon"], lemon)
                    self.assertEqual(segments(local["limon"]), [(lemon,"limon")])
                    for stem, parts in {
                        "citronpremil": [(displays["citron"],"citron"),("压","prem"),("具","il")],
                        "citronflav": [(displays["citron"],"citron"),("黄","flav")],
                        "futbalist": [(displays["futbal"],"futbal"),("家","ist")],
                        "piedpilk": [("足","pied"),("球","pilk")],
                    }.items():
                        self.assertEqual(segments(normal[stem]), parts)

