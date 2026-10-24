"""Approved displays apply to both rule scopes and keep the fixed legacy."""
from pathlib import Path
import csv
import gc
import gzip
import io
import json
import unittest

from test_tril_sfinks_alcion import visible, fragments

ROOT = Path(__file__).resolve().parent.parent
CSV = "世界语词根-汉字对应列表_参照2新割当_7791.csv"
CURRENT = {"ŝtip": "木块", "pensi": "年金", "sankci": "裁ˢ"}
LEGACY = {"ŝtip": "圆木", "pensi": "养老", "sankci": "制裁"}
KEEPS = {"pens": "思", "pension": "宿", "tajl": "裁", "irigaci": "水渠", "tandem": "串联"}


class ThreeSemanticAssignments(unittest.TestCase):
    def test_current_manual_authority_distinguishes_neighbour_roots(self):
        for language in ("JA", "ZH", "KO"):
            data = ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data"
            mapping = dict(csv.reader(io.StringIO((data / CSV).read_text("utf-8"))))
            for root, glyph in {**CURRENT, **KEEPS}.items():
                self.assertEqual(mapping[root], glyph, (language, root))

    def test_normal_and_marked_tables_use_the_selected_edition(self):
        for language in ("JA", "ZH", "KO"):
            for edition, values in (("current", CURRENT), ("legacy", LEGACY)):
                raw = ((ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_漢字.json").read_bytes()
                       if edition == "current" else gzip.decompress(
                           (ROOT / f"assignment_editions/legacy/{language}/kanji.json.gz").read_bytes()))
                payload = json.loads(raw)
                for prefix in ("全域", "局部"):
                    rows = payload[next(k for k in payload if k.startswith(prefix))]
                    seen = set()
                    for row in rows:
                        if not any(root in row[1].lower() for root in values):
                            continue
                        for spelling, glyph in fragments(row[1]):
                            root = spelling.lower().replace('s^', 'ŝ')
                            if root in values:
                                seen.add(root)
                                self.assertEqual(glyph, values[root], (language, edition, prefix, row[0], spelling))
                    self.assertEqual(seen, set(values), (language, edition, prefix))
                    if prefix == "局部":
                        # Normal rules can be boundary-sensitive (pensi / pens+i).
                        # Only the explicit marked root must have a bare-root key.
                        wanted = {s for root in values for s in (root, root.title(), root.upper())}
                        table = {r[0]: r[1] for r in rows if r[0] in wanted}
                        for root, glyph in values.items():
                            for spelling in (root, root.title(), root.upper()):
                                self.assertEqual(visible(table[spelling]), glyph)
                                self.assertEqual(fragments(table[spelling]), [(spelling, glyph)])
                del raw, payload, rows, table
                gc.collect()


if __name__ == "__main__":
    unittest.main()
