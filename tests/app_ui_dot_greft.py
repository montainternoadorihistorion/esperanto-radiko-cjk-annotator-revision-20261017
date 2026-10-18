"""Actual Streamlit forms, navigation and independently specified accepted displays.

Run from the repository root: python -B -X utf8 tests/app_ui_dot_greft.py
This uses AppTest, not a browser. Cloud verification is recorded separately.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import app_ui_smoke as smoke

HERE = Path(__file__).resolve().parent
SOURCE = smoke.SPERM_DISTINCTION_SOURCE + ' grefti @greft@i greftoj @greft@oj korgrefto doto @dot@o dotita naturdotita tualeto @tualet@o ŝminko @ŝmink@o kosmetiko @kosmetik@o transplanti'
EXPECTED = smoke.SPERM_DISTINCTION_EXPECTED + ' 移植i 移植i 移植oj 移植oj 心移植o 妆o 妆o 妆受a 然妆受a 妆ᵀo 妆ᵀo 妆ˢ̂o 妆ˢ̂o 妆ᴷo 妆ᴷo 越植i'


def plain(value):
    return html.unescape(re.sub(r'<[^>]*>', '', value)).replace('\u00a0', ' ')


def run_language(language):
    smoke.SOURCE, smoke.EXPECTED = SOURCE, EXPECTED
    report = smoke.run_language(language)
    annotation, kanji, pure = report['results']
    pairs = [(plain(root).lower(), plain(gloss)) for root, gloss in
             re.findall(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', annotation['result_html'], re.S)]
    generic = {
        'JA': {'dot': ('婚姻財産', '資質'), 'greft': ('接ぎ木', '組織', '器官')},
        'ZH': {'dot': ('婚姻财产', '资质'), 'greft': ('嫁接', '组织', '器官')},
        'KO': {'dot': ('혼인 재산', '자질'), 'greft': ('접목', '조직', '기관')},
    }
    for root, tokens in generic[language].items():
        matching = [gloss for spelling, gloss in pairs if spelling == root]
        generic_count = 3 if root == 'dot' else 4
        assert len(matching) == generic_count + 1, (language, root, matching)
        assert all(all(token in gloss for token in tokens)
                   for gloss in matching[:generic_count]), (language, root, matching)
    # The contextual nature/endowment example must not lose its figurative sense.
    roots = [root for root, _ in pairs]
    nature = roots.index('natur')
    assert roots[nature + 1] == 'dot'
    assert {'JA': '資質', 'ZH': '资质', 'KO': '자질'}[language] in pairs[nature + 1][1]
    # Restore every ruby to the unchanged source spelling, including older fixes.
    expected_source = SOURCE.replace('@', '').replace('%', '')
    for row, original_group in ((annotation, 1), (kanji, 2)):
        body = re.fullmatch(r'.*?<p class="text-M_M">\n(.*?)</p></body></html>',
                            row['result_html'], re.S)
        assert body, 'Expected the app-generated HTML body wrapper'
        restored = re.sub(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',
                          lambda match: plain(match[original_group]), body[1], flags=re.S)
        assert plain(restored) == expected_source, (language, row['mode'])
    report['reviewed_semantics_passed'] = True
    report['ruby_source_spelling_preserved'] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=smoke.LANGUAGES)
    args = parser.parse_args()
    if args.language:
        print(json.dumps(run_language(args.language), ensure_ascii=False))
        return
    started = time.monotonic()
    cases = []
    for language in smoke.LANGUAGES:
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()),
                                 '--language', language], cwd=smoke.ROOT,
                                encoding='utf-8', capture_output=True)
        if result.returncode:
            raise RuntimeError(smoke.public_message(result.stdout + result.stderr))
        cases.append(json.loads(result.stdout))
        print(language, 'PASS', flush=True)
    report = {
        'passed': True, 'method': 'Streamlit AppTest, fresh process for each language',
        'conversion_routes': 9, 'subpage_routes': 6, 'return_to_main_routes': 6,
        'seconds': round(time.monotonic() - started, 3), 'source': SOURCE, 'expected': EXPECTED,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'results': cases,
    }
    (HERE / 'app_ui_dot_greft.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS: 9 conversion routes, 6 subpages, 6 returns; meaning and spelling checks')


if __name__ == '__main__':
    main()
