"""Verify recorded Cloud observations and real downloaded bytes, without browser access.

No missing observation is inferred from a local test. This file also supports
portable evidence packages when their paths remain relative to the package.
"""
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import argparse
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
FIXTURE_SHA256 = '9d4b4675d5a251a1625f9cecc42278bcba2553947c1249b1513e9313ca4458aa'
PREFIX = {'JA': '変換結果の版: ', 'ZH': '转换结果使用的版本: '}
LANGUAGES = ('JA', 'ZH')
EDITIONS = ('current', 'legacy')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def resolve(base, value):
    path = Path(value)
    return path if path.is_absolute() else base / path


def filename_matches(observed, expected):
    if observed == expected:
        return True
    path = Path(expected)
    return isinstance(observed, str) and re.fullmatch(
        re.escape(path.stem) + r' \([1-9][0-9]*\)' + re.escape(path.suffix), observed
    ) is not None


class Check:
    def __init__(self):
        self.errors = []
        self.missing = []
        self.count = 0

    def require(self, condition, message):
        self.count += 1
        if not condition:
            self.errors.append(message)
        return condition

    def rows(self, value, fields, expected, label):
        if not isinstance(value, list):
            self.require(False, label + ': observations must be an array')
            self.missing.append(label)
            return {}
        found = {}
        for row in value:
            try:
                key = tuple(row[field] for field in fields)
                hash(key)
            except (KeyError, TypeError):
                self.require(False, label + ': malformed identity')
                continue
            self.require(key not in found, label + ': duplicate ' + repr(key))
            found[key] = row
        absent = set(expected) - set(found)
        self.missing.extend(label + ' ' + repr(key) for key in sorted(absent))
        self.require(not absent, label + ': missing ' + repr(sorted(absent)))
        self.require(not set(found) - set(expected), label + ': unexpected identities')
        return found

    def observation(self, row, label):
        try:
            url = urlparse(row['url'])
            self.require(url.scheme == 'https' and bool(url.hostname)
                         and url.hostname.endswith('.streamlit.app'), label + ': invalid Cloud URL')
            stamp = datetime.fromisoformat(row['utc'].replace('Z', '+00:00'))
            self.require(stamp.tzinfo is not None, label + ': UTC timestamp needs timezone')
            return url.hostname
        except (KeyError, TypeError, ValueError):
            self.require(False, label + ': missing or invalid URL/timestamp')
            return None

    def file(self, base, row, expected, label):
        try:
            path = resolve(base, row['path'])
            raw = path.read_bytes()
        except (KeyError, TypeError, OSError) as exc:
            self.require(False, label + ': real downloaded file unavailable: ' + str(exc))
            self.missing.append(label + ' downloaded file')
            return None
        self.require(path.name == row.get('filename'), label + ': actual basename differs')
        self.require(raw == expected, label + ': entire downloaded bytes differ')
        self.require(sha(raw) == sha(expected), label + ': downloaded SHA differs')
        return {'path': row['path'], 'bytes': len(raw), 'sha256': sha(raw)}


def validate(base=HERE, evidence_path=None):
    base = Path(base)
    evidence_path = Path(evidence_path) if evidence_path else base / 'cloud_evidence.json'
    required = (base / 'cloud_fixture.json', base / 'cloud_forward_reference.json', evidence_path)
    absent = [str(path) for path in required if not path.exists()]
    if absent:
        return {'completed': False, 'passed': False, 'status': 'incomplete', 'missing_files': absent}
    check = Check()
    try:
        fixture = read(base / 'cloud_fixture.json')
        evidence = read(evidence_path)
        proof = read(base / 'cloud_forward_reference.json')
    except (ValueError, OSError) as exc:
        return {'completed': False, 'passed': False, 'status': 'failed', 'errors': [str(exc)]}
    check.require(sha((base / 'cloud_fixture.json').read_bytes()) == FIXTURE_SHA256,
                  'fixed release fixture SHA differs')
    check.require(sha((base / 'cloud_forward_reference.json').read_bytes())
                  == fixture['forward_reference_sha256'], 'actual forward reference SHA differs')
    forward_expected = {(r['language'], r['edition'], r['mode']): r for r in fixture['forward_cases']}
    inverse_expected = {(r['language'], r['edition']): r for r in fixture['inverse_cases']}
    csv_expected = {(r['language'], r['edition'], r['kind']): r for r in fixture['downloads']}
    fkeys = {(l, e, m) for l in (*LANGUAGES, 'KO') for e in EDITIONS for m in ('pure', 'kanji')}
    ikeys = {(l, e) for l in LANGUAGES for e in EDITIONS}
    ckeys = {(l, e, k) for l in LANGUAGES for e in EDITIONS for k in ('full', 'two_column', 'effective')}
    check.require(set(forward_expected) == fkeys and len(fixture['forward_cases']) == 12,
                  'fixture must contain twelve exact forward routes')
    check.require(set(inverse_expected) == ikeys and len(fixture['inverse_cases']) == 4,
                  'fixture must contain four inverse routes')
    check.require(set(csv_expected) == ckeys and len(fixture['downloads']) == 12,
                  'fixture must contain twelve dictionary downloads')
    reference = check.rows(proof.get('rows'), ('forward_language', 'edition', 'mode'), fkeys, 'local reference')
    for key, exp in forward_expected.items():
        row = reference.get(key, {})
        check.require(row.get('input') == exp['input'] and row.get('forward_output') == exp['expected_output']
                      and row.get('visible') == exp['expected_visible'], repr(key) + ': reference differs')
        check.require(row.get('restored') == {l: exp['expected_restored'] for l in LANGUAGES},
                      repr(key) + ': local forward proof did not restore original Esperanto')

    inverse = check.rows(evidence.get('inverse'), ('language', 'edition'), ikeys, 'inverse')
    hosts = {}
    verified_inverse = []
    for key, row in inverse.items():
        if key not in inverse_expected:
            continue
        exp = inverse_expected[key]; label = 'inverse ' + repr(key)
        host = check.observation(row, label)
        check.require(row.get('case_id') == exp['case_id'], label + ': case ID differs')
        check.require(row.get('input') == exp['input'], label + ': input differs')
        check.require(row.get('output') == exp['expected_output'], label + ': complete output differs')
        check.require(sha(exp['expected_output'].encode()) == exp['expected_output_sha256'], label + ': fixture output SHA differs')
        caption = PREFIX[key[0]] + exp['provenance']['label']
        check.require(isinstance(row.get('captions'), list) and row['captions'].count(caption) == 1,
                      label + ': actual result provenance caption missing or repeated')
        if key[0] in hosts:
            check.require(hosts[key[0]] == host, label + ': editions came from different hosts')
        hosts[key[0]] = host
        verified_inverse.append({'case_id': exp['case_id'], 'output_sha256': sha(exp['expected_output'].encode()),
                                 'caption': caption})

    forward = check.rows(evidence.get('forward'), ('language', 'edition', 'mode'), fkeys, 'forward')
    forward_hosts = {}; verified_forward = []
    for key, row in forward.items():
        if key not in forward_expected:
            continue
        exp = forward_expected[key]; label = 'forward ' + repr(key)
        host = check.observation(row, label)
        if key[0] in forward_hosts:
            check.require(forward_hosts[key[0]] == host, label + ': routes came from different hosts')
        forward_hosts[key[0]] = host
        check.require(row.get('case_id') == exp['case_id'], label + ': case ID differs')
        check.require(row.get('input') == exp['input'], label + ': input differs')
        check.require(row.get('visible') == exp['expected_visible'], label + ': visible base text differs')
        if key[2] == 'pure' and 'output' in row:
            check.require(row['output'] == exp['expected_output'], label + ': pure raw output differs')
        verified_forward.append({'case_id': exp['case_id'], 'visible_sha256': sha(exp['expected_visible'].encode()),
                                 'verification': 'observed visible base text; no raw HTML DOM equality claimed'})

    expected_files = {}
    for key, exp in csv_expected.items():
        try:
            raw = resolve(base, exp['expected_file']).read_bytes()
        except OSError:
            check.missing.append(exp['expected_file'])
            check.require(False, repr(key) + ': expected CSV unavailable')
            continue
        check.require(len(raw) == exp['expected_bytes'] and sha(raw) == exp['expected_sha256'],
                      repr(key) + ': expected CSV bytes/SHA differ')
        expected_files[key] = raw
    dkeys = ckeys | {(l, e, 'result') for l, e in ikeys}
    downloads = check.rows(evidence.get('downloads'), ('language', 'edition', 'kind'), dkeys, 'downloads')
    verified_downloads = []
    for key, row in downloads.items():
        if key not in dkeys:
            continue
        label = 'download ' + repr(key)
        host = check.observation(row, label)
        check.require(host == hosts.get(key[0]), label + ': inverse app host differs')
        check.require(isinstance(row.get('case_id'), str) and bool(row['case_id']), label + ': case ID absent')
        if key[2] == 'result':
            exp = inverse_expected[key[:2]]
            expected = exp['expected_output'].encode('utf-8')
            filename = exp['provenance']['result_filename']
        else:
            if key not in expected_files:
                continue
            expected = expected_files[key]
            filename = csv_expected[key]['expected_filename']
        check.require(filename_matches(row.get('filename'), filename), label + ': edition filename differs')
        observed = check.file(base, row, expected, label)
        if observed:
            verified_downloads.append({'language': key[0], 'edition': key[1], 'kind': key[2],
                                       'expected_filename': filename, **observed})

    gkeys = {(l, 'edition_switch') for l in LANGUAGES}
    guards = check.rows(evidence.get('guards'), ('language', 'kind'), gkeys, 'guards')
    verified_guards = []
    for key, row in guards.items():
        if key not in gkeys:
            continue
        exp = inverse_expected[(key[0], 'current')]; label = 'guard ' + repr(key)
        host = check.observation(row, label)
        check.require(host == hosts.get(key[0]), label + ': inverse app host differs')
        caption = PREFIX[key[0]] + exp['provenance']['label']
        check.require(row.get('from_edition') == 'current' and row.get('to_edition') == 'legacy',
                      label + ': direction differs')
        check.require(row.get('caption_before') == caption, label + ': initial result caption differs')
        check.require(row.get('caption_after_switch') == caption, label + ': generated-result caption was relabeled')
        check.require(row.get('output') == exp['expected_output'], label + ': generated result not retained')
        check.require(row.get('download_disabled') is True, label + ': old-result download must be unavailable')
        verified_guards.append({'language': key[0], 'kind': key[1], 'retained_caption': caption,
                                'download_disabled': row.get('download_disabled')})
    return {'completed': not check.missing, 'passed': not check.errors and not check.missing,
            'status': 'incomplete' if check.missing else ('failed' if check.errors else 'passed'),
            'fixture_sha256': FIXTURE_SHA256, 'evidence_sha256': sha(evidence_path.read_bytes()),
            'checks': check.count, 'errors': check.errors, 'missing': check.missing,
            'observed_counts': {'forward': len(forward), 'inverse': len(inverse), 'downloads': len(downloads), 'guards': len(guards)},
            'verified_forward': verified_forward, 'verified_inverse': verified_inverse,
            'verified_downloads': verified_downloads, 'verified_guards': verified_guards,
            'limits': ['Recorded observations and saved bytes are verified; this script does not itself operate the browser.',
                       'Forward validation checks visible base text, not browser-specific HTML wrapper serialization.',
                       'No Cloud custom-upload claim is made for this repair.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, default=HERE)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = validate(args.base, args.evidence)
    report = args.report or args.base / 'cloud_validation.json'
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if not k.startswith('verified_')}, ensure_ascii=True))
    raise SystemExit(0 if result['passed'] else 2)
