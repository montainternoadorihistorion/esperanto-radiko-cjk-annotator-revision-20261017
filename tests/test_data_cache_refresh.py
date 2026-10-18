"""Real Streamlit cache and overlay-cache invalidation with temporary files.

App data remains read-only. Tests execute the actual loader function ASTs so
they can exercise Streamlit's cache without creating the full page UI.
"""
import argparse
import ast
import importlib.util
import json
import logging
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from typing import List, Tuple
import unittest

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
REPORT = []
GROUPS = ["全域替换用のリスト(列表)型配列(replacements_final_list)",
          "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)",
          "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
logging.disable(logging.WARNING)  # Expected bare-mode Streamlit notices only.


def loaders(path, main):
    names = {"load_replacements_lists" if main else "_load_lists"}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names:
        raise AssertionError(f"Missing versioned loaders: {path}")
    calls = []
    def read_json(stream):
        calls.append(str(stream.name))
        return json.load(stream)
    app = path.parent if main else path.parent.parent
    spec = importlib.util.spec_from_file_location("cache_editions_" + app.name,
                                                app / "esp_assignment_edition.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.json = SimpleNamespace(load=read_json)
    namespace = {"__name__": "cache_test_" + path.parent.name, "editions": helper,
                 "Tuple": Tuple, "List": List}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    wrapper = namespace["load_replacements_lists" if main else "_load_lists"]
    cached = helper._load_lists_cached
    return wrapper, cached, calls


def rewrite(path, raw, *, preserve_mtime=False):
    previous = path.stat()
    path.write_bytes(raw)
    stamp = previous.st_mtime_ns if preserve_mtime else previous.st_mtime_ns + 2_000_000_000
    os.utime(path, ns=(previous.st_atime_ns, stamp))
    return path.stat()


class DataCacheRefreshTests(unittest.TestCase):
    def test_all_main_and_manual_json_loaders(self):
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            paths = [app / "main.py", next((app / "pages").glob("1_*.py"))]
            for main, path in zip((True, False), paths):
                with self.subTest(language=language, loader="main" if main else "manual"):
                    wrapper, cached, calls = loaders(path, main)
                    cached.clear()
                    try:
                        with tempfile.TemporaryDirectory(prefix="json_cache_refresh_") as directory:
                            fixture = Path(directory) / "same_path.json"
                            old = json.dumps({g: [["las", "留", "$1$"]] for g in GROUPS}, ensure_ascii=False).encode()
                            new = json.dumps({g: [["las", "放", "$1$"]] for g in GROUPS}, ensure_ascii=False).encode()
                            self.assertEqual(len(old), len(new))
                            fixture.write_bytes(old)
                            initial_stat = fixture.stat()
                            first = wrapper(str(fixture))
                            self.assertEqual([part[0][1] for part in first], ["留"] * 3)
                            self.assertEqual(len(calls), 1)
                            self.assertEqual(wrapper(str(fixture)), first)
                            self.assertEqual(len(calls), 1, "Unchanged file must use cache")
                            rewrite(fixture, new)
                            second = wrapper(str(fixture))
                            self.assertEqual([part[0][1] for part in second], ["放"] * 3)
                            self.assertEqual(len(calls), 2, "Same-size update must reload")
                            self.assertEqual(wrapper(str(fixture)), second)
                            self.assertEqual(len(calls), 2)
                            larger = new.replace("放".encode(), "放ᴱ".encode())
                            rewrite(fixture, larger, preserve_mtime=True)
                            third = wrapper(str(fixture))
                            self.assertEqual([part[0][1] for part in third], ["放ᴱ"] * 3)
                            self.assertEqual(len(calls), 3, "Size change with same mtime must reload")
                            rewrite(fixture, larger.replace("放ᴱ".encode(), "放ᴱX".encode()))
                            wrapper(str(fixture))
                            self.assertEqual(len(calls), 4)
                            fixture.write_bytes(old)
                            os.utime(fixture, ns=(initial_stat.st_atime_ns, initial_stat.st_mtime_ns))
                            self.assertEqual([part[0][1] for part in wrapper(str(fixture))], ["留"] * 3)
                            self.assertEqual(len(calls), 5, "Fourth generation must evict oldest cache entry")
                            fixture.unlink()
                            with self.assertRaises(FileNotFoundError):
                                wrapper(str(fixture))
                            REPORT.append({"language": language, "loader": "main" if main else "manual",
                                           "same_path_same_size_refresh": True, "unchanged_cache_hit": True,
                                           "same_mtime_size_change_refresh": True, "deleted_file_rejected": True,
                                           "bounded_to_one_entry": True,
                                           "json_reads": len(calls)})
                    finally:
                        cached.clear()

    def test_all_overlay_csv_and_width_cache_slots(self):
        for language in ("JA", "ZH", "KO"):
            app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
            spec = importlib.util.spec_from_file_location("cache_overlay_" + language, app / "esp_overlay_module.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with tempfile.TemporaryDirectory(prefix="csv_cache_refresh_") as directory:
                data = Path(directory)
                csv_path = data / "fixture.csv"
                widths_path = data / "char_widths.json"
                csv_path.write_bytes("las,留\nemancip,放\n".encode())
                widths_path.write_bytes((app / "app_data/char_widths.json").read_bytes())
                first = module._build_root_dict(str(data), csv_path.name, module.KANJI_FMT)
                self.assertIn("<ruby>留<rt", first["las"])
                self.assertIs(module._build_root_dict(str(data), csv_path.name, module.KANJI_FMT), first)
                old_size = csv_path.stat().st_size
                rewrite(csv_path, "las,放\nemancip,放\n".encode())
                self.assertEqual(csv_path.stat().st_size, old_size)
                second = module._build_root_dict(str(data), csv_path.name, module.KANJI_FMT)
                self.assertIn("<ruby>放<rt", second["las"])
                self.assertIsNot(first, second)
                self.assertIs(module._build_root_dict(str(data), csv_path.name, module.KANJI_FMT), second)
                rewrite(csv_path, "las,放\nemancip,放ᴱ\n".encode(), preserve_mtime=True)
                third = module._build_root_dict(str(data), csv_path.name, module.KANJI_FMT)
                self.assertIn("<ruby>放ᴱ<rt", third["emancip"])
                self.assertIsNot(second, third)
                # Width data also determines cached HTML, even with unchanged CSV.
                rewrite(widths_path, widths_path.read_bytes())
                fourth = module._build_root_dict(str(data), csv_path.name, module.KANJI_FMT)
                self.assertIsNot(third, fourth)
                self.assertEqual(third, fourth)
                self.assertEqual(len(module._ROOT_DICT_CACHE), 1, "Do not retain obsolete generations")
                REPORT.append({"language": language, "loader": "overlay_csv",
                               "same_path_same_size_refresh": True, "unchanged_cache_hit": True,
                               "same_mtime_size_change_refresh": True, "widths_refresh": True,
                               "cache_slots_after_four_generations": len(module._ROOT_DICT_CACHE)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    ROOT = args.app_root.resolve() if args.app_root else ROOT
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DataCacheRefreshTests))
    if args.report:
        args.report.write_text(json.dumps({"passed": result.wasSuccessful(), "results": REPORT},
                                         ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
