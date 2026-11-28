"""Approved spellings and teaching glosses in the bundled public editions."""
import csv
import gzip
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "dafodil": ("草ᴰᶠ", "水仙ᴰ"),
    "pumili": ("木ᴾᴹ", "松ᴾᴹ"),
    "labrusk": ("草ᴸᴮ", "葡ᴸ"),
    "kontralt": ("女低", "女低音"),
}
PUMILI_GLOSSES = {"JA": "ムゴマツ", "ZH": "矮松", "KO": "무고소나무"}
CSV_NAME = "世界语词根-汉字对应列表_参照2新割当_7791.csv"
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


def readings(table, group, keys):
    rows, = (rows for name, rows in table.items() if name.startswith(group))
    return {key: RUBY.findall(html.replace("<br>", "")) for key, html, *_ in rows if key in keys}


class November28Assignments(unittest.TestCase):
    def test_shared_labels_manual_and_compound_boundaries(self):
        for language in PUMILI_GLOSSES:
            data = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            frozen = ROOT / "assignment_editions" / "legacy" / language
            for index, edition in enumerate(("legacy", "current")):
                with self.subTest(language=language, edition=edition):
                    if edition == "legacy":
                        raw = gzip.decompress((frozen / "kanji.json.gz").read_bytes())
                        csv_file = frozen / "kanji.csv"
                    else:
                        raw = (data / "置換リスト_漢字.json").read_bytes()
                        csv_file = data / CSV_NAME
                    table = json.loads(raw)
                    roots = {root: pair[index] for root, pair in SPELLINGS.items()}
                    roots.update({"pin": "松", "vit": "葡", "narcis": "水仙", "jonkvil": "水仙ᴶ"})
                    with csv_file.open(encoding="utf-8-sig", newline="") as stream:
                        manual = dict(csv.reader(stream))
                    expected = {root: [(glyph, root)] for root, glyph in roots.items()}
                    for group in ("局部", "全域"):
                        self.assertEqual(readings(table, group, roots), expected)
                    self.assertEqual({root: manual[root] for root in roots}, roots)
                    singer = [(roots["kontralt"], "kontralt"), ("者", "ul"), ("女", "in")]
                    self.assertEqual(readings(table, "全域", {"kontraltulin"}), {"kontraltulin": singer})

    def test_pumili_shared_learning_gloss(self):
        for language, gloss in PUMILI_GLOSSES.items():
            with self.subTest(language=language):
                data = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
                words = json.loads((data / "word_anno.json").read_bytes())
                self.assertEqual(words["pumili"], [["pumili", gloss]])
                table = json.loads((data / "置換リスト_ルビ.json").read_bytes())
                expected = {k: [(k, gloss)] for k in ("pumili", "Pumili", "PUMILI")}
                for group in ("局部", "全域"):
                    self.assertEqual(readings(table, group, expected), expected)
