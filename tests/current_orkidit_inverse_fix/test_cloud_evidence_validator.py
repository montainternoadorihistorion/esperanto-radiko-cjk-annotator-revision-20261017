"""Small negative checks for the portable Cloud evidence validator."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

path = Path(__file__).with_name('verify_cloud_evidence.py')
spec = importlib.util.spec_from_file_location('current_cloud_evidence_validator', path)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class EvidenceValidatorTests(unittest.TestCase):
    def test_missing_evidence_never_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            report, bundle = validator.validate(Path(temp))
            self.assertEqual(report['status'], 'incomplete')
            self.assertFalse(report['passed'])
            self.assertIsNone(bundle)

    def test_raw_file_must_stay_inside_evidence_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(validator.safe_file(root, 'nested/result.txt'), root/'nested/result.txt')
            with self.assertRaises(AssertionError):
                validator.safe_file(root, '../outside.txt')

    def test_result_filename_only_allows_browser_collision_suffix(self):
        name = 'result_current_reviewed_ab12.txt'
        self.assertTrue(validator.filename_matches(name, name))
        self.assertTrue(validator.filename_matches('result_current_reviewed_ab12 (2).txt', name))
        for value in ('result_current_reviewed_ab12 (0).txt', 'result_current_reviewed_ab12 (2).csv', 'unrelated.txt', '../'+name):
            self.assertFalse(validator.filename_matches(value, name))

    def test_duplicate_observation_identity_is_rejected(self):
        with self.assertRaises(AssertionError):
            validator.keyed([{'id': 'one'}, {'id': 'one'}], lambda item: item['id'], 'test')

    def test_only_expected_cloud_host_is_accepted(self):
        correct = 'https://esperanto-reverter-revision-ja-20261018.streamlit.app/'
        self.assertEqual(validator.public_url(correct+'?temporary=value#section', 'JA'), correct)
        for value in ('http'+correct[5:], correct.replace('-ja-', '-zh-'), correct.replace('.app/', '.app:8000/'), correct+'other-page'):
            with self.assertRaises(AssertionError):
                validator.public_url(value, 'JA')

    def test_timestamp_requires_timezone(self):
        validator.timestamp('2026-10-18T06:00:00Z')
        with self.assertRaises(AssertionError):
            validator.timestamp('2026-10-18T06:00:00')

    def test_export_omits_machine_specific_prefix(self):
        private = 'D'+':'+'/'+'workspace/Esperanto-Reverter-JA/esperanto_converter.py'
        self.assertEqual(validator.sanitize({'path': private}), {'path': 'Esperanto-Reverter-JA/esperanto_converter.py'})
        unknown = 'C'+':'+'/'+'unrelated/private.txt'
        self.assertEqual(validator.sanitize(unknown), '[local filesystem path omitted]')


if __name__ == '__main__':
    unittest.main()
