"""Check the adopted root labels, maintained controls and medical it at explicit boundaries."""
import gzip
import importlib.util
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
GLOBAL = '全域替换用のリスト(列表)型配列(replacements_final_list)'
LOCAL = '局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'
LABELS = {
    'tazet': ('草ᵀᶻ', '水仙ᵀ'), 'makaon': ('虫ᴹᴷ', '蝶ᴹ'),
    'turbot': ('鱼ᵀᴮ', '比目鱼ᵀ'), 'uter': ('宫ᵁ', '子宫'),
    'pirus': ('木ᴾᴵ', '梨ᴾˢ'), 'eklezi': ('教ᴱ', '教会'),
    'pir': ('梨', '梨'), 'garaĝ': ('库ᴳ', '库ᴳ'),
}
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)


def roots(value):
    return RUBY.findall(value.replace('<br>', ''))


class TazetSixTests(unittest.TestCase):
    def test_root_labels_and_compound_boundaries(self):
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT / f'Esperanto-Kanji-Ruby-{lang}'
            for edition in ('current', 'legacy'):
                if edition == 'current':
                    raw = (app / 'app_data/置換リスト_漢字.json').read_bytes()
                else:
                    raw = gzip.decompress((ROOT / 'assignment_editions/legacy' / lang / 'kanji.json.gz').read_bytes())
                rules = json.loads(raw)
                labels = {r: v[edition == 'current'] for r, v in LABELS.items()}
                for group in (GLOBAL, LOCAL):
                    rows = {k: v for k, v, _ in rules[group] if k in LABELS}
                    with self.subTest(lang=lang, edition=edition, group=group):
                        self.assertEqual({r: roots(v) for r, v in rows.items()},
                                         {r: [(v, r)] for r, v in labels.items()})
                normal = {k: v for k, v, _ in rules[GLOBAL] if k in ('uterito', 'ekleziano')}
                self.assertEqual(roots(normal['uterito']), [(labels['uter'], 'uter'), ('炎ᵀ', 'it')])
                self.assertEqual(roots(normal['ekleziano']), [(labels['eklezi'], 'eklezi'), ('员', 'an')])
                local = next(v for k, v, _ in rules[LOCAL] if k == 'uterit')
                expected = '子宫炎ᵀ' if edition == 'current' else '宫炎'
                self.assertEqual(roots(local), [(expected, 'uterit')])
                del raw, rules

    def test_only_marked_current_medical_it_uses_inflammation(self):
        for lang, inflammation in [('JA', '炎'), ('ZH', '炎'), ('KO', '염')]:
            app = ROOT / f'Esperanto-Kanji-Ruby-{lang}'
            spec = importlib.util.spec_from_file_location('medical_' + lang, app / 'esp_text_replacement_module.py')
            engine = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(engine)
            data = json.loads((app / 'app_data/置換リスト_ルビ.json').read_bytes())
            forms = {'uterito', 'uterit', 'Uterit', 'UTERIT', 'uter', 'it', 'skrib', 'UTER', 'IT'}
            ordinary = [row for row in data[GLOBAL] if row[0] in forms]
            local = [row for row in data[LOCAL] if row[0] in forms]
            del data
            def protected(text, edition, bundled=True):
                rendered, marked, skipped = engine._protect_input_regions(
                    text, ['%901%'], ['@901@'], local, ordinary, True, bundled,
                    assignment_edition=edition,
                )
                for token, piece in marked + skipped:
                    rendered = rendered.replace(token, piece)
                return rendered
            for ending in ('o', 'on', 'oj', 'ojn'):
                for stem in ('@uter@@it@', '@uterit@'):
                    self.assertEqual(roots(protected(stem + ending, 'current'))[-1], ('it', inflammation))
            self.assertEqual(roots(protected('@UTER@@IT@O', 'current'))[-1], ('IT', inflammation))
            multi = roots(protected('@uter@@it@o @skrib@@it@a', 'current'))
            usual = roots(protected('@it@', 'legacy'))
            self.assertEqual(multi[-1], usual[0])
            self.assertEqual(roots(protected('@uter@@it@o', 'legacy'))[-1], usual[0])
            self.assertEqual(roots(protected('@uter@@it@o', None))[-1], usual[0])
            self.assertEqual(roots(protected('@uter@@it@o', 'current', False))[-1], usual[0])
            self.assertEqual(protected('%@uter@@it@o%', 'current'), '@uter@@it@o')


if __name__ == '__main__':
    unittest.main()
