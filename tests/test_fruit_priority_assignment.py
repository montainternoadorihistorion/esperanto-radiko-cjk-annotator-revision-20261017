"""Independent full-row delta and multilingual runtime checks for the 2026-10-17 revision.

Can be copied to public tests/ without the private migration implementation.
The optional Git baseline is 40f9772 in the private integration repository.
"""
import argparse
from collections import Counter
import csv
import hashlib
import html
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
BASELINE = None
REPORT = {"delta": [], "runtime": [], "overlay": []}
GLOBAL = "全域替换用のリスト(列表)型配列(replacements_final_list)"
LOCAL = "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"
TWO = "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"
MODES = {
    "ruby": ("置換リスト_ルビ.json", "HTML格式_Ruby文字_大小调整"),
    "kanji": ("置換リスト_漢字.json", "HTML格式_Ruby文字_大小调整_汉字替换"),
    "pure": ("置換リスト_漢字_純粋置換.json", "替换后文字列のみ(仅)保留(简单替换)"),
}
CSV_NAME = "世界语词根-汉字对应列表_参照2新割当_7791.csv"
OLD = {"ananas": "菠萝", "jakv": "菠萝蜜", "ananassuk": "菠萝-汁"}
NEW = {"ananas": "菠", "jakv": "菠蜜", "ananassuk": "菠-汁", "prioritat": "优先"}
GLOSSES = {"JA": "優先権", "ZH": "优先权", "KO": "우선권"}
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)
TAGS = re.compile(r"<[^>]*>")
FORMS = {"prioritat", "PRIORITAT", "Prioritat"}


def plain(value):
    return html.unescape(TAGS.sub("", value)).replace("\xa0", " ")


def visible(value):
    return plain(re.sub(r"<rt[^>]*>.*?</rt>", "", value, flags=re.S))


def original(value, mode):
    return plain(RUBY.sub(lambda m: m[2] if mode == "kanji" else m[1], value))


def strip_ruby(value):
    return re.sub(r"<rt[^>]*>.*?</rt>", "", value).replace("<ruby>", "").replace("</ruby>", "")


def neutral(value, expected):
    def visit(match):
        root = plain(match[2]).lower()
        if root not in expected:
            return match[0]
        if match[1] != expected[root]:
            raise AssertionError((root, match[1], expected[root]))
        return "<reviewed>" + plain(match[2]) + "</reviewed>"
    return RUBY.sub(visit, value)


def baseline_bytes(path):
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                                       text=True, encoding="utf-8").strip())
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path.relative_to(repo).as_posix()}"], cwd=repo)


def load_module(app, filename, key):
    spec = importlib.util.spec_from_file_location(key, app / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render(module, data, payload, words, fmt):
    value = module.orchestrate_comprehensive_esperanto_text_replacement(
        " ◆ ".join(words), module.import_placeholders(str(data / "placeholders_skip.txt")),
        payload[LOCAL], module.import_placeholders(str(data / "placeholders_localcapture.txt")),
        payload[GLOBAL], payload[TWO], fmt)
    parts = [part.strip() for part in value.split("◆")]
    if len(parts) != len(words):
        raise AssertionError("Batch alignment changed")
    return dict(zip(words, parts))


class FruitPriorityTests(unittest.TestCase):
    def test_full_json_delta_and_sources(self):
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            data = app / "app_data"
            path = data / MODES["kanji"][0]
            after = json.loads(path.read_bytes())
            before = json.loads(baseline_bytes(path)) if BASELINE else None
            groups = {}
            for group, rows in after.items():
                names = [row[0] for row in rows]
                pieces, changed = Counter(), 0
                if before:
                    oldrows = before[group]
                    filtered = [row for row in rows if not (group == LOCAL and row[0] in FORMS)]
                    self.assertEqual(len(filtered), len(oldrows))
                    for old, new in zip(oldrows, filtered):
                        self.assertEqual(old[:1] + old[2:], new[:1] + new[2:])
                        if old[0] in FORMS:
                            self.assertEqual(old[1], old[0])
                            self.assertEqual(visible(new[1]), "优先")
                        else:
                            self.assertEqual(neutral(old[1], OLD), neutral(new[1], NEW))
                        self.assertEqual(original(old[1], "kanji"), original(new[1], "kanji"))
                        changed += old != new
                for row in rows:
                    neutral(row[1], NEW)
                    for match in RUBY.finditer(row[1]):
                        root = plain(match[2]).lower()
                        if root in NEW:
                            pieces[root] += 1
                if group in (GLOBAL, LOCAL):
                    by_name = {row[0]: row for row in rows}
                    for word in FORMS:
                        self.assertEqual(visible(by_name[word][1]), "优先")
                        self.assertEqual(original(by_name[word][1], "kanji"), word)
                    self.assertLess(names.index("prioritat"), names.index("prior"))
                groups[group] = {"rows": len(rows), "changed_existing_rows": changed,
                                 "target_pieces": dict(pieces)}
            REPORT["delta"].append({"language": language, "groups": groups,
                                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            if language == "JA":
                pure = json.loads((data / MODES["pure"][0]).read_bytes())
                for group, rows in after.items():
                    self.assertEqual(pure[group], [[r[0], strip_ruby(r[1]), *r[2:]] for r in rows])
                del pure
            mapping = dict(csv.reader(io.StringIO((data / CSV_NAME).read_text(encoding="utf-8"))))
            self.assertEqual({r: mapping[r] for r in ("ananas", "jakv", "prioritat")},
                             {r: NEW[r] for r in ("ananas", "jakv", "prioritat")})
            self.assertEqual(mapping["prior"], "院长ᴾ")
            self.assertEqual(mapping["las"], "放")
            self.assertEqual(mapping["emancip"], "放ᴱ")
            if BASELINE:
                oldraw = baseline_bytes(data / CSV_NAME)
                expected = oldraw.replace(b'ananas,\xe8\x8f\xa0\xe8\x90\x9d\n', 'ananas,菠\n'.encode())
                expected = expected.replace('jakv,菠萝蜜\n'.encode(), 'jakv,菠蜜\n'.encode())
                expected += 'prioritat,优先\n'.encode()
                self.assertEqual((data / CSV_NAME).read_bytes(), expected)
                for item in app.rglob("*"):
                    if not item.is_file() or "__pycache__" in item.parts:
                        continue
                    if item in (path, data / CSV_NAME, ROOT / "Esperanto-Kanji-Ruby-JA/app_data" / MODES["pure"][0]):
                        continue
                    self.assertEqual(item.read_bytes(), baseline_bytes(item), str(item))
            del after, before

    def test_runtime_and_manual_overlay(self):
        base = [
            "ananaso", "ananasoj", "ananason", "ananasojn", "ananasujon", "ananasfruktoj", "ananassuko",
            "jakvo", "jakvoj", "jakvon", "jakvojn", "jakvujo", "jakvarboj",
            "prioritato", "prioritatoj", "prioritaton", "prioritatojn", "prioritata", "prioritataj",
            "prioritatan", "prioritatajn", "prioritate", "prioritatas", "prioritatis", "prioritatos",
            "prioritatus", "prioritati", "prioritatu", "prioritatigi", "prioritatigo", "prioritatinda",
            "senprioritata", "malprioritata", "prioritatlisto",
            "@ananas@o", "@jakv@o", "@prioritat@o", "@prioritato@", "@prioritatigo@",
            "%prioritato%", "%ananaso%", "%jakvo%", "prioro", "prioritato prioro",
            "lasi", "emancipi", "semajntagoj", "@semajn@tagoj", "ŝakisto", "spinaco",
        ]
        words = list(dict.fromkeys(form for word in base for form in (word, word.capitalize(), word.upper())))
        controls = {"prioro": "院长ᴾo", "lasi": "放i", "emancipi": "放ᴱi",
                    "semajntagoj": "周日oj", "@semajn@tagoj": "周日oj", "ŝakisto": "棋家o"}
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            data = app / "app_data"
            runtime = load_module(app, "esp_text_replacement_module.py", "fruit_runtime_" + language)
            overlay = load_module(app, "esp_overlay_module.py", "fruit_overlay_" + language)
            corrections = [overlay.build_correction(split, str(data)) for split in
                           ("ananas/o", "jakv/o", "prioritat/o", "prioritat/ig/o", "prior/o")]
            kanji_outputs = None
            for mode, (filename, fmt) in MODES.items():
                owner = ROOT / "Esperanto-Kanji-Ruby-JA/app_data" if mode == "pure" else data
                payload = json.loads((owner / filename).read_bytes())
                outputs = render(runtime, data, payload, words, fmt)
                # Exercise the same auto-correction second pass as main.py.
                auto = overlay.auto_overlay_entries(" ◆ ".join(outputs.values()), str(data),
                                                    "ruby" if mode == "ruby" else "kanji")
                if mode == "pure":
                    auto = [[old, strip_ruby(new), ph] for old, new, ph in auto]
                if auto:
                    updated = dict(payload)
                    updated[GLOBAL] = overlay.merge_overlay(payload[GLOBAL], auto)
                    final = render(runtime, data, updated, words, fmt)
                    self.assertEqual(outputs, final)
                for word, output in outputs.items():
                    expected_original = word.replace("@", "").replace("%", "")
                    if mode != "pure":
                        self.assertEqual(original(output, mode), expected_original)
                    if word.startswith("%"):
                        self.assertEqual(visible(output), expected_original)
                    elif mode in ("kanji", "pure"):
                        text = visible(output)
                        for root in ("ananas", "jakv", "prioritat"):
                            if root in word.lower():
                                self.assertIn(NEW[root], text)
                                self.assertNotIn(root, text.lower())
                        if word in controls:
                            self.assertEqual(text, controls[word])
                        if "prioritat" in word.lower() and "prioro" not in word.lower():
                            self.assertNotIn("院长", text)
                    elif "prioritat" in word.lower() and not word.startswith("%"):
                        self.assertIn(GLOSSES[language], plain(output))
                    if mode == "pure":
                        self.assertEqual(output, visible(kanji_outputs[word]))
                    REPORT["runtime"].append({"language": language, "mode": mode, "input": word, "output": output})
                if mode == "kanji":
                    kanji_outputs = outputs
                key = "ruby" if mode == "ruby" else "kanji"
                pairs = [pair for c in corrections for pair in c[key]]
                expected = {word: strip_ruby(value) if mode == "pure" else value for word, value in pairs}
                entries = [[word, value, f"${9100000+i}$"] for i, (word, value) in enumerate(expected.items())]
                payload[GLOBAL] = overlay.merge_overlay(payload[GLOBAL], entries)
                manual = render(runtime, data, payload, list(expected), fmt)
                self.assertEqual(manual, expected)
                REPORT["overlay"].extend({"language": language, "mode": mode, "input": word, "output": value}
                                         for word, value in manual.items())
                del payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path)
    parser.add_argument("--baseline-ref")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    ROOT = args.app_root.resolve() if args.app_root else ROOT
    BASELINE = args.baseline_ref
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FruitPriorityTests))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"passed": result.wasSuccessful(), **REPORT}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
