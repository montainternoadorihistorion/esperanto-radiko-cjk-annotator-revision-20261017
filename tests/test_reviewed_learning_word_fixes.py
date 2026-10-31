"""Reviewed whole-word learning fixes use selected data, preserving custom JSON."""
from pathlib import Path
import gc, html, importlib.util, json, logging, re, sys, unittest
logging.disable(logging.WARNING)
ROOT = Path(__file__).resolve().parent.parent
BEFORE_ROOT = None
REPORT_ROWS = []
FORMATS = {'pure': '替换后文字列のみ(仅)保留(简单替换)',
           'kanji': 'HTML格式_Ruby文字_大小调整_汉字替换',
           'ruby': 'HTML格式_Ruby文字_大小调整'}
EXPECTED = {'anestez': '无ᴬ感ᴱ', 'ĉar': '车ᶜ̂', 'ĉaret': '车ᶜ̂小',
            'observad': '观行', 'alventag': '向来日',
            'programaranĝ': '程整ᴬ', 'otit': '耳ᴼᵀ炎ᵀ'}
CONTROLS = ['ĉar', '@ĉar@', '@an@', '@ret@', '@on@', '@tit@',
            '@ĉareton kaj ĉarojn@', '@ ĉarojn @', '@ĉarojn!@',
            '@anestezisto@', '@malanestezi@', '@xanestezi@',
            '@anestezix@', '@biontologio@', 'biontologio',
            '@greganta@', '@preganta@', '@kordonita@', '@semajn@o',
            'ĉarojn@example.com', 'xobservadony', 'programaranĝisto',
            '%observadon%', '%alventago%', '%programaranĝo%',
            '%@ĉareton@%', '@%ĉareton%@', '%<ĉarojn>&%']

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module); return module

def plain(value):
    return html.unescape(re.sub(r'<[^>]*>', '', value)).replace('\xa0', ' ')

def source(value, mode):
    return plain(re.sub(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',
                        lambda m: m[2] if mode == 'kanji' else m[1], value, flags=re.S))

class ReviewedLearningWordFixes(unittest.TestCase):
    def test_explicit_manual_corrections_keep_priority(self):
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT/f'Esperanto-Kanji-Ruby-{lang}'; sys.path.insert(0, str(app))
            rt = load(app/'esp_text_replacement_module.py', 'manual_rt_'+lang)
            ov = load(app/'esp_overlay_module.py', 'manual_overlay_'+lang)
            words = ['anestezi', 'ĉarojn', 'ĉareton', 'observadon', 'alventago', 'programaranĝo', 'otito']
            entries = [[word, 'MANUAL'+str(i), '$'+str(9000000+i)+'$'] for i, word in enumerate(words)]
            rules = ov.merge_overlay([], entries)
            for mode, fmt in FORMATS.items():
                for i, word in enumerate(words):
                    for wrapped in (word, '@'+word+'@'):
                        actual = rt.orchestrate_comprehensive_esperanto_text_replacement(
                            wrapped, [], [], [], rules, [], fmt, reviewed_local_decompositions=True)
                        self.assertEqual(actual, 'MANUAL'+str(i), (lang, mode, wrapped))
                    protected = rt.orchestrate_comprehensive_esperanto_text_replacement(
                        '%'+word+'%', [], [], [], rules, [], fmt, reviewed_local_decompositions=True)
                    self.assertEqual(protected, word)
            phrase_rules = ov.merge_overlay([], [['la programaranĝo', 'PHRASE', '$9000100$']])
            for fmt in FORMATS.values():
                actual = rt.orchestrate_comprehensive_esperanto_text_replacement(
                    'la programaranĝo', [], [], [], phrase_rules, [], fmt,
                    reviewed_local_decompositions=True)
                self.assertEqual(actual, 'PHRASE')
            rows = rt.create_replacements_list_for_localized_replacement(
                '@ĉareton@', ['@999@'], [], rules, reviewed_local_decompositions=True)
            self.assertEqual(rows[0][2], 'MANUAL2')
            sys.path.pop(0)

    def test_two_letter_boundaries_and_twelve_round_limit(self):
        data = json.loads((ROOT/'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字_純粋置換.json').read_text('utf8'))
        real_rules = data[next(k for k in data if 'replacements_list_for_2char' in k)]
        for lang in ('JA', 'ZH', 'KO'):
            rt = load(ROOT/f'Esperanto-Kanji-Ruby-{lang}/esp_text_replacement_module.py', 'boundary_'+lang)
            def convert(text, rules=real_rules, enabled=True):
                return rt.orchestrate_comprehensive_esperanto_text_replacement(
                    text, [], [], [], [('san', 'SAN', '$8800$')], rules, FORMATS['pure'],
                    reviewed_local_decompositions=enabled)
            # Real 330 rules need three rounds. The old outer ! cuts off the boundary.
            self.assertEqual(convert('sanigejetaro'), 'SAN使所小群o')
            self.assertEqual(convert('sanigejetaro', enabled=False), 'SAN使所etaro')
            for word in ('xamiqx', 'amSANig', '%sanigejetaro%'):
                self.assertEqual(convert(word), convert(word, enabled=False))
            self.assertEqual(convert('sanigejetaro sanigejetaro'), 'SAN使所小群o SAN使所小群o')
            # Reverse-ordered synthetic pairs force a new round at each pair.
            # A longer chain stops after exactly 12 rounds, with no marker leaks.
            rules = [('$bb', '$B', '$$8002$'), ('$aa', '$A', '$$8001$')]
            self.assertEqual(convert('san'+'aa'+'bbaa'*11, rules), 'SAN'+'A'+'BA'*11)
            self.assertEqual(convert('san'+'aa'+'bbaa'*12, rules), 'SAN'+'A'+'BA'*11+'bbaa')

    def test_bundled_forms_controls_custom_and_roundtrips(self):
        inverse = load(ROOT/'Esperanto-Reverter-JA/esperanto_converter.py', 'learning_inverse')
        recovery = load(ROOT/'Esperanto-Reverter-JA/html_source_recovery.py', 'learning_recovery')
        indices = {edition: inverse.build_mapping_index_cached(inverse.effective_mapping_records(
            key, inverse.load_dictionary_source(key))) for edition, key in
            (('current', 'pejvo-piv-20260620'), ('legacy', 'pre-las-20261017'))}
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT/f'Esperanto-Kanji-Ruby-{lang}'; sys.path.insert(0, str(app))
            rt = load(app/'esp_text_replacement_module.py', 'learning_rt_'+lang)
            ed = load(app/'esp_assignment_edition.py', 'learning_ed_'+lang)
            before = load(BEFORE_ROOT/f'Esperanto-Kanji-Ruby-{lang}/esp_text_replacement_module.py',
                          'learning_before_'+lang) if BEFORE_ROOT else None
            self.assertEqual(set(rt._REVIEWED_LOCAL_DECOMPOSITIONS), {'greganta', 'preganta'})
            for edition in ('current', 'legacy'):
                for mode, fmt in FORMATS.items():
                    gg, gl, g2 = ed.load_lists(app/'app_data', mode, edition)
                    inputs = ['@'+w+'@' for w in rt._REVIEWED_WORD_FORMS]
                    inputs += sorted(rt._REVIEWED_NORMAL_FORMS) + CONTROLS
                    def batch(engine, enabled=True):
                        output = engine.orchestrate_comprehensive_esperanto_text_replacement(
                            ' ◆ '.join(inputs), [], gl, [], gg, g2, fmt,
                            reviewed_local_decompositions=enabled)
                        parts = [s.strip() for s in output.split('◆')]
                        self.assertEqual(len(parts), len(inputs))
                        return dict(zip(inputs, parts))
                    current = batch(rt); previous = batch(before) if before else {}
                    for key in inputs:
                        value = current[key]
                        if key in CONTROLS:
                            if before: self.assertEqual(value, previous[key], (lang, edition, mode, key))
                        else:
                            word = key.strip('@'); stem, ending, case = rt._REVIEWED_WORD_FORMS[word]
                            expected = EXPECTED[stem] + (ending.upper() if case == 2 else ending)
                            self.assertNotIn('@', value)
                            if mode == 'pure':
                                self.assertEqual(value, expected, (lang, edition, key))
                                restored = inverse.convert_kanji_esperanto_to_alphabet(value, indices[edition])
                                self.assertEqual(restored, word.lower(), (edition, word, restored))
                            else:
                                self.assertEqual(source(value, mode), word)
                                document = rt.apply_ruby_html_header_and_footer(value, fmt)
                                self.assertEqual(recovery.recover_standard_html(document,
                                    'kanji' if mode == 'kanji' else 'annotation')['text'], word)
                                if mode == 'ruby' and stem in {'ĉar', 'ĉaret'}:
                                    self.assertIn(rt._REVIEWED_CART_GLOSS+'</rt>', value)
                                    for wrong in ('なぜ', '因为', '때문에'): self.assertNotIn(wrong, value)
                                if mode == 'ruby' and stem == 'anestez':
                                    for wrong in ('成員', '成员', '구성원'): self.assertNotIn(wrong, value)
                        REPORT_ROWS.append({'language': lang, 'edition': edition, 'mode': mode,
                                            'input': key, 'before': previous.get(key), 'after': value})
                    # Explicit opt-out remains byte-for-byte compatible with the old engine.
                    if before: self.assertEqual(batch(rt, False), batch(before, False))
                    ed._load_lists_cached.clear(); del gg, gl, g2; gc.collect()
            sys.path.pop(0)

if __name__ == '__main__': unittest.main()
