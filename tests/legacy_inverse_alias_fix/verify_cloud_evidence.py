"""Verify real Cloud evidence for the fixed-old inverse-only repair.

Run with --source DIR. Missing observations produce incomplete, never success.
After every required check passes, --public-dir DIR exports only selected evidence.
This verifier edits no app, dictionary, README, or Git state.
"""
from pathlib import Path, PureWindowsPath
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
import argparse
import hashlib
import json
import re

FORWARD_HOSTS = {lang: f'esperanto-cjk-revision-{lang.lower()}-20261017.streamlit.app' for lang in ('JA', 'ZH', 'KO')}
INVERSE_HOSTS = {lang: f'esperanto-reverter-revision-{lang.lower()}-20261018.streamlit.app' for lang in ('JA', 'ZH')}
OBSERVATIONS = {'cloud_forward.json': 6, 'cloud_inverse.json': 4, 'cloud_constraints.json': 4,
                'cloud_downloads.json': 6, 'cloud_custom.json': 2, 'cloud_guards.json': 2}
FIXED_SHA = 'eed2a8bfc21a97b719e40b703ca356a6b9cd37e772811bd6d62203cfc00c4c14'
TWO_SHA = '535ba2b65eb799ccbb6cc8400a705f23b06fe2e5207ccf3c3d460641d53d1a19'
REVIEW_FILES = ['app_validation.json', 'independent_added_tests_review.json',
                'independent_alias_collision_report.json', 'independent_implementation_review.json']
HISTORY_FILES = ['reverse_forward_independent_summary.json', 'reverse_inverse_after_summary.json', 'reverse_final_validation.json']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def safe_file(root, name):
    path = Path(name)
    path = path.resolve() if path.is_absolute() else (root/path).resolve()
    assert path.is_relative_to(root.resolve()), 'Evidence file is outside the source evidence folder'
    return path


def filename_matches(actual, expected):
    if not isinstance(actual, str) or any(char in actual for char in '/\\'):
        return False
    path = Path(expected)
    return re.fullmatch(re.escape(path.stem)+r'(?: \([1-9][0-9]*\))?'+re.escape(path.suffix), actual) is not None


def public_url(value, language, forward=False):
    url = urlsplit(value)
    hosts = FORWARD_HOSTS if forward else INVERSE_HOSTS
    assert url.scheme == 'https' and url.hostname == hosts[language] and not url.username and not url.password
    assert url.path in ('', '/', '/~/+/', '/~/+'), 'Unexpected app page'
    return urlunsplit((url.scheme, url.netloc, url.path, '', ''))


def timestamp(value):
    assert isinstance(value, str)
    assert datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None


def keyed(rows, key, label):
    result = {key(row): row for row in rows}
    assert len(rows) == len(result), label+' contains duplicate identities'
    return result


def validate(root):
    required = ['reverse_cloud_fixture.json', 'cloud_download_expectations.json'] + list(OBSERVATIONS) + REVIEW_FILES + HISTORY_FILES
    missing = [name for name in required if not (root/name).is_file()]
    if missing:
        return {'status': 'incomplete', 'passed': False, 'missing_files': missing}, None
    fixture = read(root/'reverse_cloud_fixture.json')
    expected_downloads = read(root/'cloud_download_expectations.json')
    assert fixture['passed_local'] is True and expected_downloads['passed_local'] is True
    assert expected_downloads['fixture_sha256'] == sha((root/'reverse_cloud_fixture.json').read_bytes())
    assert expected_downloads['app_validation_sha256'] == sha((root/'app_validation.json').read_bytes())
    for name in REVIEW_FILES:
        assert read(root/name)['status'] == 'PASS', name
    for name in HISTORY_FILES:
        assert read(root/name)['passed'] is True, name
    final_local = read(root/'reverse_final_validation.json')
    for name in ('reverse_forward_independent_summary.json', 'reverse_inverse_after_summary.json', 'reverse_cloud_fixture.json', 'app_validation.json'):
        assert final_local['evidence_sha256'][name] == sha((root/name).read_bytes()), name+' evidence checksum differs'
    local = read(root/'app_validation.json')
    assert local['asset_changes'] == [] and local['algorithm_changes'] == []
    assert len(local['apps']) == 2 and all(row['full_pytest_passed'] == 162 for row in local['apps'])
    forward = keyed(fixture['forward_cases'], lambda row: row['case_id'], 'forward fixture')
    inverse = keyed(fixture['inverse_cases'], lambda row: row['case_id'], 'inverse fixture')
    constraints = keyed(fixture['constraint_inverse_cases'], lambda row: row['case_id'], 'constraint fixture')
    assert len(forward) == 6 and len(inverse) == 4 and len(constraints) == 4
    for row in list(forward.values()) + list(inverse.values()) + list(constraints.values()):
        assert sha(row['expected_output'].encode('utf-8')) == row['expected_output_sha256']
    for row in inverse.values():
        assert row['matches_original_lower'] is True
        assert row['expected_output'] == row['expected_original_lower_without_control_markers']
        assert row['input'] == forward[f"{row['language']}-{row['edition']}-pure"]['expected_output']
    for row in constraints.values():
        assert row['input'] == '兰炎ᵀ'
        assert row['expected_output'] == ('orkidit' if row['edition'] == 'legacy' else 'orkidkatarᵀ')
        assert row['matches_original_lower'] == (row['edition'] == 'legacy')
    csv_expected = keyed(expected_downloads['records'], lambda row: (row['language'], row['kind']), 'CSV fixture')
    assert set(csv_expected) == {(lang, kind) for lang in ('JA', 'ZH') for kind in ('full', 'two_column', 'effective')}
    for row in csv_expected.values():
        if row['kind'] in ('full', 'two_column'):
            assert row['sha256'] == {'full': FIXED_SHA, 'two_column': TWO_SHA}[row['kind']]
    observed = {name: read(root/name) for name in OBSERVATIONS}
    assert all(isinstance(rows, list) for rows in observed.values())
    coverage = {name: len(rows) for name, rows in observed.items()}
    if coverage != OBSERVATIONS:
        return {'status': 'incomplete', 'passed': False, 'coverage': coverage, 'required': OBSERVATIONS}, None
    referenced = []
    normal_urls = []
    for name, expected, is_forward in (('cloud_forward.json', forward, True), ('cloud_inverse.json', inverse, False), ('cloud_constraints.json', constraints, False)):
        rows = keyed(observed[name], lambda row: row['case_id'], name)
        assert set(rows) == set(expected), name+' case coverage differs'
        for case_id, row in rows.items():
            exp = expected[case_id]
            assert all(row[key] == exp[key] for key in ('language', 'edition', 'input')), case_id
            assert row['output'] == exp['expected_output'], 'Visible output differs: '+case_id
            raw = safe_file(root, row['local_path']).read_bytes()
            assert raw == exp['expected_output'].encode('utf-8'), 'Full download bytes differ: '+case_id
            assert sha(raw) == row['sha256'] == exp['expected_output_sha256']
            if 'bytes' in row:
                assert row['bytes'] == len(raw)
            clean_url = public_url(row['url'], row['language'], is_forward)
            if urlsplit(clean_url).path in ('', '/'):
                normal_urls.append(case_id)
            timestamp(row['utc'])
            if not is_forward:
                assert filename_matches(row['filename'], exp['provenance']['result_filename']), 'Versioned result filename differs: '+case_id
                assert exp['provenance']['label'] in row['provenance_caption'], 'Result provenance caption differs: '+case_id
            referenced.append({'observation': name, 'identity': case_id, 'source': row['local_path'], 'target': 'cloud_outputs/'+case_id+'.txt', 'sha256': sha(raw)})
    # Confirm the measured forward text, rather than merely the local fixture, was reversed.
    forward_observed = {row['case_id']: row for row in observed['cloud_forward.json']}
    for row in observed['cloud_inverse.json']:
        assert row['input'] == forward_observed[f"{row['language']}-{row['edition']}-pure"]['output']
    csv_rows = keyed(observed['cloud_downloads.json'], lambda row: (row['language'], row['kind']), 'Cloud CSV')
    assert set(csv_rows) == set(csv_expected)
    for identity, row in csv_rows.items():
        exp = csv_expected[identity]
        raw = safe_file(root, row['local_path']).read_bytes()
        assert len(raw) == row['bytes'] == exp['bytes']
        assert sha(raw) == row['sha256'] == exp['sha256']
        assert filename_matches(row['filename'], exp['filename'])
        if 'url' in row:
            public_url(row['url'], row['language'])
        if 'utc' in row:
            timestamp(row['utc'])
        referenced.append({'observation': 'cloud_downloads.json', 'identity': '-'.join(identity), 'source': row['local_path'], 'target': 'cloud_outputs/'+'-'.join(identity)+'.csv', 'sha256': sha(raw)})
    customs = keyed(observed['cloud_custom.json'], lambda row: row['language'], 'Cloud custom')
    assert set(customs) == {'JA', 'ZH'}
    for language, row in customs.items():
        exp = inverse[language+'-legacy-effective']
        assert row['input'] == exp['input'] and row['output'] == exp['expected_output']
        upload = csv_expected[(language, 'effective')]
        assert row['upload_sha256'] == upload['sha256'] == csv_rows[(language, 'effective')]['sha256']
        assert filename_matches(row['filename'], upload['filename'])
        public_url(row['url'], language)
        timestamp(row['utc'])
    guards = keyed(observed['cloud_guards.json'], lambda row: row['language'], 'Cloud guards')
    assert set(guards) == {'JA', 'ZH'}
    for language, row in guards.items():
        assert row['from_edition'] == 'current' and row['to_edition'] == 'legacy'
        assert row['options'] == ['新版（更新中）', '旧版（固定）']
        assert all(row[key] is True for key in ('download_disabled', 'old_caption_retained', 'reconvert_enabled'))
        if 'caption_before_switch' in row and 'caption_after_switch' in row:
            label = inverse[language+'-current-effective']['provenance']['label']
            assert label in row['caption_before_switch'] and label in row['caption_after_switch']
        if 'url' in row:
            public_url(row['url'], language)
        timestamp(row['utc'])
    report = {'status': 'passed', 'passed': True, 'coverage': coverage,
              'full_byte_downloads_checked': len(referenced), 'matching_edition_roundtrips': 4,
              'old_bare_root_restored_constraints': 2, 'current_bare_root_known_limit_controls': 2,
              'custom_effective_csv_matches': 2, 'two_edition_guard_observations': 2,
              'observed_normal_root_url_cases': normal_urls,
              'filename_rule': 'Exact expected inverse-result/dictionary filename; only a final browser-added positive-integer collision suffix is allowed. Forward filenames are retained as observations; their output bytes are independently checked.',
              'scope': 'Actual browser outputs/download bytes compared with frozen local expectations. No universal restoration or original capitalization claim.',
              'fixture_stage_note': 'The fixture and app_validation retain their original local-only / Cloud-pending notes. This separate report validates the later observed Cloud files.',
              'limitations': fixture.get('limitations', []),
              'guards_scope': 'Disabled and re-enabled controls are browser observations; recorded captions are independently compared when supplied.',
              'custom_scope': 'Browser upload/result observation matched against the downloaded effective CSV SHA and the same fixed-old sample; exhaustive custom index equivalence is covered by local tests.',
              'inputs': [{'file': name, 'sha256': sha((root/name).read_bytes())} for name in required],
              'downloads': referenced}
    return report, {'fixture': fixture, 'observed': observed, 'referenced': referenced}


def private_pattern():
    return re.compile(r'(?i)(?<![a-z])[a-z]:[\\/]|'+re.escape('/'+'Users'+'/')+'|'+re.escape('/'+'home'+'/')+r'[^/]+/|'+re.escape('file'+':'+'//'))


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str) and private_pattern().search(value):
        path = PureWindowsPath(value)
        # Preserve useful application-relative pointers, never machine-specific prefixes.
        aliases = {'Esperanto-Reverter-JA': 'Esperanto-Reverter-JA', 'Esperanto-Reverter-ZH': 'Esperanto-Reverter-ZH',
                   'kanjized-esperanto-reverter': 'Esperanto-Reverter-JA', 'hanzized-esperanto-reverter-zh_更新版20260822': 'Esperanto-Reverter-ZH'}
        for pos, part in enumerate(path.parts):
            if part in aliases:
                return '/'.join((aliases[part], *path.parts[pos+1:]))
        return '[local filesystem path omitted]'
    return value


def export(root, dest, report, bundle):
    assert report.get('passed') is True
    # Only explicitly selected reports are published; no preparation scripts, ZIPs, or baselines.
    extras = ['decision.md', 'reverse_cloud_fixture.json', 'cloud_download_expectations.json'] + REVIEW_FILES + HISTORY_FILES
    missing = [name for name in extras if not (root/name).is_file()]
    assert not missing, 'Missing final evidence reports: '+', '.join(missing)
    dest.mkdir(parents=True, exist_ok=True)
    publication = []
    for name in extras:
        source = root/name
        if source.suffix == '.json':
            value = read(source)
            if name in REVIEW_FILES:
                assert value['status'] == 'PASS'
            if name in HISTORY_FILES:
                assert value['passed'] is True
            cleaned = sanitize(value)
            if cleaned == value:
                (dest/name).write_bytes(source.read_bytes())
            else:
                save(dest/name, cleaned)
        else:
            assert not private_pattern().search(source.read_text(encoding='utf-8'))
            (dest/name).write_bytes(source.read_bytes())
        publication.append({'file': name, 'source_sha256': sha(source.read_bytes()), 'published_sha256': sha((dest/name).read_bytes()), 'local_paths_removed': source.read_bytes() != (dest/name).read_bytes()})
    for row in bundle['referenced']:
        path = dest/row['target']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(safe_file(root, row['source']).read_bytes())
    safe_fields = {'case_id', 'language', 'edition', 'input', 'output', 'bytes', 'sha256', 'filename', 'provenance_caption', 'url', 'utc', 'kind', 'upload_sha256', 'from_edition', 'to_edition', 'options', 'download_disabled', 'old_caption_retained', 'reconvert_enabled', 'caption_before_switch', 'caption_after_switch'}
    for name, values in bundle['observed'].items():
        copied = []
        for row in values:
            item = {key: value for key, value in row.items() if key in safe_fields}
            if 'url' in item:
                item['url'] = public_url(item['url'], item['language'], name == 'cloud_forward.json')
            matches = [file for file in bundle['referenced'] if file['observation'] == name and file['identity'] == (row.get('case_id') if name != 'cloud_downloads.json' else row['language']+'-'+row['kind'])]
            if matches:
                assert len(matches) == 1
                item['local_path'] = matches[0]['target']
            copied.append(item)
        save(dest/name, copied)
    # These traces are small passing-suite summaries with no application/user text.
    for name in ('app_pytest_JA.log', 'app_pytest_ZH.log'):
        raw = (root/name).read_bytes()
        assert not private_pattern().search(raw.decode('utf-8'))
        (dest/name).write_bytes(raw)
    if (root/'cloud_before.json').is_file():
        before = read(root/'cloud_before.json')
        before['url'] = public_url(before['url'], 'JA')
        timestamp(before['utc'])
        save(dest/'cloud_before.json', sanitize(before))
    # Optional screenshots must have been explicitly reviewed by the browser operator.
    if (root/'cloud_visual_review.json').is_file():
        visual = read(root/'cloud_visual_review.json')
        for row in visual['screenshots']:
            raw = safe_file(root, row['file']).read_bytes()
            assert sha(raw) == row['sha256']
            target = Path('screenshots')/Path(row['file']).name
            (dest/target).parent.mkdir(parents=True, exist_ok=True)
            (dest/target).write_bytes(raw)
            row['file'] = target.as_posix()
        save(dest/'cloud_visual_review.json', sanitize(visual))
    (dest/'verify_cloud_evidence.py').write_bytes(Path(__file__).read_bytes())
    public_report, _ = validate(dest)
    assert public_report['passed']
    for item in public_report['downloads']:
        item['source'] = item['target']
    save(dest/'cloud_verification.json', public_report)
    save(dest/'publication_sources.json', publication)
    for path in dest.rglob('*'):
        if path.is_file() and path.suffix in ('.json', '.py', '.txt', '.csv', '.md', '.log'):
            assert not private_pattern().search(path.read_text(encoding='utf-8-sig')), 'Local private path found in '+path.name
    files = [{'path': path.relative_to(dest).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in sorted(dest.rglob('*')) if path.is_file() and path.name != 'evidence_manifest.json']
    save(dest/'evidence_manifest.json', {'passed': True, 'local_absolute_paths_found': 0, 'files': files})
    return {'files': len(files), 'manifest_sha256': sha((dest/'evidence_manifest.json').read_bytes())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--public-dir', type=Path)
    args = parser.parse_args()
    root = args.source.resolve()
    try:
        report, bundle = validate(root)
        if args.public_dir and report.get('passed'):
            report['public_export'] = export(root, args.public_dir.resolve(), report, bundle)
    except Exception as exc:
        report = {'status': 'failed', 'passed': False, 'error_type': type(exc).__name__, 'error': str(exc)}
    save(root/'cloud_verification.json', report)
    print(json.dumps({key: value for key, value in report.items() if key not in ('inputs', 'downloads')}, ensure_ascii=False))
    return 0 if report.get('passed') else 2 if report['status'] == 'incomplete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
