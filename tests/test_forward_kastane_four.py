"""Keep the adopted displays tied to their labelled roots in both editions."""
import gzip
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "kastane": ("木ᴷᴬˢ", "栗ᴷˢ"),
    "hipermetrop": ("远ᴴ", "远视"),
    "kalson": ("裤ᴷ", "内裤"),
    "streptopeli": ("鸟ˢᴱ", "鸽ˢ"),
    "miop": ("近ᴹ", "近ᴹ"),
    "tron": ("座ᵀ", "座ᵀ"),
    "kaŝtan": ("栗", "栗"),
    "maron": ("栗ᴹ", "栗ᴹ"),
    "pantalon": ("裤", "裤"),
    "kolomb": ("鸽", "鸽"),
    "turt": ("鸽ᵀ", "鸽ᵀ"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


class FourAssignmentTests(unittest.TestCase):
    def test_global_and_local_rules_keep_distinct_root_readings(self):
        for lang in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{lang}" / "app_data"
            legacy = ROOT / "assignment_editions" / "legacy" / lang / "kanji.json.gz"
            for edition, path in (("legacy", legacy), ("current", app / "置換リスト_漢字.json")):
                with self.subTest(lang=lang, edition=edition):
                    raw = path.read_bytes()
                    table = json.loads(gzip.decompress(raw) if edition == "legacy" else raw)
                    base = {r: pair[edition == "current"] for r, pair in SPELLINGS.items()}
                    expected = {r: [(k, r)] for r, k in base.items()}
                    for prefix in ("全域", "局部"):
                        labels = dict(expected)
                        if prefix == "全域":
                            # Unmarked maron is the accusative of maro in ordinary text.
                            labels["maron"] = [("海", "mar")]
                            underpants = (base["kalson"], "kalson")
                            labels.update({
                                "hipermetropec": [(base["hipermetrop"], "hipermetrop"), ("性", "ec")],
                                "bankalson": [("浴", "ban"), underpants],
                                "kalsonet": [underpants, ("小", "et")],
                                "naĝkalsonet": [("游", "naĝ"), underpants, ("小", "et")],
                                "kalsonŝtrump": [underpants, ("袜", "ŝtrump")],
                                "ŝtrumpokalson": [("袜", "ŝtrump"), underpants],
                                "senkalson": [("无", "sen"), underpants],
                            })
                        rows, = (v for k, v in table.items() if k.startswith(prefix))
                        found = {
                            key: RUBY.findall(value.replace("<br>", ""))
                            for key, value, *_ in rows if key in labels
                        }
                        self.assertEqual(found, labels)


if __name__ == "__main__":
    unittest.main()
