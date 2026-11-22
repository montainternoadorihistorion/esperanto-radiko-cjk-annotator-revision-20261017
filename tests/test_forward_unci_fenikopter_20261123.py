"""Check the snow leopard and flamingo assignments in both dictionary editions."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENTS = {'unci': ('兽ᵁᶜ', '豹ᵁ'), 'fenikopter': ('鸟ᶠᴾ', '火烈鸟ᶠᴱ')}
OWNERS = {'panter': '豹', 'leopard': '豹ᴸ', 'flameng': '火烈鸟', 'fenikur': '鸟ᶠᴺ'}
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
BREAK = re.compile(r'<br\s*/?>', re.I)

def pieces(value):
    return [(BREAK.sub('', spelling), body) for body, spelling in RUBY.findall(value)]

class SnowLeopardAndFlamingoAssignments(unittest.TestCase):
    def test_forward_rules_and_manual_corrections(self):
        for language in ('JA', 'ZH', 'KO'):
            app = ROOT / f'Esperanto-Kanji-Ruby-{language}' / 'app_data'
            legacy = ROOT / 'assignment_editions' / 'legacy' / language
            for index, edition in enumerate(('legacy', 'current')):
                with self.subTest(language=language, edition=edition):
                    expected = {r: pair[index] for r, pair in ASSIGNMENTS.items()}
                    controls = OWNERS
                    csv_path = (app / '世界语词根-汉字对应列表_参照2新割当_7791.csv'
                                if edition == 'current' else legacy / 'kanji.csv')
                    with csv_path.open(encoding='utf-8-sig', newline='') as source:
                        manual = dict(csv.reader(source))
                    for root, display in (expected | controls).items():
                        self.assertEqual(manual[root], display)
                    raw = ((app / '置換リスト_漢字.json').read_bytes() if edition == 'current'
                           else gzip.decompress((legacy / 'kanji.json.gz').read_bytes()))
                    payload = json.loads(raw)
                    for prefix in ('局部', '全域'):
                        rows = next(v for k, v in payload.items() if k.startswith(prefix))
                        forms = {v: display for root, display in expected.items()
                                 for v in (root, root.title(), root.upper())}
                        observed = {word: pieces(value) for word, value, *_ in rows if word in forms}
                        self.assertEqual(observed, {k: [(k, v)] for k, v in forms.items()})
                        if prefix == '局部':
                            neighbours = {k: pieces(v) for k, v, *_ in rows if k in controls}
                            self.assertEqual(neighbours, {k: [(k, v)] for k, v in controls.items()})

                        else:
                            singular = {word: markup for word, markup, *_ in rows if word == 'uncio'}
                            self.assertEqual(pieces(singular['uncio']), [('unci', expected['unci'])])
                            self.assertTrue(singular['uncio'].endswith('</ruby>o'))


if __name__ == '__main__':
    unittest.main()
