"""Verify captured Chrome DOM output against the locally tested application.

This script does not operate a browser. mirror_cloud_capture.json is recorded
separately through Codex's connected Chrome browser after deployment.
"""
from pathlib import Path
import argparse
import html
import json
import re

HERE = Path(__file__).resolve().parent

def plain(value):
    return html.unescape(re.sub(r'<[^>]*>', '', value)).replace('\xa0', ' ').strip()

def visible(value):
    return plain(re.sub(r'<rt[^>]*>.*?</rt>', '', value, flags=re.S))

def original(value, mode):
    value = re.sub(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',
                   lambda match: match[2] if mode == 'kanji' else match[1], value, flags=re.S)
    return plain(value)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    expected = json.loads((HERE / 'mirror_cloud_expected.json').read_text(encoding='utf-8'))
    captured = json.loads((HERE / 'mirror_cloud_capture.json').read_text(encoding='utf-8'))
    assert len(captured['cases']) == len(expected['cases']) == 9
    lookup = {(row['language'], row['mode']): row for row in expected['cases']}
    results = []
    for row in captured['cases']:
        reference = lookup.pop((row['language'], row['mode']))
        assert row['input'] == expected['input']
        if row['mode'] == 'pure':
            text = row['output'].strip()
            assert text == reference['output'].strip(), (row['language'], 'pure output')
            assert text == reference['visible'].strip()
            restored = None
        else:
            match = re.search(r'<body[^>]*>(.*?)</body>', row['srcdoc'], flags=re.S | re.I)
            assert match, 'Preview HTML body missing'
            body = match[1].strip()
            assert reference['output'] in body, (row['language'], row['mode'], 'HTML differs')
            text = visible(body)
            assert text == reference['visible'].strip(), (row['language'], row['mode'], 'visible text')
            restored = original(body, row['mode'])
            assert restored == reference['restored_text'].strip(), (row['language'], row['mode'], 'source reconstruction')
        results.append({'language': row['language'], 'mode': row['mode'], 'url': row['url'],
                        'visible': text, 'restored_text': restored, 'passed': True})
    assert not lookup
    report = {'method': 'Actual connected Chrome UI operation; captured preview HTML or output textarea compared with local runtime fixture',
              'source_commit_on_main': args.commit, 'browser_profile': captured['browser_profile'],
              'captured_at': captured['captured_at'], 'cases': results,
              'passed': True,
              'limitations': 'Annotation results are preserved, not semantically reapproved. Pre-existing localized annotation splits, including medical it and metapsiki, remain. Pure text contains no source ruby; its exact output is compared here, and reversal is verified independently with the actual reverter.'}
    (HERE / 'mirror_cloud_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(results), 'passed': True}, ensure_ascii=False))

if __name__ == '__main__':
    main()
