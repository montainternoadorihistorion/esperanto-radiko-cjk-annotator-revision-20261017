"""Four approved exact @ payloads keep endings literal, with no family expansion."""
from pathlib import Path
import functools
import gc
import hashlib
import html
import importlib.util
import json
import logging
import os
import re
import sys
import unittest

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
BEFORE_ROOT = (Path(os.environ['FOUR_LOCAL_ENDINGS_BEFORE_ROOT'])
               if os.environ.get('FOUR_LOCAL_ENDINGS_BEFORE_ROOT') else None)
REPORT = []
# Independent linguistic expectations, not read from the runtime allowlist.
CASES = {'domon': ('dom', 'on', '屋'), 'belajn': ('bel', 'ajn', '美'),
         'homojn': ('hom', 'ojn', '人'), 'diris': ('dir', 'is', '说')}
GLOSSES = {'JA': {'dom': '家', 'bel': '美しい', 'hom': '人', 'dir': '(を)言う'},
           'ZH': {'dom': '房屋', 'bel': '美丽', 'hom': '人', 'dir': '说'},
           'KO': {'dom': '집', 'bel': '아름다운', 'hom': '사람', 'dir': '말하다'}}
FORMATS = {'pure': '替换后文字列のみ(仅)保留(简单替换)',
           'kanji': 'HTML格式_Ruby文字_大小调整_汉字替换',
           'ruby': 'HTML格式_Ruby文字_大小调整'}
CONTROLS = ['@on@', '@ajn@', '@homo@', '@iris@', '@balon@', '@Katono@',
            '@iu ajn@', '@duono@', '@monon@', '@katon@', '@min@', '@vidis@',
            '@diras@', '@diris kaj domon@', '@DOMON@', '@Diris@']
RUBY = re.compile(r'<ruby\b[^>]*>(.*?)<rt\b[^>]*>(.*?)</rt\s*>\s*</ruby\s*>', re.I | re.S)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def plain(value):
    return html.unescape(re.sub(r'<[^>]*>', '', value)).replace('\xa0', ' ')


def source(value, mode):
    return plain(RUBY.sub(lambda m: m[2] if mode == 'kanji' else m[1], value))


def visible(value):
    return plain(RUBY.sub(lambda m: m[1], value))


def inputs():
    result = []
    for word in CASES:
        result.extend([('@' + word + '@', 'target'), (word, 'normal'),
                       ('%' + word + '%', 'protected'), ('%@' + word + '@%', 'protected_at'),
                       ('@' + word.capitalize() + '@', 'control'),
                       ('@' + word.upper() + '@', 'control'),
                       ('@ ' + word + ' @', 'control'), ('@' + word + '!@', 'control'),
                       ('@x' + word + '@', 'control'), ('@' + word + 'x@', 'control'),
                       ('@' + word + ' kaj test@', 'control'),
                       ('x' + word + 'y', 'control')])
    result.extend((word, 'control') for word in CONTROLS)
    return result


class FourLocalEndingTests(unittest.TestCase):
    def test_exact_scope_custom_manual_preview_and_missing_atoms(self):
        # Deliberately conflicting local atoms model the real suffix/root collisions.
        atoms = [('iris', 'IRIS'), ('homo', 'HOMO'), ('balon', 'BALON'),
                 ('dom', 'DOM'), ('bel', 'BEL'), ('hom', 'HOM'), ('dir', 'DIR'),
                 ('on', 'ON'), ('ajn', 'AJN')]
        local = [(old, new, '@' + str(1800 + i) + '@') for i, (old, new) in enumerate(atoms)]
        ordinary = [(word, 'NORMAL' + str(i), '$' + str(8100 + i) + '$')
                    for i, word in enumerate(CASES)]
        fallback = {'domon': 'DOMON', 'belajn': 'BELAJN', 'homojn': 'HOMOjn', 'diris': 'dIRIS'}
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT / ('Esperanto-Kanji-Ruby-' + lang)
            rt = load(app / 'esp_text_replacement_module.py', 'four_scope_' + lang)
            ov = load(app / 'esp_overlay_module.py', 'four_overlay_scope_' + lang)
            for fmt in FORMATS.values():
                def render(text, enabled=True, rules=ordinary, local_rules=local):
                    return rt.orchestrate_comprehensive_esperanto_text_replacement(
                        text, [], local_rules, [], rules, [], fmt,
                        reviewed_local_decompositions=enabled)
                for i, (word, (root, ending, _)) in enumerate(CASES.items()):
                    expected = root.upper() + ending
                    self.assertEqual(render('@' + word + '@'), expected)
                    self.assertEqual(render(word), 'NORMAL' + str(i))
                    self.assertEqual(render(word + ' @' + word + '@'), 'NORMAL' + str(i) + ' ' + expected)
                    self.assertEqual(render('@' + word + '@', enabled=False), fallback[word])
                    self.assertEqual(render('%' + word + '%'), word)
                    self.assertEqual(render('%@' + word + '@%'), '@' + word + '@')
                    preview = rt.create_replacements_list_for_localized_replacement(
                        '@' + word + '@', ['@999@'], local, ordinary,
                        reviewed_local_decompositions=True)
                    self.assertEqual(preview[0][2], expected)
                    manual = ov.merge_overlay(ordinary, [[word, 'USER', '$9000000$']])
                    self.assertEqual(render('@' + word + '@', rules=manual), 'USER')
                    self.assertEqual(render(word, rules=manual), 'USER')
                    self.assertEqual(render('%@' + word + '@%', rules=manual), '@' + word + '@')
                    manual_preview = rt.create_replacements_list_for_localized_replacement(
                        '@' + word + '@', ['@999@'], local, manual,
                        reviewed_local_decompositions=True)
                    self.assertEqual(manual_preview[0][2], 'USER')
                    # Auto-generated $911NNNN$ fallbacks must not undo these four repairs.
                    automatic = [(word, 'AUTO_FALLBACK', '$9110000$')]
                    self.assertEqual(render('@' + word + '@', rules=automatic), expected)
                    self.assertEqual(render(word, rules=automatic), 'AUTO_FALLBACK')
                    combined = automatic + [(word, 'USER', '$9000000$')]
                    self.assertEqual(render('@' + word + '@', rules=combined), 'USER')
                    self.assertEqual(render('%@' + word + '@%', rules=combined), '@' + word + '@')
                # The automatic-override rule for previously approved words is unchanged.
                self.assertEqual(render('@metron@', rules=[('metron', 'AUTO', '$9110099$')]), 'AUTO')
                # These are not the four exact lowercase payloads.
                for payload in (' domon ', 'domon!', 'xdomon', 'domonx', 'domon kaj belajn',
                                'Domon', 'DOMON', 'Diris', 'diras', 'on', 'ajn', 'homo', 'iris', 'balon'):
                    self.assertEqual(render('@' + payload + '@'),
                                     render('@' + payload + '@', enabled=False), (lang, fmt, payload))
                self.assertEqual(render('@on@ @ajn@ @homo@ @iris@ @balon@'), 'ON AJN HOMO IRIS BALON')
                missing = [row for row in local if row[0] != 'dir']
                with self.assertRaisesRegex(ValueError, 'Missing reviewed corpus atoms'):
                    render('@diris@', local_rules=missing)
                # Uploaded/custom data never starts using the bundled exact fixes.
                self.assertEqual(render('@diris@', enabled=False, local_rules=missing), 'dIRIS')

    def test_bundled_all_editions_formats_and_roundtrips(self):
        inv = load(ROOT / 'Esperanto-Reverter-JA/esperanto_converter.py', 'four_inverse')
        recovery = load(ROOT / 'Esperanto-Reverter-JA/html_source_recovery.py', 'four_recovery')
        indexes = {edition: inv.build_mapping_index_cached(inv.effective_mapping_records(
            key, inv.load_dictionary_source(key))) for edition, key in
            [('current', 'pejvo-piv-20260620'), ('legacy', 'pre-las-20261017')]}
        cases = inputs()
        joined = ' ◆ '.join(text for text, kind in cases)
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT / ('Esperanto-Kanji-Ruby-' + lang)
            data = app / 'app_data'
            sys.path.insert(0, str(app))
            rt = load(app / 'esp_text_replacement_module.py', 'four_real_' + lang)
            ed = load(app / 'esp_assignment_edition.py', 'four_edition_' + lang)
            ov = load(app / 'esp_overlay_module.py', 'four_overlay_' + lang)
            before = (load(BEFORE_ROOT / ('Esperanto-Kanji-Ruby-' + lang) /
                           'esp_text_replacement_module.py', 'four_before_' + lang)
                      if BEFORE_ROOT else None)
            original_hash = hashlib.sha256((app / 'esp_text_replacement_module.py').read_bytes()).hexdigest()
            for edition in ('current', 'legacy'):
                for mode, fmt in FORMATS.items():
                    gg, gl, g2 = ed.load_lists(data, mode, edition)
                    gg = ov.merge_overlay(gg, ov.load_overlay_entries(str(data), mode, edition))
                    self.assertTrue(ed.supports_reviewed_local_decompositions(ed.resolve_path(data, mode, edition)))
                    def batch(engine, enabled):
                        fn = functools.partial(engine.orchestrate_comprehensive_esperanto_text_replacement,
                                               reviewed_local_decompositions=enabled)
                        output = ov.autofix_render(joined, [], gl, [], gg, g2, fmt,
                                                   str(data), mode, fn, edition)
                        parts = [part.strip() for part in output.split('◆')]
                        self.assertEqual(len(parts), len(cases))
                        return parts
                    after = batch(rt, True)
                    # Also test an ordinary mixed input without adversarial uppercase controls.
                    ordinary_input = ' '.join(word + ' @' + word + '@' for word in CASES)
                    ordinary_fn = functools.partial(rt.orchestrate_comprehensive_esperanto_text_replacement,
                                                    reviewed_local_decompositions=True)
                    ordinary_output = ov.autofix_render(ordinary_input, [], gl, [], gg, g2, fmt,
                                                        str(data), mode, ordinary_fn, edition)
                    if mode == 'pure':
                        self.assertEqual(ordinary_output, ' '.join((kanji + ending + ' ' + kanji + ending)
                                         for root, ending, kanji in CASES.values()))
                    else:
                        self.assertEqual(source(ordinary_output, mode), ordinary_input.replace('@', ''))
                        ordinary_pairs = [(plain(m[1]), plain(m[2])) for m in RUBY.finditer(ordinary_output)]
                        if mode == 'kanji':
                            self.assertEqual(len(ordinary_pairs), 8)
                        else:
                            # Ordinary diris already annotates the past ending; preserve it.
                            self.assertEqual([base for base, gloss in ordinary_pairs],
                                             ['dom', 'dom', 'bel', 'bel', 'hom', 'hom', 'dir', 'is', 'dir'])
                            self.assertEqual(ordinary_pairs[7][1],
                                             {'JA': '過去形', 'ZH': '过去式', 'KO': '였'}[lang])
                    old = batch(before, True) if before else None
                    if before:
                        self.assertEqual(batch(rt, False), batch(before, False), (lang, edition, mode, 'custom'))
                    checked_inverse = 0
                    checked_html = 0
                    out_of_scope = 0
                    for i, ((text, kind), output) in enumerate(zip(cases, after)):
                        if kind != 'target':
                            out_of_scope += 1
                            if old is not None:
                                self.assertEqual(output, old[i], (lang, edition, mode, text, 'out-of-scope'))
                            if kind == 'protected': self.assertEqual(output, text[1:-1])
                            if kind == 'protected_at': self.assertEqual(output, text[1:-1])
                            if kind == 'normal' and mode == 'pure':
                                _, ending, kanji = CASES[text]
                                self.assertEqual(output, kanji + ending)
                            continue
                        word = text[1:-1]
                        root, ending, kanji = CASES[word]
                        self.assertNotIn('@', output)
                        self.assertTrue(output.endswith(ending), (lang, edition, mode, word))
                        if mode == 'pure':
                            self.assertEqual(output, kanji + ending)
                        else:
                            pairs = [(plain(m[1]), plain(m[2])) for m in RUBY.finditer(output)]
                            self.assertEqual(pairs, [(kanji, root)] if mode == 'kanji'
                                             else [(root, GLOSSES[lang][root])], (lang, edition, mode, word, output))
                            self.assertEqual(source(output, mode), word)
                            document = rt.apply_ruby_html_header_and_footer(output, fmt)
                            recovered = recovery.recover_standard_html(
                                document, 'kanji' if mode == 'kanji' else 'annotation')['text']
                            self.assertEqual(recovered, word)
                            checked_html += 1
                        if mode != 'ruby':
                            pure = output if mode == 'pure' else visible(output)
                            self.assertEqual(inv.convert_kanji_esperanto_to_alphabet(pure, indexes[edition]), word)
                            checked_inverse += 1
                    REPORT.append({'language': lang, 'edition': edition, 'mode': mode,
                                   'targets': 4, 'mixed_inputs': len(cases),
                                   'out_of_scope_compared': out_of_scope if old is not None else 0,
                                   'custom_compared': len(cases) if old is not None else 0,
                                   'inverse_exact': checked_inverse, 'html_exact': checked_html,
                                   'runtime_sha256': original_hash})
                    print('four local endings', lang, edition, mode, 'PASS', flush=True)
                    ed._load_lists_cached.clear()
                    del gg, gl, g2
                    gc.collect()
            self.assertEqual(hashlib.sha256((app / 'esp_text_replacement_module.py').read_bytes()).hexdigest(), original_hash)
            sys.path.pop(0)
        if os.environ.get('FOUR_LOCAL_ENDINGS_REPORT'):
            Path(os.environ['FOUR_LOCAL_ENDINGS_REPORT']).write_text(
                json.dumps({'passed': True, 'rows': REPORT}, ensure_ascii=False, indent=2), 'utf8')


if __name__ == '__main__':
    unittest.main()
