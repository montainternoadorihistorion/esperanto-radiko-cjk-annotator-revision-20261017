"""Verify the six reviewed displays, their neighbours, and the family name."""
import csv
import gzip
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENTS = {
    'korsak': ('兽ᴷˢ', '狐ᴷ'), 'hematit': ('矿ᴴ', '赤铁矿'),
    'kolokazi': ('草ᴷᶻ', '芋'), 'kolokasi': ('草ᴷᴼᴸ', '芋ᴷˢ'),
    'orcin': ('兽ᴼᴿ', '虎鲸ᴼᶜ'), 'grosulari': ('木ᴳˢ', '醋栗ᴳᴸ'),
}
OWNERS = {'vulp': '狐', 'ork': '虎鲸', 'rib': '醋栗', 'gros': '醋栗ᴳ',
          'kironekt': '兽ᴷᵀ', 'orikterop': '兽ᴼᵀ', 'krozofor': '草ᴷᶠ'}
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
BREAK = re.compile(r'<br\s*/?>', re.I)

def pieces(value):
    return [(BREAK.sub('', spelling), body) for body, spelling in RUBY.findall(value)]

class SixRootAssignments(unittest.TestCase):
    def test_forward_rules_and_manual_corrections(self):
        for language in ('JA', 'ZH', 'KO'):
            app = ROOT / f'Esperanto-Kanji-Ruby-{language}' / 'app_data'
            legacy = ROOT / 'assignment_editions' / 'legacy' / language
            for index, edition in enumerate(('legacy', 'current')):
                with self.subTest(language=language, edition=edition):
                    expected = {r: pair[index] for r, pair in ASSIGNMENTS.items()}
                    controls = {**OWNERS, 'izatis': '兽ᴵ' if edition == 'legacy' else '狐ᴵ'}
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
                            values = [v for k, v, *_ in rows if k == ' grosulariacoj ']
                            self.assertEqual(len(values), 1)
                            self.assertEqual(pieces(values[0]), [('grosulari', expected['grosulari']), ('ac', '科ᴬ')])
                            self.assertTrue(values[0].endswith('</ruby>oj '))

if __name__ == '__main__':
    unittest.main()

