"""Check adopted root labels, protected neighbouring roots and compound boundaries."""
import gzip
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPELLINGS = {
    "malus": ("木ᴹˢ", "苹ᴹ"),
    "kolibr": ("鸟ᴷᴮ", "蜂鸟"),
    "unaŭ": ("兽ᵁ", "树懒ᵁ"),
    "mebl": ("具ᴹ", "家具"),
    "pru": ("头ᴾ", "头ᴾ"),
    "pom": ("苹", "苹"),
    "ake": ("树懒", "树懒"),
    "bradip": ("兽ᴮᴿ", "树懒ᴮ"),
    "abel": ("蜂", "蜂"),
    "bird": ("鸟", "鸟"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


class MalusFourTest(unittest.TestCase):
    def test_normal_and_local_rules_keep_distinct_roots_and_endings(self):
        for lang in ("JA", "ZH", "KO"):
            current = ROOT / f"Esperanto-Kanji-Ruby-{lang}" / "app_data" / "置換リスト_漢字.json"
            legacy = ROOT / "assignment_editions" / "legacy" / lang / "kanji.json.gz"
            for edition, path in (("legacy", legacy), ("current", current)):
                with self.subTest(lang=lang, edition=edition):
                    raw = path.read_bytes()
                    table = json.loads(gzip.decompress(raw) if edition == "legacy" else raw)
                    displays = {r: pair[edition == "current"] for r, pair in SPELLINGS.items()}
                    local = {r: [(label, r)] for r, label in displays.items()}
                    furniture = (displays["mebl"], "mebl")
                    normal = dict(local)
                    normal.update({
                        # Ordinary malus preserves mal + us. Maluso takes the tree root.
                        "malus": [("反", "mal")],
                        "maluso": local["malus"],
                        "malusoide": local["malus"],
                        "angulmebl": [("角", "angul"), furniture],
                        "letermebl": [("信ᴸ", "leter"), furniture],
                        "telermebl": [("盘", "teler"), furniture],
                        "kontormeblar": [("所ᴷ", "kontor"), furniture, ("群", "ar")],
                        "meblar": [furniture, ("群", "ar")],
                        "meblist": [furniture, ("家", "ist")],
                        "meblit": [furniture, ("受", "it")],
                        "meblovendej": [furniture, ("卖", "vend"), ("所", "ej")],
                        "meblovendist": [furniture, ("卖", "vend"), ("家", "ist")],
                        "meblotenej": [furniture, ("持", "ten"), ("所", "ej")],
                        "mebloremburist": [furniture, ("填ᴿ", "rembur"), ("家", "ist")],
                        "senmeblig": [("无", "sen"), furniture, ("使", "ig")],
                    })
                    for prefix, expected in (("全域", normal), ("局部", local)):
                        rows, = (v for k, v in table.items() if k.startswith(prefix))
                        outputs = {k: v for k, v, *_ in rows if k in expected}
                        labels = {k: RUBY.findall(v.replace("<br>", "")) for k, v in outputs.items()}
                        self.assertEqual(expected, labels)
                        if prefix == "全域":
                            visible = {k: RUBY.sub(r"\1", v) for k, v in outputs.items()}
                            self.assertEqual(visible["malus"], "反us")
                            self.assertEqual(visible["maluso"], displays["malus"] + "o")
                            self.assertEqual(visible["meblovendej"], displays["mebl"] + "o卖所")


if __name__ == "__main__":
    unittest.main()
