"""Check pollen-family, sea lion and pachyderm renderings and the frozen edition."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FROZEN = {
    "polen": "粉ᴾᴺ", "polenolog": "粉学家", "polenologi": "粉学", "polenoz": "粉症",
    "otari": "兽ᴼ", "pakiderm": "兽ᴾᴷ",
}
CURRENT = {
    "polen": "花粉ᴾᴸ", "polenolog": "花粉ᴾᴸ学家", "polenologi": "花粉ᴾᴸ学ᴸᴳ",
    "polenoz": "花粉ᴾᴸ症ᴼ", "otari": "海狮ᴼ", "pakiderm": "厚皮ᴾᴷ",
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)
BREAK = re.compile(r"<br\s*/?>", re.I)


def label_markup(html):
    return RUBY.sub(lambda match: f"{match[1]}({BREAK.sub('', match[2])})", html)


class PollenSeaLionPachyderm(unittest.TestCase):
    def test_displays_and_separate_compound_segments(self):
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
            legacy = ROOT / "assignment_editions" / "legacy" / language
            for edition, expected in [("current", CURRENT), ("legacy", FROZEN)]:
                with self.subTest(language=language, edition=edition):
                    if edition == "current":
                        csv_path = app / "世界语词根-汉字对应列表_参照2新割当_7791.csv"
                        payload = json.loads((app / "置換リスト_漢字.json").read_bytes())
                    else:
                        csv_path = legacy / "kanji.csv"
                        payload = json.loads(gzip.decompress((legacy / "kanji.json.gz").read_bytes()))
                    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                        manual = dict(csv.reader(stream))
                    self.assertEqual({root: manual[root] for root in expected}, expected)
                    local = next(rows for name, rows in payload.items() if name.startswith("局部"))
                    normal = next(rows for name, rows in payload.items() if name.startswith("全域"))

                    def case_variants(root):
                        return (root, root.title(), root.upper())

                    marked = {v: f"{display}({v})" for root, display in expected.items()
                              for v in case_variants(root)}
                    self.assertEqual({word: label_markup(html) for word, html, *_ in local
                                      if word in marked}, marked)
                    normal_forms = {root: f"{expected[root]}({root})"
                                    for root in ("polen", "otari", "pakiderm")}
                    pollen = normal_forms["polen"]
                    normal_forms.update({
                        "polenolog": pollen + "o学家(log)",
                        "polenologi": pollen + "o学ᴸᴳ(logi)",
                        "polenoz": pollen + "症ᴼ(oz)",
                    })
                    self.assertEqual({word: label_markup(html) for word, html, *_ in normal
                                      if word in normal_forms}, normal_forms)
                    components = {"flor": "花", "farun": "粉", "pulvor": "粉ᴾ",
                                  "mar": "海", "leon": "狮", "dik": "厚", "pelt": "皮ᴾ"}
                    self.assertEqual({root: manual[root] for root in components}, components)
