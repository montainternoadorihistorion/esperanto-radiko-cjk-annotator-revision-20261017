"""Marker contracts, using tiny rules to isolate parsing from dictionary policy."""
import html
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent


def visible(source):
    class Reader(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.text, self.depth = [], 0

        def handle_starttag(self, tag, attrs):
            if tag == 'rt':
                self.depth += 1

        def handle_endtag(self, tag):
            if tag == 'rt':
                self.depth -= 1

        def handle_data(self, data):
            if not self.depth:
                self.text.append(data)
    reader = Reader()
    reader.feed(source)
    return ''.join(reader.text)


class MarkerRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = {}
        for language in ('JA', 'ZH', 'KO'):
            path = ROOT / f'Esperanto-Kanji-Ruby-{language}' / 'esp_text_replacement_module.py'
            spec = importlib.util.spec_from_file_location('marker_runtime_' + language, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls.modules[language] = module

    def render(self, module, source, mode='pure', skip=(), local=()):
        def output(word, meaning):
            return meaning if mode == 'pure' else f'<ruby>{word}<rt>{meaning}</rt></ruby>'
        localized = [(word, output(word, meaning), f'$L{i}$') for i, (word, meaning) in
                     enumerate([('amiko', '友o'), ('semajn', '周'), ('am', '爱')])]
        global_rules = [(word, output(word, meaning), f'$G{i}$') for i, (word, meaning) in
                        enumerate([('amiko', '友o'), ('kaj', '和'), ('mi', '我')])]
        return module.orchestrate_comprehensive_esperanto_text_replacement(
            source, list(skip), localized, list(local), global_rules, [],
            'HTML格式_Ruby文字_大小调整' if mode == 'html' else 'pure',
        )

    def test_word_internal_and_unicode_adjacent_markers(self):
        for language, module in self.modules.items():
            for source, expected in [('@semajn@tagoj', '周tagoj'),
                                     ('antaŭ@semajn@', 'antaŭ周'),
                                     ('ĉ@semajn@a', 'ĉ周a'),
                                     ('a@amiko@b @amiko@', 'a友ob 友o'),
                                     ('@amiko@@amiko@', '友o友o')]:
                with self.subTest(language=language, source=source):
                    self.assertEqual(self.render(module, source), expected)

    def test_marker_outside_text_still_converts(self):
        for language, module in self.modules.items():
            with self.subTest(language=language):
                self.assertEqual(self.render(module, '@amiko@ kaj mi'), '友o 和 我')

    def test_long_payload_and_placeholder_exhaustion(self):
        for language, module in self.modules.items():
            with self.subTest(language=language):
                self.assertEqual(self.render(module, '@' + 'amiko ' * 8 + '@'), '友o ' * 8)
                source = ' '.join(['@amiko@'] * 6)
                self.assertEqual(self.render(module, source, local=['@500@']), ' '.join(['友o'] * 6))

    def test_emails_do_not_consume_adjacent_valid_markers(self):
        for language, module in self.modules.items():
            for source in ['a@host.eo b@host.eo @amiko@',
                           'name+tag@sub.example.org, a@b.eo; @amiko@',
                           'a@example.com. b@example.org. @amiko@',
                           'foo@bar.com@amiko@',
                           'a@localhost b@localhost @amiko@']:
                with self.subTest(language=language, source=source):
                    self.assertEqual(self.render(module, source), source.replace('@amiko@', '友o'))

    def test_unpaired_empty_and_multiline_markers_stay_literal(self):
        for language, module in self.modules.items():
            for source in ['@@', '@xyz', 'xyz@', '@xyz\nxyz@', '＠xyz＠']:
                with self.subTest(language=language, source=source):
                    self.assertEqual(self.render(module, source), source)

    def test_percent_protection_has_priority_and_preserves_inner_markers(self):
        for language, module in self.modules.items():
            for source, expected in [('%@amiko@% @amiko@', '@amiko@ 友o'),
                                     ('%amiko% %amiko%', 'amiko amiko'),
                                     ('%a@b@c%', 'a@b@c')]:
                with self.subTest(language=language, source=source):
                    self.assertEqual(self.render(module, source), expected)

    def test_html_metacharacters_are_not_treated_as_esperanto(self):
        for language, module in self.modules.items():
            for symbol in ['&', '&&', '<', '>', '<b>']:
                source = '@amiko ' + symbol + ' amiko@'
                with self.subTest(language=language, source=source):
                    rendered = self.render(module, source, 'html')
                    self.assertEqual(visible(rendered), source[1:-1])
                    self.assertEqual(rendered.count('<ruby>'), 2)
                    self.assertNotIn('<b>', rendered)

    def test_percent_length_uses_original_input_not_html_expansion(self):
        payload = '<amiko>' + 'x' * 42
        self.assertEqual(len(payload), 49)
        for language, module in self.modules.items():
            with self.subTest(language=language):
                rendered = self.render(module, '%' + payload + '%', 'html')
                self.assertEqual(visible(rendered), payload)
                self.assertNotIn('<ruby>', rendered)
                self.assertEqual(rendered, html.escape(payload, quote=False))

    def test_html_round_trip_for_literal_entities_and_protected_text(self):
        for language, module in self.modules.items():
            for source in ['%&amp; &#38; <script>x</script>%', '@& < >@']:
                with self.subTest(language=language, source=source):
                    rendered = self.render(module, source, 'html')
                    self.assertEqual(visible(rendered), source[1:-1])
                    self.assertNotIn('<script>', rendered)

    def test_public_marker_finder_uses_same_contract(self):
        for language, module in self.modules.items():
            with self.subTest(language=language):
                self.assertEqual(module.find_at_enclosed_strings_for_localized_replacement(
                    'a@host.eo @semajn@tagoj ĉ@amiko@'), ['semajn', 'amiko'])

    def test_shared_whole_word_boundary_is_not_consumed(self):
        for language, module in self.modules.items():
            for count in (1, 2, 3, 8):
                with self.subTest(language=language, count=count):
                    source = ' '.join(['xyz'] * count)
                    result = module.orchestrate_comprehensive_esperanto_text_replacement(
                        source, [], [], [], [(' xyz ', ' OK ', ' $B1$ '), ('xyz', 'BAD', '$B2$')], [], 'pure')
                    self.assertEqual(result, ' '.join(['OK'] * count))


if __name__ == '__main__':
    unittest.main()
