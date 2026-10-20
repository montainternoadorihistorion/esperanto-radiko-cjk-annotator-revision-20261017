"""Portable checks for the reviewed mikrob and diafragm assignment families."""
from pathlib import Path
import csv
import gc
import gzip
import html
import io
import json
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
VALUES = {
    "mikrob": "微生物", "diafragm": "隔膜",
    "mikrobicid": "微生物杀", "mikrobologi": "微生物学ᴸᴳ",
}
LEGACY_LOCAL = {
    "mikrob": "细菌", "diafragm": "光圈",
    "mikrobicid": "细菌杀", "mikrobologi": "细菌学",
}
CONTROLS = {
    "mikrobiologi": "微生ᴮᴼ学ᴸᴳ", "mikrobreĉi": "微角砾岩",
    "gelaten": "明胶", "ŝakal": "胡狼", "bedaŭr": "惜ᴮ",
    "raŭk": "哑ᴿ", "buf": "蟆", "lofi": "蟆鱼",
    "aŭtomat": "自动", "aŭtomaci": "自动ᴬᶜ",
}
CSV = "世界语词根-汉字对应列表_参照2新割当_7791.csv"


def visible(text):
    return html.unescape(re.sub(
        r"<[^>]*>", "", re.sub(r"<rt[^>]*>.*?</rt>", "", text, flags=re.S)))


def fragments(text):
    return [
        (html.unescape(re.sub(r"<[^>]*>", "", spelling)), glyph)
        for glyph, spelling in re.findall(
            r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", text, flags=re.S)
    ]


class MikrobDiafragmAssignments(unittest.TestCase):
    def test_current_csv_and_preserved_other_choices(self):
        for language in ("JA", "ZH", "KO"):
            data = ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data"
            mapping = dict(csv.reader(io.StringIO((data / CSV).read_text("utf-8"))))
            for root, glyph in {**VALUES, **CONTROLS}.items():
                self.assertEqual(mapping[root], glyph, (language, root))

    def test_local_edition_displays_and_normal_family_splits(self):
        for language in ("JA", "ZH", "KO"):
            for edition in ("current", "legacy"):
                if edition == "current":
                    raw = (ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data"
                           / "置換リスト_漢字.json").read_bytes()
                else:
                    raw = gzip.decompress(
                        (ROOT / f"assignment_editions/legacy/{language}/kanji.json.gz").read_bytes())
                payload = json.loads(raw)
                local = {
                    row[0]: row[1]
                    for row in payload[next(key for key in payload if key.startswith("局部"))]
                }
                normal = {
                    row[0]: row[1]
                    for row in payload[next(key for key in payload if key.startswith("全域"))]
                    if row[0] in {"mikrobiologi", "mikrobreĉi", "mikrobologi", "mikrobicid"}
                }
                for root, glyph in (VALUES if edition == "current" else LEGACY_LOCAL).items():
                    for spelling in (root, root.title(), root.upper()):
                        self.assertEqual(visible(local[spelling]), glyph,
                                         (language, edition, spelling))
                        self.assertEqual(fragments(local[spelling]), [(spelling, glyph)])
                # These two words have valid existing splits; prefix resemblance
                # to mikrob must never rewrite them into the new mikrob glyph.
                self.assertEqual(fragments(normal["mikrobiologi"]),
                                 [("mikro", "微"), ("bio", "生ᴮᴼ"), ("logi", "学ᴸᴳ")])
                self.assertEqual(fragments(normal["mikrobreĉi"]),
                                 [("mikro", "微"), ("breĉi", "角砾岩")])
                micro = VALUES["mikrob"] if edition == "current" else "细菌"
                self.assertEqual(fragments(normal["mikrobologi"]),
                                 [("mikrob", micro), ("logi", "学ᴸᴳ")])
                self.assertEqual(visible(normal["mikrobologi"]), micro + "o学ᴸᴳ")
                self.assertEqual(fragments(normal["mikrobicid"]),
                                 [("mikrob", micro), ("icid", "杀")])
                # Legacy whole-root @ data intentionally differs from its
                # normal decomposition; preserve the fixed old edition.
                legacy_microbio = "微生学" if edition == "legacy" else CONTROLS["mikrobiologi"]
                self.assertEqual(visible(local["mikrobiologi"]), legacy_microbio)
                self.assertEqual(visible(local["mikrobreĉi"]), CONTROLS["mikrobreĉi"])
                del raw, payload, local, normal
                gc.collect()


if __name__ == "__main__":
    unittest.main()
