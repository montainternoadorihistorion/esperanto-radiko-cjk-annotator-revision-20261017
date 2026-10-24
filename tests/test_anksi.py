"""The approved anksi display follows both rule scopes; explicit keeps stay fixed."""
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
KEEPS = {"angor": "忧", "konsider": "虑", "irigaci": "水渠", "tandem": "串联"}


class AnksiAssignment(unittest.TestCase):
    def test_current_manual_correction_authority(self):
        for language in ("JA", "ZH", "KO"):
            path = ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data" / CSV
            mapping = dict(csv.reader(io.StringIO(path.read_text("utf-8"))))
            for root, glyph in {"anksi": "忧ᴬᴷ", **KEEPS}.items():
                self.assertEqual(mapping[root], glyph, (language, root))

    def test_normal_and_local_rules_preserve_sources_and_keeps(self):
        for language in ("JA", "ZH", "KO"):
            for edition, display in (("current", "忧ᴬᴷ"), ("legacy", "忧虑")):
                raw = ((ROOT / f"Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_漢字.json").read_bytes()
                       if edition == "current" else gzip.decompress(
                           (ROOT / f"assignment_editions/legacy/{language}/kanji.json.gz").read_bytes()))
                payload = json.loads(raw)
                values = {"anksi": display, **KEEPS}
                wanted = {s for root in values for s in (root, root.title(), root.upper())}
                for prefix in ("全域", "局部"):
                    rows = payload[next(k for k in payload if k.startswith(prefix))]
                    table = {r[0]: r[1] for r in rows if r[0] in wanted}
                    for root, glyph in values.items():
                        for spelling in (root, root.title(), root.upper()):
                            self.assertEqual(visible(table[spelling]), glyph,
                                             (language, edition, prefix, spelling))
                            self.assertEqual(fragments(table[spelling]), [(spelling, glyph)])
                del raw, payload, rows, table
                gc.collect()


if __name__ == "__main__":
    unittest.main()
