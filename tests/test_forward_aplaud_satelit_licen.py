"""Keep the adopted displays tied to their labelled roots in both editions."""
import gzip
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "aplaŭd": ("鼓ᴬ", "拍手"),
    "satelit": ("星ˢᵀ", "卫星"),
    "licen": ("虫ᴸᶜ", "蝶ᴸᶜ"),
    "lepidopter": ("蝶ᴸ", "蝶ᴸ"),
    "kand": ("糖ᴷᴰ", "糖ᴷᴰ"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


class ApplauseSatelliteButterflyTests(unittest.TestCase):
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
                            labels.update({
                                "aplaŭdistar": [(base["aplaŭd"], "aplaŭd"), ("家", "ist"), ("群", "ar")],
                                "vetersatelit": [("气ⱽ", "veter"), (base["satelit"], "satelit")],
                            })
                        rows, = (v for k, v in table.items() if k.startswith(prefix))
                        found = {
                            key: RUBY.findall(value.replace("<br>", ""))
                            for key, value, *_ in rows if key in labels
                        }
                        self.assertEqual(found, labels)


if __name__ == "__main__":
    unittest.main()
