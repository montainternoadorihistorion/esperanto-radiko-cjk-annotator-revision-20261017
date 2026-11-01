"""Meaning-aware ruby regressions for the two assignment editions.

Use separate normal/local batches and isolated homographs: one mixed request
can trigger automatic corrections that conceal a faulty single-word rule.
The boundary repair matrix is covered separately.
"""
from contextlib import contextmanager
from pathlib import Path
import csv
import functools
import gc
import html
import importlib.util
import json
import logging
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
FORMAT = 'HTML格式_Ruby文字_大小调整'
RUBY = re.compile(r'<ruby\b[^>]*>(.*?)<rt\b[^>]*>(.*?)</rt>\s*</ruby>', re.S | re.I)
AS_WORDS = ('dankegas', 'enestas', 'ricevindas', 'sumiĝas', 'trametas', 'datumas', 'as-tempo')
AS_SPLIT = ('tra/met/as', 'dank/eg/as', 'en/est/as', 'ricev/ind/as', 'sum/iĝ/as')
COMMON_ROOT_WORDS = {
    'solvi': 'solv', 'solvo': 'solv', 'solvaĵo': 'solv', 'akvosolvebla': 'solv',
    'planto': 'plant', 'planti': 'plant', 'propozicio': 'propozici',
}
ANNOTATION_CSV = {
    'JA': 'エスペラント語根-日本語訳ルビ対応リスト.csv',
    'ZH': '世界语词根-中文注释对应列表.csv',
    'KO': '에스페란토 어근-한국어 번역 루비 대응 목록.csv',
}
WORDS = (*AS_WORDS, 'aso', 'asoj', 'ason', 'asojn', 'pensiuloj', 'pensi',
         'konsilianoj', 'konsili', 'metrosistemon', 'metroj', 'metron', 'metrojn',
         'viktimoj', 'gazeto', 'radioamatoroj', 'radioaj', 'boreliozo-kazoj',
         'radioterapio', 'sunradio', 'programado', 'komunumo', 'rolon',
         'sentas', 'kiu', 'parolas', *COMMON_ROOT_WORDS)
EXPECT = {
    'JA': {'as': '現在形', 'ace': 'エース', 'pensi': '年金', 'pens': '思う',
           'konsili': '評議会', 'konsil': '助言する', 'metro': '地下鉄', 'metr': 'メートル',
           'viktim': 'いけにえ;犠牲者', 'gazet': '新聞・雑誌', 'radio': '光線・無線',
           'kaz': '格・事例', 'therapy': '放射線', 'parol': '話す',
           'solv': '解決;溶かす', 'plant': '植物;植える', 'propozici': '節;命題'},
    'ZH': {'as': '现在时', 'ace': 'A牌', 'pensi': '养老金', 'pens': '思考',
           'konsili': '评议会', 'konsil': '建议', 'metro': '地铁', 'metr': '米',
           'viktim': '祭品;受害者', 'gazet': '报刊', 'radio': '光线;无线电',
           'kaz': '格;事例', 'therapy': '放射线', 'program': '程序;节目',
           'solv': '解决;溶解', 'plant': '植物;种植', 'propozici': '分句;命题'},
    'KO': {'as': '현재', 'ace': '에이스', 'pensi': '연금', 'pens': '생각하다',
           'konsili': '평의회', 'konsil': '조언하다', 'metro': '지하철', 'metr': '미터',
           'viktim': '제물;희생자', 'gazet': '신문;잡지', 'radio': '광선;무선',
           'kaz': '격;사례', 'therapy': '방사선', 'um': '의미 불특정',
           'rol': '역할', 'sent': '느끼다', 'kiu': '누구;어느 것',
           'solv': '해결하다;녹이다', 'plant': '식물;심다', 'propozici': '절;명제'},
}


def plain(value):
    return html.unescape(re.sub(r'<[^>]*>', '', value)).replace('\xa0', ' ')


def source(value):
    return plain(re.sub(r'<rt\b[^>]*>.*?</rt>', '', value, flags=re.S | re.I)).strip()


def glosses(value):
    return [(plain(rb).lower(), plain(rt)) for rb, rt in RUBY.findall(value)]


@contextmanager
def app_modules(language):
    app = ROOT / ('Esperanto-Kanji-Ruby-' + language)
    original_path = list(sys.path)
    names = []
    modules = []
    try:
        sys.path.insert(0, str(app))
        for name in ('esp_text_replacement_module', 'esp_overlay_module', 'esp_assignment_edition'):
            unique = 'annotation_semantics_' + language + '_' + name
            spec = importlib.util.spec_from_file_location(unique, app / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            sys.modules[unique] = module
            names.append(unique)
            spec.loader.exec_module(module)
            modules.append(module)
        modules[1]._session_list = lambda: []
        yield app, modules
    finally:
        sys.path[:] = original_path
        for name in names:
            sys.modules.pop(name, None)
        modules.clear()
        gc.collect()


class LearningAnnotationSemantics(unittest.TestCase):
    def test_three_common_glosses_cover_packaged_and_generation_sources(self):
        roots = set(COMMON_ROOT_WORDS.values())
        for language, expected in EXPECT.items():
            data = ROOT / ('Esperanto-Kanji-Ruby-' + language) / 'app_data'
            packaged = json.loads((data / '置換リスト_ルビ.json').read_text(encoding='utf-8'))
            seen = {root: 0 for root in roots}
            for section, rows in packaged.items():
                for row in rows:
                    for root, meaning in glosses(row[1]):
                        if root in roots:
                            with self.subTest(language=language, section=section, key=row[0], root=root):
                                self.assertEqual(meaning, expected[root])
                            seen[root] += 1
            self.assertTrue(all(seen.values()), (language, 'packaged', seen))
            del packaged

            words = json.loads((data / 'word_anno.json').read_text(encoding='utf-8'))
            seen = {root: 0 for root in roots}
            for key, pairs in words.items():
                for rb, meaning in pairs:
                    root = plain(rb).lower()
                    if root in roots:
                        with self.subTest(language=language, source_key=key, root=root):
                            self.assertEqual(meaning, expected[root])
                        seen[root] += 1
            self.assertTrue(all(seen.values()), (language, 'word_anno', seen))
            del words

            with (data / ANNOTATION_CSV[language]).open(encoding='utf-8-sig', newline='') as handle:
                rows = [row for row in csv.reader(handle) if row and row[0].lower() in roots]
            self.assertEqual(len(rows), len(roots), (language, rows))
            self.assertEqual({row[0].lower() for row in rows}, roots)
            for root, meaning in rows:
                with self.subTest(language=language, csv_root=root):
                    self.assertEqual(meaning, expected[root.lower()])

    def test_generation_sources_disambiguate_tense_without_replacing_ace(self):
        for language, expected in EXPECT.items():
            data = ROOT / ('Esperanto-Kanji-Ruby-' + language) / 'app_data'
            words = json.loads((data / 'word_anno.json').read_text(encoding='utf-8'))
            with self.subTest(language=language):
                self.assertEqual(words['as'], [['as', expected['ace']]])
                for key in AS_SPLIT:
                    self.assertEqual([p[0] for p in words[key]], key.split('/'))
                    self.assertEqual(words[key][-1], ['as', expected['as']])
                for key in ('@typed:as-tempo:0', '@typed:datumas:2'):
                    self.assertEqual(words[key], [['as', expected['as']]])
            del words

    def test_two_editions_preserve_meanings_and_original_spelling(self):
        old_logging = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            for language, expected in EXPECT.items():
                with app_modules(language) as (app, modules):
                    rt, ov, ed = modules
                    data = app / 'app_data'
                    ps = rt.import_placeholders(str(data / 'placeholders_skip.txt'))
                    pl = rt.import_placeholders(str(data / 'placeholders_localcapture.txt'))
                    run = functools.partial(rt.orchestrate_comprehensive_esperanto_text_replacement,
                                            reviewed_local_decompositions=True)
                    edition_results = {}
                    for edition in ('current', 'legacy'):
                        gg, gl, g2 = ed.load_lists(data, 'ruby', edition)
                        gg = ov.merge_overlay(gg, ov.load_overlay_entries(str(data), 'ruby', edition))

                        def convert(text):
                            return ov.autofix_render(text, ps, gl, pl, gg, g2, FORMAT,
                                                     str(data), 'ruby', run, edition)

                        outputs = {}
                        for mode in ('normal', 'local'):
                            inputs = list(WORDS) if mode == 'normal' else ['@' + w + '@' for w in WORDS]
                            result = convert(' ◆ '.join(inputs)).split('◆')
                            self.assertEqual(len(result), len(WORDS))
                            outputs[mode] = dict(zip(WORDS, (s.strip() for s in result)))
                            for word, rendered in outputs[mode].items():
                                with self.subTest(language=language, edition=edition, mode=mode, word=word):
                                    self.assertEqual(source(rendered), word)
                                    self.assertNotIn('@', rendered)

                            requirements = [(w, 'as', expected['as']) for w in AS_WORDS]
                            requirements += [(w, 'as', expected['ace']) for w in ('aso', 'asoj', 'ason', 'asojn')]
                            requirements += [(word, root, expected[root])
                                             for word, root in COMMON_ROOT_WORDS.items()]
                            requirements += [('pensiuloj', 'pensi', expected['pensi']),
                                             ('konsilianoj', 'konsili', expected['konsili']),
                                             ('metrosistemon', 'metro', expected['metro']),
                                             ('viktimoj', 'viktim', expected['viktim']),
                                             ('gazeto', 'gazet', expected['gazet']),
                                             ('radioamatoroj', 'radio', expected['radio']),
                                             ('radioaj', 'radio', expected['radio']),
                                             ('boreliozo-kazoj', 'kaz', expected['kaz'])]
                            metric_gloss = '[単]メートル' if language == 'JA' and mode == 'local' else expected['metr']
                            requirements += [(w, 'metr', metric_gloss) for w in ('metroj', 'metron', 'metrojn')]
                            if language == 'JA':
                                requirements.append(('parolas', 'parol', expected['parol']))
                            if language == 'ZH':
                                requirements.append(('programado', 'program', expected['program']))
                            if language == 'KO':
                                requirements += [(word, root, expected[root]) for word, root in
                                                 (('komunumo', 'um'), ('rolon', 'rol'),
                                                  ('sentas', 'sent'), ('kiu', 'kiu'))]
                            for word, root, meaning in requirements:
                                with self.subTest(language=language, edition=edition, mode=mode, word=word, root=root):
                                    self.assertIn((root, meaning), glosses(outputs[mode][word]))

                        # Surface homographs use the existing ordinary interpretation;
                        # @pensi/@konsili may deliberately select the independent root.
                        for word, root in (('pensi', 'pens'), ('konsili', 'konsil')):
                            self.assertIn((root, expected[root]), glosses(outputs['normal'][word]))
                        self.assertIn(('radi', expected['therapy']), glosses(outputs['normal']['radioterapio']))

                        # Single inputs prove that another @ input is not masking a bad rule.
                        for text, root, meaning in (('ricevindas', 'as', expected['as']),
                                                    ('@ricevindas@', 'as', expected['as']),
                                                    ('@aso@', 'as', expected['ace']),
                                                    ('pensi', 'pens', expected['pens'])):
                            rendered = convert(text)
                            self.assertEqual(source(rendered), text.strip('@'))
                            self.assertIn((root, meaning), glosses(rendered))
                        # Check each adopted meaning independently of a batch, so
                        # another word's automatic correction cannot mask its rule.
                        for word, root in (('akvosolvebla', 'solv'), ('planto', 'plant'),
                                           ('propozicio', 'propozici')):
                            for text in (word, '@' + word + '@'):
                                with self.subTest(language=language, edition=edition, isolated=text):
                                    rendered = convert(text)
                                    self.assertEqual(source(rendered), word)
                                    self.assertIn((root, expected[root]), glosses(rendered))
                        protected = convert('%dankegas pensiuloj%')
                        self.assertEqual(protected, 'dankegas pensiuloj')
                        edition_results[edition] = outputs
                    self.assertEqual(edition_results['current'], edition_results['legacy'], language)
                    del gg, gl, g2, edition_results, outputs
        finally:
            logging.disable(old_logging)


if __name__ == '__main__':
    unittest.main()
