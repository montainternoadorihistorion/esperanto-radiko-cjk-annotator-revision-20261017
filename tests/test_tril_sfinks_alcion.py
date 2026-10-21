"""Reviewed displays, versioned bird identifiers and preserved nearby roots."""
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
CURRENT = {"tril": "颤音", "sfinks": "人面狮", "alcion": "鸟ᴬᴸ", "alced": "鸟ᴬᴰ"}
LEGACY = {"tril": "颤歌", "sfinks": "狮面", "alcion": "翠鸟", "alced": "鸟ᴬᴸ"}
KEEPS = {"grifel": "石笔", "brav": "勇ᴮ", "frivol": "轻浮", "animal": "兽ᴬ"}
CSV = "世界语词根-汉字对应列表_参照2新割当_7791.csv"


def visible(text):
    return html.unescape(re.sub(r"<[^>]*>", "", re.sub(
        r"<rt[^>]*>.*?</rt>", "", text, flags=re.S)))


def fragments(text):
    return [(html.unescape(re.sub(r"<[^>]*>", "", spelling)), glyph)
            for glyph, spelling in re.findall(
                r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", text, flags=re.S)]


class TrilSfinksAlcionAssignments(unittest.TestCase):
    def test_authorities_and_user_keeps(self):
        for language in ("JA", "ZH", "KO"):
            path = ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data" / CSV
            mapping = dict(csv.reader(io.StringIO(path.read_text("utf-8"))))
            for root, glyph in {**CURRENT, **KEEPS, "alcioni": "虫ᴬᴸ"}.items():
                self.assertEqual(mapping[root], glyph, (language, root))

    def test_both_editions_normal_local_and_nearby_roots(self):
        for language in ("JA", "ZH", "KO"):
            for edition, values in (("current", CURRENT), ("legacy", LEGACY)):
                raw = ((ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_漢字.json").read_bytes()
                       if edition == "current" else gzip.decompress(
                           (ROOT / f"assignment_editions/legacy/{language}/kanji.json.gz").read_bytes()))
                payload = json.loads(raw)
                for prefix in ("全域", "局部"):
                    rows = payload[next(k for k in payload if k.startswith(prefix))]
                    wanted = {s for root in {*values, *KEEPS, "alcioni"}
                              for s in (root, root.title(), root.upper())}
                    wanted.update({"trilobit", "sfinkter"})
                    table = {r[0]: r[1] for r in rows if r[0] in wanted}
                    for root, glyph in {**values, **KEEPS, "alcioni": "虫ᴬᴸ"}.items():
                        for spelling in (root, root.title(), root.upper()):
                            self.assertEqual(visible(table[spelling]), glyph,
                                             (language, edition, prefix, spelling))
                            self.assertEqual(fragments(table[spelling]), [(spelling, glyph)])
                    if prefix == "全域":
                        self.assertEqual(fragments(table["trilobit"]),
                                         [("tri", "三"), ("lob", "叶ᴸ"), ("it", "受")])
                        self.assertEqual(table["sfinkter"], "sfinkter")
                del raw, payload, rows, table
                gc.collect()


if __name__ == "__main__":
    unittest.main()
