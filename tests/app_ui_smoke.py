"""Run actual Streamlit forms from the repository root (not a browser test).

Run from the repository root with: python -B -X utf8 tests/app_ui_smoke.py
Results contain repository-relative paths only. Each language runs in a fresh
process so that modules with the same names cannot leak between language apps.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
SOURCE = '@semajn@tagoj & %amiko% ŝakisto semajntagoj'
LANGUAGES = ('JA', 'ZH', 'KO')


def public_message(value):
    """Keep failures useful without exposing machine-specific absolute paths."""
    message = str(value)
    for path, replacement in ((ROOT, '<repo>'), (Path.home(), '<home>'),
                              (Path(sys.prefix), '<python>')):
        message = message.replace(str(path), replacement)
        message = message.replace(path.as_posix(), replacement)
    return re.sub(r'[A-Za-z]:[\\/][^\s\"\'<>]*', '<absolute-path>', message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_from_root(at, app):
    os.chdir(ROOT)
    assert Path.cwd() == ROOT, 'The AppTest must start from the repository root'
    at.run()
    if at.exception:
        raise AssertionError('; '.join(public_message(item.message) for item in at.exception))
    if at.error:
        raise AssertionError('; '.join(public_message(item.value) for item in at.error))
    assert Path.cwd() == app, 'The app did not resolve its own data directory'
    return at


def run_language(language):
    from streamlit.testing.v1 import AppTest

    app = ROOT / ('Esperanto-Kanji-Ruby-' + language)
    sys.path.insert(0, str(app))
    main = app / 'main.py'
    scripts = [main, *sorted((app / 'pages').glob('*.py'))]
    before = {path.relative_to(ROOT).as_posix(): sha256(path) for path in scripts}
    started = time.perf_counter()
    at = run_from_root(AppTest.from_file(str(main), default_timeout=120), app)
    modes = list(at.radio[0].options[:3])
    assert len(modes) == 3, 'Expected the three built-in conversion modes'
    results = []
    for index, mode in enumerate(modes):
        mode_started = time.perf_counter()
        at.radio[0].set_value(mode)
        run_from_root(at, app)
        at.text_area(key='text0_value').set_value(SOURCE)
        submit = next(button for button in at.button
                      if str(button.key).startswith('FormSubmitter:profile_form-'))
        submit.click()
        run_from_root(at, app)
        rendered = at.session_state['result_html']
        assert rendered and '@' not in rendered, 'The local marker was not removed'
        assert 'amiko' in rendered and '%amiko%' not in rendered, 'The skip marker contract failed'
        assert '&' in html.unescape(rendered), 'The ampersand was not preserved'
        if index == 2:
            assert rendered == '周日oj & amiko 棋家o 周日oj', 'Reviewed pure outputs differ'
            assert '<ruby' not in rendered and '<html' not in rendered, 'Pure mode emitted HTML'
        else:
            assert '<ruby' in rendered, 'Ruby mode emitted no ruby annotations'
        results.append({
            'language': language, 'mode': mode, 'source': SOURCE,
            'result_html': rendered, 'passed': True,
            'cwd_before_each_run': '.',
            'elapsed_seconds': round(time.perf_counter() - mode_started, 3),
        })

    pages = []
    for prefix, kind in (('1_', 'manual_correction'), ('2_', 'data_download')):
        matches = sorted((app / 'pages').glob(prefix + '*.py'))
        assert len(matches) == 1, 'Expected one page for ' + kind
        path = matches[0]
        page_started = time.perf_counter()
        page = run_from_root(AppTest.from_file(str(path), default_timeout=120), app)
        assert page.title, 'The subpage displayed no title'
        if kind == 'manual_correction':
            assert page.text_input and page.button, 'The correction controls did not appear'
        else:
            assert len(page.header) >= 3, 'The download sections did not appear'
            assert len(page.get('download_button')) >= 3, 'The local downloads did not appear'
        pages.append({
            'language': language, 'page': path.relative_to(ROOT).as_posix(),
            'kind': kind, 'title': page.title[0].value, 'passed': True,
            'cwd_before_run': '.', 'exception_count': len(page.exception),
            'error_count': len(page.error),
            'download_button_count': len(page.get('download_button')),
            'elapsed_seconds': round(time.perf_counter() - page_started, 3),
        })

    after = {path.relative_to(ROOT).as_posix(): sha256(path) for path in scripts}
    assert before == after, 'App/page source changed while the checks were running'
    return {'language': language, 'results': results, 'pages': pages,
            'script_sha256': after, 'script_bytes_unchanged_during_run': True,
            'elapsed_seconds': round(time.perf_counter() - started, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', choices=LANGUAGES)
    args = parser.parse_args()
    if args.language:
        try:
            result = run_language(args.language)
        except Exception as exc:
            print(json.dumps({'language': args.language, 'passed': False,
                              'error_type': type(exc).__name__,
                              'error': public_message(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(result, ensure_ascii=False))
        return 0

    os.chdir(ROOT)
    rows, pages, scripts, language_results = [], [], {}, []
    for language in LANGUAGES:
        child = subprocess.run(
            [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()),
             '--language', language], cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', timeout=600)
        if child.returncode:
            try:
                failure = json.loads(child.stdout)
            except (ValueError, TypeError):
                failure = {'error': 'AppTest worker failed; return code ' + str(child.returncode)}
            print(language + ': FAILED: ' + public_message(failure.get('error', failure)), flush=True)
            return 1
        result = json.loads(child.stdout)
        rows.extend(result['results'])
        pages.extend(result['pages'])
        scripts.update(result['script_sha256'])
        language_results.append({'language': language, 'passed': True,
                                 'elapsed_seconds': result['elapsed_seconds']})
        print(language + ': 3 actual forms and 2 subpages passed from repository root', flush=True)

    import pandas
    import streamlit
    output = {
        'method': 'Streamlit AppTest: actual main.py forms and both subpages',
        'limitations': [
            'AppTest is not a browser; visual layout and clipboard behavior were not tested.',
            'Subpages were checked for startup and controls, not full correction editing workflows.',
            'Remote download availability and Streamlit Cloud deployment were not tested.',
        ],
        'command': 'python -B -X utf8 tests/app_ui_smoke.py',
        'cwd': '.', 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'environment': {'python': platform.python_version(), 'system': platform.system(),
                        'streamlit': streamlit.__version__, 'pandas': pandas.__version__},
        'passed': True, 'conversion_routes': len(rows), 'subpage_routes': len(pages),
        'script_bytes_unchanged_during_run': True, 'script_sha256': scripts,
        'languages': language_results, 'results': rows, 'pages': pages,
    }
    Path(__file__).with_suffix('.json').write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved tests/app_ui_smoke.json (9 conversions, 6 subpages)', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
