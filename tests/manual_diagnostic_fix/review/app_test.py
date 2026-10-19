"""Independent actual Streamlit diagnostics/iframe comparison with main.py.

Each language runs in a fresh process. No production function is mocked.
The page and main AppTest sessions share only an explicitly copied session
correction, as real page navigation does. Disk corrections are hash-guarded.
"""
from pathlib import Path
from html.parser import HTMLParser
import argparse, hashlib, json, logging, os, re, sys, time

ROOT = Path(__file__).resolve().parents[3]
WORDS = ('greganta', 'preganta', 'kordonita', '@greganta@', '@preganta@',
         '@kordonita@', 'semajno', 'kseno', 'sene', 'testikito', 'orkidita')
URLS = [f'https://esperanto-cjk-revision-{lang}-20261017.streamlit.app/'
        for lang in ('ja', 'zh', 'ko')]


class VisibleSegments(HTMLParser):
    """Read visible ruby bases and bare Latin runs, independently of page regex."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.body = self.ruby = self.rt = False
        self.base = self.bare = ''
        self.tokens = []

    def flush(self):
        self.tokens.extend(re.findall('[a-zĉĝĥĵŝŭ]+', self.bare, re.I))
        self.bare = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'body': self.body = True
        if not self.body: return
        if tag == 'ruby':
            self.flush(); self.ruby = True; self.base = ''
        elif tag == 'rt': self.rt = True

    def handle_endtag(self, tag):
        if tag == 'rt': self.rt = False
        elif tag == 'ruby':
            self.tokens.append(self.base); self.ruby = False
        elif tag == 'body': self.flush(); self.body = False

    def handle_data(self, data):
        if not self.body or self.rt: return
        if self.ruby: self.base += data
        else: self.bare += data


def segmentation(doc):
    parser = VisibleSegments(); parser.feed(doc)
    return '/'.join(parser.tokens)


def check(language, report):
    started = time.monotonic()
    logging.disable(logging.WARNING)
    from streamlit.testing.v1 import AppTest
    app = ROOT / f'Esperanto-Kanji-Ruby-{language}'
    sys.path.insert(0, str(app)); os.chdir(ROOT)
    corrections = app / 'app_data/user_corrections.json'
    before = corrections.read_bytes()
    main = AppTest.from_file(app / 'main.py', default_timeout=180)

    def run(at):
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        assert not at.error, [e.value for e in at.error]

    run(main)
    footer = next(m.value for m in main.markdown if all(url in m.value for url in URLS))
    assert not re.search('https://esperanto-radiko-cjk-annotator(?:-zh|-ko)?[.]streamlit[.]app', footer)
    page = AppTest.from_file(next((app / 'pages').glob('1_*.py')), default_timeout=180)
    run(page)
    rows = []; guards = []

    def main_expected(word, edition, session):
        main.session_state['user_corrections_session'] = session
        main.selectbox(key='_assignment_edition_widget').set_value(edition); run(main)
        docs = []
        for mode in (0, 1):
            opts = main.radio(key='_conversion_mode_widget').options
            main.radio(key='_conversion_mode_widget').set_value(opts[mode]); run(main)
            main.text_area(key='text0_value').set_value(' ' + word + ' ')
            main.button(key='convert_text').click(); run(main)
            docs.append(main.session_state['result_html'])
        return docs

    def probe(word, edition, session, context):
        expected = main_expected(word, edition, session)
        page.text_input(key='word_probe').set_value(word)
        page.button[0].click(); run(page)
        docs = [frame.proto.srcdoc for frame in page.get('iframe')]
        assert len(docs) == 2, (language, edition, word, len(docs))
        assert docs == expected, (language, edition, word, 'iframe srcdoc differs from actual main')
        diag = [m.value for m in page.markdown
                if re.fullmatch(r'\*\*[^\n]+\*\*: `[^\n]*`', m.value)]
        assert len(diag) == 2, (language, edition, word, diag)
        decomps = [re.search(r'`([^`]*)`$', item).group(1) for item in diag]
        assert decomps == [segmentation(doc) for doc in docs], (word, decomps)
        assert page.session_state['probe_ruby'] == decomps[0]
        rows.append({'edition': edition, 'word': word, 'context': context,
                     'diagnostics': decomps, 'iframe_equals_main': [True, True],
                     'main_html_sha256': [hashlib.sha256(doc.encode()).hexdigest() for doc in expected],
                     'preview_html': docs})
        print(language, edition, context, word, 'PASS', flush=True)

    for edition in ('current', 'legacy'):
        page.session_state['user_corrections_session'] = []
        page.selectbox(key='_assignment_edition_widget').set_value(edition); run(page)
        # Existing user-entered correction draft must not be overwritten by a probe.
        page.text_input(key='decomp_in').set_value('sem/ajn/o'); run(page)
        for word in WORDS:
            probe(word, edition, [], 'baseline')
            assert page.text_input(key='decomp_in').value == 'sem/ajn/o'
            guards.append(edition + '/' + word + ': existing draft retained')

        # Exercise the actual save button, then mirror its session state into
        # main's independent test session. This choice intentionally differs
        # from the automatic greg/ant/a split without touching stored data.
        page.text_input(key='decomp_in').set_value('gre/gant/a'); run(page)
        next(b for b in page.button if b.label.startswith('✅')).click(); run(page)
        session = [dict(c) for c in page.session_state['user_corrections_session']]
        assert any(c.get('decomp') == 'gre/gant/a' for c in session)
        for word in ('greganta', '@greganta@'):
            probe(word, edition, session, 'session_override')
        assert rows[-2]['diagnostics'][0] == 'gre/gant/a'
        assert rows[-1]['diagnostics'][0] == 'greg/ant/a'
        guards.append(edition + ': saved session correction remains effective only in global path')

    assert corrections.read_bytes() == before
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({'passed': True, 'language': language, 'rows': rows,
       'main_conversions': len(rows) * 2, 'preview_comparisons': len(rows) * 2,
       'diagnostic_comparisons': len(rows) * 2, 'guards': guards,
       'footer_urls': URLS, 'corrections_disk_unchanged': True,
       'elapsed_seconds': round(time.monotonic() - started, 3),
       'method': 'Actual main and manual-page AppTest controls; compare final main result to actual iframe srcdoc and displayed diagnostic markdown. No production functions mocked; no Cloud claim.'},
       ensure_ascii=False, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--language', required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args(); check(args.language, args.report)
