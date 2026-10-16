"""Independent closed-delta and runtime checks for las=放 / emancip=放ᴱ.

The optional Git baseline is compared row-for-row, without importing the
migration implementation.  --app-root also permits checking the private source
tree with the same assertions.  No app data or session corrections are written.
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
REPORT = {"json_delta": [], "runtime": [], "overlay": [], "source_delta": []}
OLD = {"las": "留", "emancip": "放"}
NEW = {"las": "放", "emancip": "放ᴱ"}
CSV_NAME = "世界语词根-汉字对应列表_参照2新割当_7791.csv"
GLOBAL = "全域替换用のリスト(列表)型配列(replacements_final_list)"
LOCAL = "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"
TWO = "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)
TAGS = re.compile(r"<[^>]*>")
MODES = {
    "ruby": ("置換リスト_ルビ.json", "HTML格式_Ruby文字_大小调整"),
    "kanji": ("置換リスト_漢字.json", "HTML格式_Ruby文字_大小调整_汉字替换"),
    "pure": ("置換リスト_漢字_純粋置換.json", "替换后文字列のみ(仅)保留(简单替换)"),
}
FAMILIES = {
    "las": ["al/las/ebl", "al/las/ebl/a kurent", "al/las", "de/las", "du/on/tra/las",
            "el/las/aĵ", "el/las", "el/las/i akv", "el/las/il", "el/las/i objekt",
            "el/las/i ov", "el/las/i sang", "el/las/it/a gas", "el/las/tub", "en/las",
            "flank/e/n/las", "for/las", "for/las/i ofic", "for/las/it", "for/las/it/a infan",
            "las/ad", "las", "las/it/aĵ", "liber/las", "lum/tra/las", "ne/for/las/ebl",
            "post/las/aĵ", "post/las", "preter/las", "re/las", "re/las/ad",
            "re/las/a fenomen", "re/las/i obtur/il", "re/las/i si", "re/las/temp",
            "sang/el/las", "tra/las", "tra/las/a grund", "tra/las/a membran", "tra/las/iv",
            "for/las/it/ec", "ne/tra/las", "tra/las/ant", "du/on/tra/las/ant",
            "du/on/tra/las/iv", "flank/las", "fum/el/las/il"],
    "emancip": ["emancip/ad", "emancip/ad/o de la sklav", "emancip", "emancip/iĝ"],
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def plain(value):
    return html.unescape(TAGS.sub("", value)).replace("\xa0", " ")


def visible(value):
    return plain(re.sub(r"<rt[^>]*>.*?</rt>", "", value, flags=re.S))


def original(value, mode="kanji"):
    return plain(RUBY.sub(lambda m: m[2] if mode == "kanji" else m[1], value))


def neutral(value, expected):
    """Keep all unrelated HTML bytes, normalize only the two approved pieces."""
    def visit(match):
        root = plain(match[2]).lower()
        if root not in NEW:
            return match[0]
        if match[1] != expected[root]:
            raise AssertionError((root, match[1], expected[root]))
        return "<reviewed-root>" + plain(match[2]) + "</reviewed-root>"
    return RUBY.sub(visit, value)


def baseline_bytes(path):
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"],
                                       cwd=ROOT, text=True, encoding="utf-8").strip())
    relative = path.relative_to(repo).as_posix()
    return subprocess.check_output(["git", "show", f"{BASELINE}:{relative}"], cwd=repo)


def load_module(app, filename, key):
    spec = importlib.util.spec_from_file_location(key, app / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render(module, data, payload, words, fmt):
    output = module.orchestrate_comprehensive_esperanto_text_replacement(
        " ◆ ".join(words), module.import_placeholders(str(data / "placeholders_skip.txt")),
        payload[LOCAL], module.import_placeholders(str(data / "placeholders_localcapture.txt")),
        payload[GLOBAL], payload[TWO], fmt)
    parts = [part.strip() for part in output.split("◆")]
    if len(parts) != len(words):
        raise AssertionError("Runtime batch alignment changed")
    return dict(zip(words, parts))


class LasAssignmentTests(unittest.TestCase):
    def test_all_json_rows_and_unchanged_sources(self):
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            path = app / "app_data" / MODES["kanji"][0]
            raw = path.read_bytes()
            after = json.loads(raw)
            before = json.loads(baseline_bytes(path)) if BASELINE else None
            if before is not None:
                self.assertEqual(list(before), list(after))
            groups = {}
            for group, rows in after.items():
                pieces, changed = Counter(), 0
                if before is not None:
                    self.assertEqual(len(before[group]), len(rows))
                for index, row in enumerate(rows):
                    normalized = neutral(row[1], NEW)
                    for match in RUBY.finditer(row[1]):
                        root = plain(match[2]).lower()
                        if root in NEW:
                            pieces[root] += 1
                    if before is not None:
                        old = before[group][index]
                        self.assertEqual(row[:1] + row[2:], old[:1] + old[2:])
                        self.assertEqual(normalized, neutral(old[1], OLD))
                        self.assertEqual(original(row[1]), original(old[1]))
                        changed += row[1] != old[1]
                groups[group] = {"rows": len(rows), "changed_rows": changed,
                                 "target_pieces": dict(pieces)}
            self.assertEqual(groups[GLOBAL]["target_pieces"], {"las": 624, "emancip": 9})
            self.assertEqual(groups[LOCAL]["target_pieces"], {"las": 3, "emancip": 3})
            self.assertEqual(groups[TWO]["target_pieces"], {})
            REPORT["json_delta"].append({"language": language, "groups": groups,
                                         "sha256": sha(raw), "all_other_bytes_in_values_preserved": True,
                                         "all_keys_order_placeholders_counts_preserved": True})
            if language == "JA":
                pure_path = app / "app_data" / MODES["pure"][0]
                pure = json.loads(pure_path.read_bytes())
                self.assertEqual(list(after), list(pure))
                for group, rows in after.items():
                    self.assertEqual(pure[group], [[row[0], re.sub(r"<rt[^>]*>.*?</rt>", "", row[1]).replace(
                        "<ruby>", "").replace("</ruby>", ""), *row[2:]] for row in rows])
                if BASELINE:
                    old_pure = json.loads(baseline_bytes(pure_path))
                    for group, rows in pure.items():
                        self.assertEqual(len(rows), len(old_pure[group]))
                        for old, new in zip(old_pure[group], rows):
                            self.assertEqual(old[:1] + old[2:], new[:1] + new[2:])
                del pure
            if BASELINE:
                # Every other tracked runtime asset stays byte-identical.  This
                # includes all annotation JSON/CSV, corrections, widths, settings,
                # placeholders, executable modules, and Cloud entrypoints.
                for item in app.rglob("*"):
                    if not item.is_file() or "__pycache__" in item.parts:
                        continue
                    if item in (path, app / "app_data" / CSV_NAME,
                                ROOT / "Esperanto-Kanji-Ruby-JA/app_data" / MODES["pure"][0]):
                        continue
                    self.assertEqual(item.read_bytes(), baseline_bytes(item), str(item))

    def test_assignment_csv_and_generator_sources(self):
        files = [ROOT / f"Esperanto-Kanji-Ruby-{lang}/app_data" / CSV_NAME
                 for lang in ("JA", "ZH", "KO")]
        out = ROOT / "_analysis_20260625/out"
        if out.is_dir():
            files.append(out / "kanji_root.csv")
        for path in files:
            raw = path.read_bytes()
            mapping = dict(csv.reader(io.StringIO(raw.decode("utf-8"))))
            self.assertEqual({root: mapping[root] for root in NEW}, NEW)
            if BASELINE:
                oldraw = baseline_bytes(path)
                expected = oldraw
                for root, value in OLD.items():
                    oldcell = (root + "," + value + "\n").encode("utf-8")
                    newcell = (root + "," + NEW[root] + "\n").encode("utf-8")
                    self.assertEqual(expected.count(oldcell), 1)
                    expected = expected.replace(oldcell, newcell)
                self.assertEqual(raw, expected)
            REPORT["source_delta"].append({"path": str(path.relative_to(ROOT)), "sha256": sha(raw),
                                           "only_cells_changed": NEW})
        if out.is_dir():
            path = out / "word_kanji.json"
            new = json.loads(path.read_bytes())
            selected = {root: [key for key, pairs in new.items() if any(r == root for r, v in pairs)]
                        for root in NEW}
            self.assertEqual(selected, FAMILIES)
            if BASELINE:
                old = json.loads(baseline_bytes(path))
                self.assertEqual(list(new), list(old))
                for key, pairs in new.items():
                    self.assertEqual(len(pairs), len(old[key]))
                    for (root, value), (oldroot, oldvalue) in zip(pairs, old[key]):
                        self.assertEqual(root, oldroot)
                        self.assertEqual(value, NEW[root] if root in NEW else oldvalue)
            REPORT["source_delta"].append({"path": str(path.relative_to(ROOT)),
                                           "changed_pair_counts": {r: len(v) for r, v in selected.items()}})

    def test_runtime_all_languages_modes_and_manual_overlay(self):
        family_words = [root.replace("/", "") + ending for roots in FAMILIES.values()
                        for root in roots for ending in ("", "i", "o")]
        target_words = [root + suffix for root in NEW for suffix in
                        ("i", "as", "is", "os", "us", "u", "o", "oj", "on", "ojn",
                         "a", "aj", "an", "ajn", "e", "ita", "itaj", "itajn", "anta", "intaj", "ontan")]
        controls = ["ananaso", "prioritato", "lastan", "lasagno", "lasero", "klaso", "glaso",
                    "elasta", "impertinenta", "semajno", "semajntagoj", "dusemajnan", "semajnfino",
                    "ŝakisto", "ŝakistoj", "ŝakiston", "ŝakistino", "kisto", "instruisto",
                    "semajn semajn semajn", "semajn semajntago semajn", "@semajn@tagoj"]
        words = list(dict.fromkeys(form for word in family_words + target_words + controls
                                  for form in (word, word.capitalize(), word.upper())))
        words += ["@las@", "@Las@", "@LAS@", "@emancip@", "@Emancip@", "@EMANCIP@",
                  "%lasi%", "%emancipo%", "%@las@%", "@las@i kaj @emancip@o"]
        REPORT["runtime_inputs_per_mode"] = len(words)
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            data = app / "app_data"
            module = load_module(app, "esp_text_replacement_module.py", "las_runtime_" + language)
            kanji_outputs = old_kanji_outputs = None
            for mode, (filename, fmt) in MODES.items():
                print(f"las runtime {language}/{mode}: {len(words)} inputs", flush=True)
                owner = ROOT / "Esperanto-Kanji-Ruby-JA/app_data" if mode == "pure" else data
                path = owner / filename
                payload = json.loads(path.read_bytes())
                outputs = render(module, data, payload, words, fmt)
                previous = None
                if BASELINE and mode == "kanji":
                    previous = render(module, data, json.loads(baseline_bytes(path)), words, fmt)
                for word in words:
                    output = outputs[word]
                    with self.subTest(language=language, mode=mode, input=word):
                        self.assertNotRegex(output, r"\$[^$]+\$")
                        if mode != "pure":
                            expected_original = word[1:-1] if word.startswith("%") and word.endswith("%") else word.replace("@", "")
                            self.assertEqual(original(output, mode), expected_original)
                        if mode == "kanji":
                            neutral(output, NEW)
                            if previous:
                                self.assertEqual(neutral(output, NEW), neutral(previous[word], OLD))
                            if word.lower() in ("lasi", "emancipo", "@las@", "@emancip@"):
                                root = "las" if "las" in word.lower() else "emancip"
                                self.assertIn(NEW[root], visible(output))
                        if mode == "pure":
                            self.assertEqual(output, visible(kanji_outputs[word]))
                        if word in controls and previous:
                            self.assertEqual(output, previous[word])
                    REPORT["runtime"].append({"language": language, "mode": mode,
                                              "input": word, "output": output,
                                              "before": previous[word] if previous else None})
                if mode == "kanji":
                    kanji_outputs, old_kanji_outputs = outputs, previous
                del payload
            overlay = load_module(app, "esp_overlay_module.py", "las_overlay_" + language)
            for split in ("las/i", "for/las/it/aj", "emancip/o", "emancip/iĝ/o", "impertinent/a"):
                correction = overlay.build_correction(split, str(data))
                for mode in ("ruby", "kanji"):
                    for word, output in correction[mode]:
                        self.assertEqual(original(output, mode), word)
                        if mode == "kanji":
                            neutral(output, NEW)
                            for root in NEW:
                                if root in split.split("/"):
                                    self.assertIn(NEW[root], visible(output))
                REPORT["overlay"].append({"language": language, "decomposition": split,
                                           "correction": correction})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path)
    parser.add_argument("--baseline-ref")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    ROOT = args.app_root.resolve() if args.app_root else ROOT
    BASELINE = args.baseline_ref
    REPORT.update({"app_root": str(ROOT), "baseline_ref": BASELINE})
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LasAssignmentTests))
    REPORT["passed"] = result.wasSuccessful()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
