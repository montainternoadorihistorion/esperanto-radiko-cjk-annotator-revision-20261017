"""Execute reviewed las assignments through manual overlay merging (read-only)."""
import argparse
import json
from pathlib import Path
import unittest

from test_las_assignment import (
    GLOBAL, MODES, NEW, ROOT, load_module, neutral, original, render, visible,
)

REPORT = []


class LasOverlayTests(unittest.TestCase):
    def test_manual_corrections_in_all_languages_modes_and_cases(self):
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            data = app / "app_data"
            module = load_module(app, "esp_text_replacement_module.py", "las_overlay_runtime_" + language)
            overlay = load_module(app, "esp_overlay_module.py", "las_overlay_merge_" + language)
            corrections = [overlay.build_correction(split, str(data)) for split in
                           ("las/i", "for/las/it/aj", "emancip/o", "emancip/iĝ/o", "impertinent/a")]
            kanji = None
            for mode, (filename, fmt) in MODES.items():
                owner = ROOT / "Esperanto-Kanji-Ruby-JA/app_data" if mode == "pure" else data
                payload = json.loads((owner / filename).read_bytes())
                key = "ruby" if mode == "ruby" else "kanji"
                pairs = [pair for correction in corrections for pair in correction[key]]
                expected = {word: visible(value) if mode == "pure" else value for word, value in pairs}
                entries = [[word, value, f"${9000000 + index}$"] for index, (word, value) in enumerate(expected.items())]
                payload[GLOBAL] = overlay.merge_overlay(payload[GLOBAL], entries)
                outputs = render(module, data, payload, list(expected), fmt)
                for word, output in outputs.items():
                    self.assertEqual(output, expected[word])
                    if mode != "pure":
                        self.assertEqual(original(output, mode), word)
                    if mode == "kanji":
                        neutral(output, NEW)
                    if mode == "pure":
                        self.assertEqual(output, visible(kanji[word]))
                    REPORT.append({"language": language, "mode": mode, "input": word, "output": output})
                if mode == "kanji":
                    kanji = outputs
                del payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    ROOT = args.app_root.resolve() if args.app_root else ROOT
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LasOverlayTests))
    if args.report:
        args.report.write_text(json.dumps({"passed": result.wasSuccessful(), "cases": REPORT},
                                         ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
