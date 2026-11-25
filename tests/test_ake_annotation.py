"""The learning gloss for the animal is shared by the assignment editions."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "JA": ("ナマケモノ", "[略]紀元前", "エスペラント語根-日本語訳ルビ対応リスト.csv"),
    "ZH": ("树懒", "[简称]公元前", "世界语词根-中文注释对应列表.csv"),
    "KO": ("나무늘보", "[약]aKE", "에스페란토 어근-한국어 번역 루비 대응 목록.csv"),
}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)


def pieces(markup):
    return [(key.replace("<br>", ""), gloss.replace("<br>", "")) for key, gloss in RUBY.findall(markup)]


def test_default_ake_animal_and_mixed_case_abbreviation():
    for language, (animal, abbreviation, filename) in EXPECTED.items():
        data = ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
        words = json.loads((data / "word_anno.json").read_bytes())
        assert words["ake"] == [["ake", animal]]
        assert words["aKE"] == [["aKE", abbreviation]]
        with (data / filename).open(encoding="utf-8-sig", newline="") as source:
            assert [r for r in csv.reader(source) if r and r[0] == "ake"] == [["ake", animal]]
        payload = json.loads((data / "置換リスト_ルビ.json").read_bytes())
        for group, rows in payload.items():
            if group.startswith("二文字"):
                continue
            expected = {"ake": "ake", "Ake": "Ake", "AKE": "AKE"}
            if group.startswith("全域"):
                expected.update(akeo="ake", Akeo="Ake", AKEO="AKE")
            found = {r[0]: pieces(r[1]) for r in rows if r[0] in expected}
            assert found == {k: [(spelling, animal)] for k, spelling in expected.items()}

