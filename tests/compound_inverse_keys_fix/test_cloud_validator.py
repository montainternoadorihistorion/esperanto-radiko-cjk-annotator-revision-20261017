"""Validator unit tests use synthetic observations, never claim Cloud verification."""
from pathlib import Path
import copy
import importlib.util
import json
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('compound_cloud_validator', HERE / 'verify_cloud_evidence.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class CloudValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        for name in ('cloud_fixture.json', 'cloud_forward_reference.json'):
            shutil.copyfile(HERE / name, self.base / name)
        shutil.copytree(HERE / 'cloud_expected', self.base / 'cloud_expected')
        fixture = validator.read(self.base / 'cloud_fixture.json')
        evidence = {'synthetic_validator_unit_test_only': True, 'forward': [], 'inverse': [], 'downloads': [], 'guards': []}
        inverse_meta = {l: {'url': 'https://synthetic-inverse-' + l.lower() + '.streamlit.app',
                            'utc': '2026-10-18T00:00:00Z'} for l in ('JA', 'ZH')}
        for row in fixture['forward_cases']:
            evidence['forward'].append({'case_id': row['case_id'], 'language': row['language'], 'edition': row['edition'],
                'mode': row['mode'], 'input': row['input'], 'visible': row['expected_visible'],
                'url': 'https://synthetic-forward-' + row['language'].lower() + '.streamlit.app', 'utc': '2026-10-18T00:00:00Z'})
        for row in fixture['inverse_cases']:
            meta = inverse_meta[row['language']]
            caption = validator.PREFIX[row['language']] + row['provenance']['label']
            evidence['inverse'].append({'case_id': row['case_id'], 'language': row['language'], 'edition': row['edition'],
                'input': row['input'], 'output': row['expected_output'], 'captions': [caption], **meta})
            name = row['provenance']['result_filename']
            path = self.base / 'downloads' / row['language'] / row['edition'] / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(row['expected_output'].encode())
            evidence['downloads'].append({'case_id': row['case_id'] + '_result', 'language': row['language'], 'edition': row['edition'],
                'kind': 'result', 'filename': name, 'path': path.relative_to(self.base).as_posix(), **meta})
            if row['edition'] == 'current':
                evidence['guards'].append({'language': row['language'], 'kind': 'edition_switch',
                    'from_edition': 'current', 'to_edition': 'legacy', 'caption_before': caption,
                    'caption_after_switch': caption, 'output': row['expected_output'], 'download_disabled': True, **meta})
        for row in fixture['downloads']:
            name = row['expected_filename']
            path = self.base / 'downloads' / row['language'] / row['edition'] / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.base / row['expected_file'], path)
            evidence['downloads'].append({'case_id': '_'.join((row['language'], row['edition'], row['kind'])),
                'language': row['language'], 'edition': row['edition'], 'kind': row['kind'], 'filename': name,
                'path': path.relative_to(self.base).as_posix(), **inverse_meta[row['language']]})
        self.evidence = evidence

    def tearDown(self):
        self.temp.cleanup()

    def validate(self):
        (self.base / 'cloud_evidence.json').write_text(json.dumps(self.evidence, ensure_ascii=False), encoding='utf-8')
        return validator.validate(self.base)

    def test_complete_synthetic_fixture_and_browser_duplicate_filename(self):
        self.assertTrue(self.validate()['passed'])
        row = self.evidence['downloads'][0]
        old = self.base / row['path']
        renamed = old.with_name(old.stem + ' (2)' + old.suffix)
        old.rename(renamed)
        row.update(filename=renamed.name, path=renamed.relative_to(self.base).as_posix())
        self.assertTrue(self.validate()['passed'])

    def test_missing_observation_is_incomplete(self):
        self.evidence['forward'].pop()
        result = self.validate()
        self.assertFalse(result['passed'])
        self.assertFalse(result['completed'])
        self.assertEqual(result['status'], 'incomplete')

    def test_duplicate_or_wrong_edition_is_rejected(self):
        original = copy.deepcopy(self.evidence)
        self.evidence['inverse'].append(copy.deepcopy(self.evidence['inverse'][0]))
        self.assertFalse(self.validate()['passed'])
        self.evidence = original
        self.evidence['downloads'][0]['edition'] = 'intermediate'
        self.assertFalse(self.validate()['passed'])

    def test_download_mutation_and_missing_file_are_rejected(self):
        row = self.evidence['downloads'][0]
        path = self.base / row['path']
        path.write_bytes(path.read_bytes() + b'wrong')
        self.assertFalse(self.validate()['passed'])
        path.unlink()
        self.assertEqual(self.validate()['status'], 'incomplete')

    def test_wrong_result_caption_and_enabled_stale_download_are_rejected(self):
        original = copy.deepcopy(self.evidence)
        self.evidence['inverse'][0]['captions'] = ['stale revision']
        self.assertFalse(self.validate()['passed'])
        self.evidence = original
        self.evidence['guards'][0]['download_disabled'] = False
        self.assertFalse(self.validate()['passed'])
        self.evidence['guards'][0]['download_disabled'] = True
        self.evidence['guards'][0]['caption_after_switch'] = 'relabeled old result'
        self.assertFalse(self.validate()['passed'])

    def test_wrong_filename_and_forward_visible_are_rejected(self):
        original = copy.deepcopy(self.evidence)
        self.evidence['downloads'][0]['filename'] = 'other-edition.txt'
        self.assertFalse(self.validate()['passed'])
        self.evidence = original
        self.evidence['forward'][0]['visible'] += 'x'
        self.assertFalse(self.validate()['passed'])


if __name__ == '__main__':
    unittest.main()
