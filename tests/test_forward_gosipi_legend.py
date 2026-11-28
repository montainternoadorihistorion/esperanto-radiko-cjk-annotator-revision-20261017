"""Test the five approved labels without collapsing independent spellings or compounds."""
import gzip
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_LABELS = {
    "gosipi": ("草ᴳˢ", "棉ᴳ"),
    "kupres": ("木ᴷˢ", "柏ᴷ"),
    "desmod": ("兽ᴰˢ", "蝠ᴰ"),
    "stakis": ("草ˢᵀᴬ", "水苏ˢˢ"),
    "legend": ("传ᴸ", "读须"),
    "staki": ("水苏", "水苏"),
    "betonik": ("水苏ᴮ", "水苏ᴮ"),
    "desmodi": ("豆ᴰ", "豆ᴰ"),
    "cipres": ("柏", "柏"),
    "vespert": ("蝠", "蝠"),
    "leg": ("读", "读"),
    "end": ("须", "须"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


class GosipiLegendTests(unittest.TestCase):
    def test_distinct_atoms_and_preserved_compounds(self):
        for lang in ("JA", "ZH", "KO"):
            current = ROOT / f"Esperanto-Kanji-Ruby-{lang}" / "app_data" / "置換リスト_漢字.json"
            legacy = ROOT / "assignment_editions" / "legacy" / lang / "kanji.json.gz"
            for active, path in ((False, legacy), (True, current)):
                with self.subTest(lang=lang, current=active):
                    data = path.read_bytes()
                    tables = json.loads(data if active else gzip.decompress(data))
                    labels = {r: pair[active] for r, pair in ROOT_LABELS.items()}
                    atoms = {r: [(label, r)] for r, label in labels.items()}
                    normal = dict(atoms)
                    for stem in ("gosipi", "kupres", "desmod", "stakis", "legend"):
                        normal[stem + "ojn"] = atoms[stem]
                    normal.update({
                        "legenda": atoms["legend"],
                        "kupresac": [(labels["kupres"], "kupres"), ("科ᴬ", "ac")],
                        "stakioz": [(labels["staki"], "staki"), ("糖ᴼ", "oz")],
                    })
                    for prefix, expected in (("全域", normal), ("局部", atoms)):
                        rows, = (rows for key, rows in tables.items() if key.startswith(prefix))
                        hits = {r: value for r, value, *_ in rows if r in expected}
                        actual = {
                            r: RUBY.findall(value.replace("<br>", ""))
                            for r, value in hits.items()
                        }
                        self.assertEqual(actual, expected)
                        if prefix == "全域":
                            self.assertEqual(RUBY.sub(r"\1", hits["legenda"]), labels["legend"] + "a")
                            self.assertEqual(RUBY.sub(r"\1", hits["stakisojn"]), labels["stakis"] + "ojn")


if __name__ == "__main__":
    unittest.main()
