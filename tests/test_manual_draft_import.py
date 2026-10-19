"""Explicit manual-draft import: guards plus real UI in fresh language processes.

Data-change guards are instrumented without modifying production dictionaries.
UI tests use actual diagnosis/import/save controls; saves remain session-only.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("JA", "ZH", "KO")
sys.path.insert(0, str(ROOT / "Esperanto-Kanji-Ruby-JA"))


class DraftImportGuards(unittest.TestCase):
    def setUp(self):
        import esp_manual_draft as drafts
        self.drafts = drafts
        self.state = {"word_probe": "greganta", "decomp_in": "",
                      "assignment_edition": "current",
                      "_assignment_edition_widget": "current"}
        self.addCleanup(patch.stopall)
        patch.object(drafts.st, "session_state", self.state).start()
        self.context = patch.object(drafts, "context_signature", return_value="context-a").start()
        drafts.remember_diagnosis("unused", "current", "greganta", "greg/ant/a", "context-a")

    def test_explicit_copy_does_not_save(self):
        self.assertEqual(self.drafts.availability("unused", "current"), "ready")
        with patch.object(self.drafts.overlay, "add_correction") as save:
            self.drafts.import_diagnosis("unused")
            save.assert_not_called()
        self.assertEqual(self.state["decomp_in"], "greg/ant/a")
        self.assertEqual(self.state[self.drafts.DRAFT_KEEP_KEY], "greg/ant/a")
        self.assertNotIn("user_corrections_session", self.state)

    def test_existing_drafts_including_whitespace_are_preserved(self):
        for draft in ("las/is", " ", "\t", "greg/ant/a"):
            with self.subTest(draft=draft):
                self.state["decomp_in"] = draft
                self.drafts.import_diagnosis("unused")
                self.assertEqual(self.state["decomp_in"], draft)
                self.assertEqual(self.state[self.drafts.NOTICE_KEY], "draft_not_empty")

    def test_single_word_validation(self):
        for word in ("", "@greganta@", "%greganta%", "greganta preganta", "greganta!", "greg\nanta"):
            with self.subTest(word=word):
                self.state["word_probe"] = word
                self.assertEqual(self.drafts.availability("unused", "current"), "single_word")
        self.state["word_probe"] = "preganta"
        self.assertEqual(self.drafts.availability("unused", "current"), "target_changed")

    def test_existing_case_and_circumflex_normalization(self):
        self.drafts.remember_diagnosis("unused", "current", "ĉuranta", "ĉur/ant/a", "context-a")
        for word in ("CxURANTA", "C^URANTA", " Ĉuranta "):
            self.state["word_probe"] = word
            self.assertEqual(self.drafts.availability("unused", "current"), "ready")

    def test_invalid_decomposition(self):
        for decomp in (None, "", "greg//ant/a", "greg/ant/a/", "preg/ant/a", "群/ant/a", "greg ant a"):
            with self.subTest(decomp=decomp):
                self.state[self.drafts.SNAPSHOT_KEY]["decomposition"] = decomp
                self.assertEqual(self.drafts.availability("unused", "current"), "invalid_decomposition")

    def test_edition_and_context_change_checked_again_in_callback(self):
        self.state["_assignment_edition_widget"] = "legacy"
        self.drafts.import_diagnosis("unused")
        self.assertEqual(self.state["decomp_in"], "")
        self.assertEqual(self.state[self.drafts.NOTICE_KEY], "context_changed")
        self.state["_assignment_edition_widget"] = "current"
        self.context.return_value = "context-b"
        self.drafts.import_diagnosis("unused")
        self.assertEqual(self.state["decomp_in"], "")
        self.assertEqual(self.state[self.drafts.NOTICE_KEY], "context_changed")
        self.context.side_effect = OSError("missing selected data")
        self.assertEqual(self.drafts.availability("unused", "current"), "context_changed")

    def test_failed_or_changed_diagnosis_clears_previous_candidate(self):
        self.drafts.begin_diagnosis("unused", "current")
        self.assertNotIn(self.drafts.SNAPSHOT_KEY, self.state)
        self.assertFalse(self.drafts.remember_diagnosis(
            "unused", "current", "greganta", "greg/ant/a", "different-context"))
        self.assertNotIn(self.drafts.SNAPSHOT_KEY, self.state)

    def test_fingerprint_failure_disables_import_without_blocking_diagnosis(self):
        self.context.side_effect = OSError("unavailable signature data")
        self.assertIsNone(self.drafts.begin_diagnosis("unused", "current"))
        self.assertFalse(self.drafts.remember_diagnosis(
            "unused", "current", "greganta", "greg/ant/a", None))
        self.assertNotIn(self.drafts.SNAPSHOT_KEY, self.state)

    def test_page_cleanup_restores_only_actual_draft(self):
        self.state["probe_ruby"] = "preg/ant/a"
        del self.state["decomp_in"]
        self.drafts.prepare_draft()
        self.assertEqual(self.state["decomp_in"], "")
        self.state["decomp_in"] = "las/is"
        self.drafts.remember_draft()
        del self.state["decomp_in"]
        self.drafts.prepare_draft()
        self.assertEqual(self.state["decomp_in"], "las/is")

    def test_context_covers_data_placeholders_and_complete_effective_entries(self):
        # Use the real function underneath setUp's guard stub.
        patch.stopall()
        with patch.object(self.drafts.st, "session_state", self.state), \
             patch.object(self.drafts.editions, "edition_signature", return_value="assignment") as data, \
             patch.object(self.drafts.editions, "file_hash", return_value="placeholder") as ph, \
             patch.object(self.drafts.overlay, "load_corrections", return_value=[]) as corrections:
            first = self.drafts.context_signature(ROOT, "current")
            self.assertEqual({Path(c.args[0]).name for c in ph.call_args_list},
                             {"placeholders_skip.txt", "placeholders_localcapture.txt"})
            corrections.return_value = [{"word": "greganta", "ruby": [["greganta", "custom"]]}]
            self.assertNotEqual(first, self.drafts.context_signature(ROOT, "current"))
            corrections.return_value = []
            ph.return_value = "changed-placeholder"
            self.assertNotEqual(first, self.drafts.context_signature(ROOT, "current"))
            ph.return_value = "placeholder"
            data.return_value = "changed-assignment"
            self.assertNotEqual(first, self.drafts.context_signature(ROOT, "current"))


def check_language(language):
    logging.disable(logging.WARNING)
    from streamlit.testing.v1 import AppTest
    app = ROOT / f"Esperanto-Kanji-Ruby-{language}"
    # Each worker is fresh; the requested language must win over the test default.
    sys.path.insert(0, str(app))
    import esp_manual_draft as drafts
    import esp_overlay_module as overlay
    os.chdir(ROOT)
    page = next((app / "pages").glob("1_*.py")).relative_to(app).as_posix()
    data = app / "app_data"
    baseline = (data / "user_corrections.json").read_bytes()
    rows = []

    def run(at):
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        assert not at.error, [e.value for e in at.error]

    for edition in ("current", "legacy"):
        at = AppTest.from_file(app / "main.py", default_timeout=180)
        run(at)
        at.switch_page(page)
        run(at)
        at.selectbox(key="_assignment_edition_widget").set_value(edition)
        run(at)

        def check(name, draft, enabled):
            assert at.text_input(key="decomp_in").value == draft, (name, draft)
            assert at.button(key="import_diagnosis_to_draft").disabled == (not enabled), name
            rows.append({"edition": edition, "scenario": name, "draft": draft,
                         "import_enabled": enabled})

        def diagnose(word, want):
            at.text_input(key="word_probe").set_value(word)
            at.button[0].click()
            run(at)
            assert at.session_state["probe_ruby"] == want

        check("initial_empty", "", False)
        diagnose("greganta", "greg/ant/a")
        check("greganta_diagnosis_does_not_fill", "", True)
        at.button(key="import_diagnosis_to_draft").click()
        run(at)
        check("greganta_explicit_import", "greg/ant/a", False)
        assert not at.session_state["user_corrections_session"]
        diagnose("preganta", "preg/ant/a")
        check("existing_draft_kept_after_new_diagnosis", "greg/ant/a", False)
        at.text_input(key="decomp_in").set_value("")
        run(at)
        check("clear_allows_current_preganta_diagnosis", "", True)
        at.button(key="import_diagnosis_to_draft").click()
        run(at)
        check("preganta_explicit_import", "preg/ant/a", False)
        assert not at.session_state["user_corrections_session"]

        at.text_input(key="decomp_in").set_value(" ")
        run(at)
        check("whitespace_is_an_existing_draft", " ", False)
        at.text_input(key="decomp_in").set_value("")
        at.text_input(key="word_probe").set_value("greganta")
        run(at)
        check("changed_word_requires_new_diagnosis", "", False)
        diagnose("greganta", "greg/ant/a")
        other = "legacy" if edition == "current" else "current"
        at.selectbox(key="_assignment_edition_widget").set_value(other)
        run(at)
        check("changed_edition_requires_new_diagnosis", "", False)
        at.selectbox(key="_assignment_edition_widget").set_value(edition)
        run(at)

        # No product file changes: instrument the data signature to simulate updates.
        with patch.object(drafts.editions, "edition_signature", return_value="changed-data"):
            run(at)
            check("changed_data_rejects_old_diagnosis", "", False)
        run(at)
        correction = overlay.build_correction("las/is", str(data), edition)
        at.session_state["user_corrections_session"] = [correction]
        run(at)
        check("changed_effective_corrections_reject_old_diagnosis", "", False)
        at.session_state["user_corrections_session"] = []
        run(at)
        diagnose("@greganta@", "greg/ant/a")
        check("marked_text_is_not_a_single_word_candidate", "", False)
        diagnose("preganta", "preg/ant/a")

        at.text_input(key="decomp_in").set_value("las/is")
        run(at)
        at.switch_page("main.py")
        run(at)
        at.switch_page(page)
        run(at)
        check("page_roundtrip_preserves_actual_draft", "las/is", False)
        at.text_input(key="decomp_in").set_value("")
        run(at)
        at.switch_page("main.py")
        run(at)
        at.switch_page(page)
        run(at)
        check("page_roundtrip_never_autofills_old_probe", "", False)

        # Saving remains a separate operation and is based on the draft.
        diagnose("greganta", "greg/ant/a")
        at.button(key="import_diagnosis_to_draft").click()
        run(at)
        assert not at.session_state["user_corrections_session"]
        next(b for b in at.button if b.label.startswith("✅")).click()
        run(at)
        saved = at.session_state["user_corrections_session"]
        assert len(saved) == 1 and saved[0]["word"] == "greganta" and saved[0]["decomp"] == "greg/ant/a"
        rows.append({"edition": edition, "scenario": "separate_save_creates_session_correction",
                     "word": saved[0]["word"], "decomposition": saved[0]["decomp"]})
        assert (data / "user_corrections.json").read_bytes() == baseline
    assert all((ROOT / f"Esperanto-Kanji-Ruby-{lang}" / "esp_manual_draft.py").read_bytes() ==
               (app / "esp_manual_draft.py").read_bytes() for lang in LANGUAGES)
    return {"passed": True, "language": language, "rows": rows,
            "checks": len(rows), "unchanged_bundled_corrections": True,
            "helper_sha256": hashlib.sha256((app / "esp_manual_draft.py").read_bytes()).hexdigest(),
            "method": "Real local AppTest controls; only data-update simulation is mocked; no Cloud operation."}


class DraftImportAppTests(unittest.TestCase):
    def test_all_languages_new_and_old(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                result = subprocess.run([sys.executable, "-B", "-X", "utf8", __file__,
                                         "--language", language], cwd=ROOT,
                                        capture_output=True, text=True, encoding="utf-8", timeout=900)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)["passed"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=LANGUAGES)
    parser.add_argument("--report", type=Path)
    args, remaining = parser.parse_known_args()
    if args.language:
        output = json.dumps(check_language(args.language), ensure_ascii=False, indent=2) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(output, "utf-8")
        print(output, end="")
    else:
        unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
