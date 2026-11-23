"""A sole root owns its display even when a compound can produce the same text."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# The pairs are fixed legacy / current. Inner identifiers belong to components.
DISPLAYS = {
    "deism": ("神主义ᴰ", "神主义"), "deist": ("神家ᴰ", "神家"),
    "dodekaedr": ("十二面", "十二面ᴱ"), "hektar": ("公顷", "百亩"),
    "kseroftalmi": ("干目", "干ᴷ目ᴼᶠ"), "metapsiki": ("超心", "超ᴹ心ᴾˢ"),
    "otari": ("兽ᴼ", "海狮"), "pakiderm": ("兽ᴾᴷ", "厚皮"),
    "pedofili": ("童爱", "童ᴾ爱ᶠ"), "polen": ("粉ᴾᴺ", "花粉"),
    "polifoni": ("多声", "多ᴾ声ᶠᴼ"), "polipodi": ("多足", "多ᴾ足ᴾᴼ"),
    "tripanosom": ("原兽ᵀ", "原兽"),
    "polenolog": ("粉学家", "花粉学家"), "polenologi": ("粉学", "花粉学ᴸᴳ"),
    "polenoz": ("粉症", "花粉症ᴼ"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.DOTALL)
BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


class SingletonOwners(unittest.TestCase):
    def test_root_labels_in_every_forward_edition(self):
        for language in ("JA", "ZH", "KO"):
            current = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            frozen = ROOT / "assignment_editions" / "legacy" / language
            for index, folder in enumerate((frozen, current)):
                with self.subTest(language=language, folder=folder):
                    if folder == frozen:
                        csv_path = folder / "kanji.csv"
                        raw = gzip.decompress((folder / "kanji.json.gz").read_bytes())
                    else:
                        csv_path = folder / "世界语词根-汉字对应列表_参照2新割当_7791.csv"
                        raw = (folder / "置換リスト_漢字.json").read_bytes()
                    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                        manual = dict(csv.reader(stream))
                    self.assertEqual({word: manual[word] for word in DISPLAYS},
                                     {word: pair[index] for word, pair in DISPLAYS.items()})
                    payload = json.loads(raw)
                    localized = next(rows for name, rows in payload.items() if name.startswith("局部"))
                    found = set()
                    for word, markup, *_ in localized:
                        if word.lower() not in DISPLAYS:
                            continue
                        ruby = RUBY.fullmatch(markup)
                        self.assertIsNotNone(ruby, word)
                        self.assertEqual(ruby[1], DISPLAYS[word.lower()][index])
                        self.assertEqual(BREAK.sub("", ruby[2]), word)
                        found.add(word)
                    self.assertEqual(found, {form for root in DISPLAYS
                                             for form in (root, root.title(), root.upper())})
