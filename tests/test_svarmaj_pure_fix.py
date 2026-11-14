"""Six whole-word pure forms match established svarm ruby/local semantics."""
from pathlib import Path
import gc
import gzip
import hashlib
import html
import importlib.util
import json
import logging
import os
import re
import sys
import tempfile
import unittest

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
WORDS = {'svarmaj': 'aj', 'Svarmaj': 'aj', 'SVARMAJ': 'AJ',
         'svarmajn': 'ajn', 'Svarmajn': 'ajn', 'SVARMAJN': 'AJN'}
GLYPHS = {'current': '群ˢ', 'legacy': '拥'}
FORMATS = {'pure': '替换后文字列のみ(仅)保留(简单替换)',
           'kanji': 'HTML格式_Ruby文字_大小调整_汉字替换',
           'ruby': 'HTML格式_Ruby文字_大小调整'}
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
REPORT = []


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def strip(value):
    return re.sub('</?ruby>', '', re.sub('<rt[^>]*>.*?</rt>', '', value, flags=re.S))


def plain(value):
    return html.unescape(re.sub('<[^>]*>', '', value)).replace('\xa0', ' ')


def visible(value):
    return plain(strip(value))


def inverse_dir(lang):
    public = ROOT / ('Esperanto-Reverter-' + lang)
    return public if public.exists() else ROOT.parent / {
        'JA': 'kanjized-esperanto-reverter',
        'ZH': 'hanzized-esperanto-reverter-zh_更新版20260822'}[lang]


class SvarmajPureFixTests(unittest.TestCase):
    def test_scope_guards_rule_order_and_custom_paths(self):
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT / ('Esperanto-Kanji-Ruby-' + lang)
            ed = load(app / 'esp_assignment_edition.py', 'svarmaj_scope_' + lang)
            local = [['svarm', 'A', '@1@'], ['Svarm', 'B', '@2@'], ['SVARM', 'C', '@3@']]
            base = [['abelsvarmaj', 'LONG', '$3$'], ['varmaj', 'WARM', '$1$'],
                    ['svarm', 'SHORT', '$2$']]
            result = ed._with_svarmaj_reviewed_pure_corrections(base, local)
            additions = [row for row in result if row not in base]
            self.assertEqual(len(additions), 6)
            self.assertEqual({row[0] for row in additions}, {' ' + word + ' ' for word in WORDS})
            self.assertEqual([row for row in result if row in base], base)
            self.assertLess(result.index(base[0]), next(i for i, row in enumerate(result) if row[0] == ' svarmaj '))
            self.assertLess(next(i for i, row in enumerate(result) if row[0] == ' svarmaj '), result.index(base[1]))
            self.assertEqual({row[0].strip(): row[1] for row in additions}, {
                'svarmaj': ' Aaj ', 'Svarmaj': ' Baj ', 'SVARMAJ': ' CAJ ',
                'svarmajn': ' Aajn ', 'Svarmajn': ' Bajn ', 'SVARMAJN': ' CAJN '})
            self.assertEqual(base, [['abelsvarmaj', 'LONG', '$3$'], ['varmaj', 'WARM', '$1$'], ['svarm', 'SHORT', '$2$']])
            for bad in (local[:-1], local + [['svarm', 'CONFLICT', '@4@']],
                        [['svarm', '', '@1@'], *local[1:]]):
                with self.assertRaises(ValueError):
                    ed._with_svarmaj_reviewed_pure_corrections(base, bad)
            for rules, atoms in ((base + [['other', 'X', '$9140000$']], local),
                                 (base, local + [['other', 'X', '$9140005$']])):
                with self.assertRaisesRegex(ValueError, 'already in use'):
                    ed._with_svarmaj_reviewed_pure_corrections(rules, atoms)
            payload = {ed.GLOBAL: base, ed.LOCAL: local, ed.TWO: []}
            with tempfile.TemporaryDirectory() as temp:
                for name in ('置換リスト_漢字_純粋置換.json', 'pure.json.gz'):
                    path = Path(temp) / name
                    raw = json.dumps(payload, ensure_ascii=False).encode()
                    path.write_bytes(gzip.compress(raw) if name.endswith('.gz') else raw)
                    self.assertFalse(ed._is_bundled_pure_path(path))
                    self.assertEqual(ed.load_lists_path(path), (base, local, []))
                    ed._load_lists_cached.clear()

    def test_actual_all_languages_editions_modes_and_inverse(self):
        inverses = {}
        for lang in ('JA', 'ZH'):
            inv = load(inverse_dir(lang) / ('esperanto_converter.py' if lang == 'JA' else 'esperanto_converter_zh.py'), 'svarmaj_inverse_' + lang)
            inverses[lang] = (inv, {edition: inv.build_mapping_index_cached(inv.effective_mapping_records(
                source, inv.load_dictionary_source(source))) for edition, source in
                [('current', 'pejvo-piv-20260620'), ('legacy', 'pre-las-20261017')]})
        recovery = load(inverse_dir('JA') / 'html_source_recovery.py', 'svarmaj_html_recovery')
        controls = ['varmaj', 'Varmaj', 'VARMAJ', 'svarma', 'svarman', 'svarmo', 'svarmi',
                    'svarmas', 'svarmado', 'abelsvarmaj', 'varsvarmaj', 'svarmajo',
                    'svarmaĵo', 'svarmajx', 'xsvarmaj', 'sVaRmAj', 'ĉsvarmaj',
                    'svarmajĉ', '2svarmaj', 'svarmaj2',
                    "svarmaj'", "svarmajn'", '@svarmaj@', '@Svarmaj@', '@SVARMAJ@',
                    '@svarmajn@', '@Svarmajn@', '@SVARMAJN@', '@svarm@aj',
                    '@Svarm@aj', '@SVARM@AJ', '@svarm@ajn', '@Svarm@ajn', '@SVARM@AJN',
                    '@svarmaj kaj varmaj@', '%svarmaj%', '%Svarmajn%',
                    '%@svarmaj@%', '%s暖aj%', '%群ˢaj%', 'sene', 'kseno', 'greganta',
                    'preganta', 'kordonita', '@ĉareton@', '@domon@', '@stalagmito@',
                    '@semajno@', 'triumfo', 'ananaso', 'prioritato', 'testikito', 'orkidito']
        cases = list(WORDS) + controls
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT / ('Esperanto-Kanji-Ruby-' + lang)
            data = app / 'app_data'
            sys.path.insert(0, str(app))
            rt = load(app / 'esp_text_replacement_module.py', 'svarmaj_runtime_' + lang)
            ed = load(app / 'esp_assignment_edition.py', 'svarmaj_edition_' + lang)
            ov = load(app / 'esp_overlay_module.py', 'svarmaj_overlay_' + lang)
            for edition in ('current', 'legacy'):
                snapshots = {}
                for mode, fmt in FORMATS.items():
                    path = ed.resolve_path(data, mode, edition)
                    before_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                    gg, gl, g2 = ed.load_lists(data, mode, edition)
                    # Removing only the new six boundary rules reconstructs the
                    # previous bundled loader. All existing rules must remain.
                    baseline = [row for row in gg if row[2].strip() not in {
                        '$' + str(9140000 + i) + '$' for i in range(6)}]
                    self.assertEqual(len(gg) - len(baseline), 6 if mode == 'pure' else 0)
                    om = 'kanji' if mode == 'pure' else mode
                    user = ov.load_overlay_entries(str(data), om, edition)
                    if mode == 'pure': user = [[old, strip(new), token] for old, new, token in user]
                    after_rules, old_rules = ov.merge_overlay(gg, user), ov.merge_overlay(baseline, user)

                    def run(text, rules):
                        value = rt.orchestrate_comprehensive_esperanto_text_replacement(
                            text, [], gl, [], rules, g2, fmt, reviewed_local_decompositions=True)
                        auto = ov.auto_overlay_entries(value, str(data), om, edition)
                        if mode == 'pure': auto = [[old, strip(new), token] for old, new, token in auto]
                        if auto:
                            value = rt.orchestrate_comprehensive_esperanto_text_replacement(
                                text, [], gl, [], ov.merge_overlay(rules, auto), g2, fmt,
                                reviewed_local_decompositions=True)
                        return value

                    # Per-input automatic corrections must not leak from the
                    # reviewed words into unrelated controls in a batch.
                    def batch(rules):
                        result = rt.orchestrate_comprehensive_esperanto_text_replacement(
                            ' ◆ '.join(cases), [], gl, [], rules, g2, fmt,
                            reviewed_local_decompositions=True)
                        parts = [part.strip() for part in result.split('◆')]
                        self.assertEqual(len(parts), len(cases))
                        outputs = dict(zip(cases, parts))
                        groups = {}
                        for word, value in outputs.items():
                            auto = ov.auto_overlay_entries(value, str(data), om, edition)
                            if mode == 'pure': auto = [[old, strip(new), token] for old, new, token in auto]
                            if auto: groups.setdefault(json.dumps(auto, ensure_ascii=False), []).append(word)
                        for encoded, words in groups.items():
                            rerendered = rt.orchestrate_comprehensive_esperanto_text_replacement(
                                ' ◆ '.join(words), [], gl, [], ov.merge_overlay(rules, json.loads(encoded)),
                                g2, fmt, reviewed_local_decompositions=True)
                            pieces = [part.strip() for part in rerendered.split('◆')]
                            self.assertEqual(len(words), len(pieces))
                            outputs.update(zip(words, pieces))
                        return outputs

                    output, old_output = batch(after_rules), batch(old_rules)
                    for word in controls:
                        self.assertEqual(output[word], old_output[word], (lang, edition, mode, word))
                    if mode == 'pure':
                        for word, ending in WORDS.items():
                            expected = GLYPHS[edition] + ending
                            self.assertEqual(output[word], expected, (lang, edition, word))
                            self.assertNotEqual(output[word], old_output[word])
                            for inv, indexes in inverses.values():
                                # Plain inverse normalizes case; the existing
                                # equivalent @ output has the same limitation.
                                self.assertEqual(inv.convert_kanji_esperanto_to_alphabet(expected, indexes[edition]), word.lower())
                        for text, expected in [('svarmaj, (Svarmajn)!', GLYPHS[edition] + 'aj, (' + GLYPHS[edition] + 'ajn)!'),
                                               ('svarmaj-svarmajn', GLYPHS[edition] + 'aj-' + GLYPHS[edition] + 'ajn'),
                                               ('_svarmaj_', '_' + GLYPHS[edition] + 'aj_'),
                                               ('  svarmaj\tSvarmajn\nSVARMAJ  ', '  ' + GLYPHS[edition] + 'aj\t' + GLYPHS[edition] + 'ajn\n' + GLYPHS[edition] + 'AJ  ')]:
                            self.assertEqual(run(text, after_rules), expected)
                        override = ov.merge_overlay(after_rules, [['svarmaj', 'USER', '$9000000$']])
                        self.assertEqual(run('svarmaj', override), 'USER')
                        self.assertEqual(run('%svarmaj%', override), 'svarmaj')
                    else:
                        self.assertEqual(output, old_output)
                        for word in WORDS:
                            document = rt.apply_ruby_html_header_and_footer(output[word], fmt)
                            self.assertEqual(recovery.recover_standard_html(document, 'kanji' if mode == 'kanji' else 'annotation')['text'], word)
                    snapshots[mode] = output
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before_hash)
                    REPORT.append({'language': lang, 'edition': edition, 'mode': mode,
                                   'single_inputs': len(cases), 'controls_unchanged': len(controls),
                                   'raw_data_unchanged': True})
                    print('svarmaj', lang, edition, mode, 'PASS', flush=True)
                    ed._load_lists_cached.clear()
                    del gg, gl, g2, baseline, after_rules, old_rules
                    gc.collect()
                for word in WORDS:
                    explicit_root = '@' + word[:5] + '@' + WORDS[word]
                    self.assertEqual(snapshots['pure'][word], visible(snapshots['kanji'][explicit_root]),
                                     (lang, edition, word, 'existing explicit-root kanji-ruby equivalence'))
                    # The existing ordinary kanji route also renders ajn as
                    # the independent ajn root. That separate issue is retained.
                    if word == 'svarmaj':
                        self.assertEqual(snapshots['pure'][word], visible(snapshots['kanji'][word]),
                                         (lang, edition, word, 'existing normal kanji-ruby equivalence'))
            sys.path.pop(0)
        if os.environ.get('SVARMAJ_REPORT'):
            Path(os.environ['SVARMAJ_REPORT']).write_text(json.dumps({'passed': True, 'rows': REPORT}, ensure_ascii=False, indent=2), 'utf-8')


if __name__ == '__main__':
    unittest.main()
