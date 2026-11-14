"""Closed ven generation repair: unchanged assignments, keys and other rows."""
from pathlib import Path
import csv
import gc
import gzip
import hashlib
import importlib.util
import json
import logging
import re
import sys
import tempfile
import unittest

logging.disable(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[1]
GLOBAL = '全域替换用のリスト(列表)型配列(replacements_final_list)'
LOCAL = '局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'
FORMS = ('ven', 'VEN', 'Ven')
BEFORE = {'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字.json': 'fede137a0d7e82c0e351f0e10cab36ef7bd3ded5ee9adfe57d54db0f84162114', 'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_漢字.json': 'a400ca9a30415a21704e9e70f22298c8573aefab9ff67a2b3626e97a3bb4ca92', 'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_漢字.json': '2af79a24687a71c0df856e39d047e4e613ddeb41fdb95f0386bde1750402a38a', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字_純粋置換.json': '37fc4cc79322325f41d5b5bab1f26516906ad6c4ec89dbb5a08b9536eece621a', 'assignment_editions/legacy/JA/kanji.json.gz': '9828f0c55f4853bb4b3c7c49cd7e05b9313679ca5e97f81282f024ba8fde177a', 'assignment_editions/legacy/ZH/kanji.json.gz': 'f6e02a9f55d57b66c0dbbb1c19ff1bda4b2ffe4df850c8763bdadf328f09fae4', 'assignment_editions/legacy/KO/kanji.json.gz': '6ed899f1da480bc5387c8a8ba8ef730348c786e5983acef2f9e57709904c6fcd', 'assignment_editions/legacy/JA/pure.json.gz': '3a8153310fc09a324a9c62ad8d49aec98d9031e34ef825030ae98726d2e0ca56'}
FORMATS = {'pure': '替换后文字列のみ(仅)保留(简单替换)',
           'kanji': 'HTML格式_Ruby文字_大小调整_汉字替换',
           'ruby': 'HTML格式_Ruby文字_大小调整'}
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def strip(value):
    return re.sub('</?ruby>', '', re.sub('<rt[^>]*>.*?</rt>', '', value, flags=re.S))


def old_value(spelling, pure):
    tail = 'N' if spelling.isupper() else 'n'
    return '哀ⱽ' + tail if pure else (
        '<ruby>哀ⱽ<rt class="XXL_L">' + spelling[:-1] + '</rt></ruby>' + tail)


def restore_rows(rows, pure):
    return [[row[0], old_value(row[0], pure), *row[2:]] if row[0] in FORMS
            else list(row) for row in rows]


class VenGenerationTests(unittest.TestCase):
    def test_full_payload_fingerprints_prove_only_six_values_changed(self):
        self.assertEqual(len(BEFORE), 8)
        for relative, expected in BEFORE.items():
            path = ROOT / relative; raw = path.read_bytes()
            payload = json.loads(gzip.decompress(raw) if relative.endswith('.gz') else raw)
            pure = 'pure.json' in relative or '純粋置換' in relative
            restored = {}
            for group, rows in payload.items():
                if group in (GLOBAL, LOCAL):
                    targets = [row for row in rows if row[0] in FORMS]
                    self.assertEqual(len(targets), 3)
                    self.assertEqual({row[0] for row in targets}, set(FORMS))
                    for row in targets:
                        self.assertEqual(strip(row[1]), '来')
                        if not pure:
                            self.assertEqual(RUBY.fullmatch(row[1])[2], row[0])
                    restored[group] = restore_rows(rows, pure)
                else:
                    restored[group] = rows
            encoded = json.dumps(restored, ensure_ascii=False).encode('utf-8')
            self.assertEqual(hashlib.sha256(encoded).hexdigest(), expected, relative)
            del payload, restored, encoded; gc.collect()

    def test_both_authorities_still_distinguish_ven_and_ve(self):
        for lang in ('JA', 'ZH', 'KO'):
            for path in [ROOT / f'Esperanto-Kanji-Ruby-{lang}/app_data/世界语词根-汉字对应列表_参照2新割当_7791.csv',
                         ROOT / f'assignment_editions/legacy/{lang}/kanji.csv']:
                rows = dict(csv.reader(path.open(encoding='utf-8-sig')))
                self.assertEqual(rows['ven'], '来')
                self.assertEqual(rows['ve'], '哀ⱽ')

    def test_real_modes_and_custom_json(self):
        positive = {'ven': '来', 'Ven': '来', 'VEN': '来',
                    '@ven@': '来', '@Ven@': '来', '@VEN@': '来',
                    '@veni@': '来i', '@venis@': '来is', '@VENI@': '来I',
                    '@alvenigi@': '向来使i', '@ven@i': '来i',
                    '@al@@ven@@ig@i': '向来使i', 'al@ven@igi': 'al来使i',
                    're@ven@i': 're来i'}
        controls = ['ve', 'Ve', 'VE', '@ve@', '@Ve@', '@VE@', 've!', 've n',
                    'veni', 'venis', 'alvenigi', 'reveni', 'kunveno', 'venĝo',
                    'ventro', 'vento', 'veneno', 'avenuo', 'aventuro',
                    'Venezuelo', 'Venero', 'veno', 'vena',
                    '%ven%', '%@veni@%', '%ve%', '%哀ⱽn%', '%来%',
                    'svarmaj', 'varmaj', '@ĉareton@', '@domon@', '@semajno@']
        inputs = list(positive) + controls
        for lang in ('JA', 'ZH', 'KO'):
            app = ROOT / ('Esperanto-Kanji-Ruby-' + lang); data = app / 'app_data'
            sys.path.insert(0, str(app))
            rt = load(app / 'esp_text_replacement_module.py', 'ven_runtime_' + lang)
            ed = load(app / 'esp_assignment_edition.py', 'ven_edition_' + lang)
            ov = load(app / 'esp_overlay_module.py', 'ven_overlay_' + lang)
            for edition in ('current', 'legacy'):
                for mode, fmt in FORMATS.items():
                    gg, gl, g2 = ed.load_lists(data, mode, edition)
                    overlay_mode = 'kanji' if mode == 'pure' else mode
                    overlay = ov.load_overlay_entries(str(data), overlay_mode, edition)
                    if mode == 'pure':
                        overlay = [[a, strip(b), c] for a, b, c in overlay]
                    before_global = restore_rows(gg, mode == 'pure') if mode != 'ruby' else gg
                    before_local = restore_rows(gl, mode == 'pure') if mode != 'ruby' else gl
                    after_rules = ov.merge_overlay(gg, overlay)
                    before_rules = ov.merge_overlay(before_global, overlay)

                    def render(rules, local):
                        text = ' ◆ '.join(inputs)
                        value = rt.orchestrate_comprehensive_esperanto_text_replacement(
                            text, [], local, [], rules, g2, fmt,
                            reviewed_local_decompositions=True)
                        auto = ov.auto_overlay_entries(value, str(data), overlay_mode, edition)
                        if mode == 'pure': auto = [[a, strip(b), c] for a, b, c in auto]
                        if auto:
                            value = rt.orchestrate_comprehensive_esperanto_text_replacement(
                                text, [], local, [], ov.merge_overlay(rules, auto), g2, fmt,
                                reviewed_local_decompositions=True)
                        pieces = [v.strip() for v in value.split('◆')]
                        self.assertEqual(len(pieces), len(inputs))
                        return dict(zip(inputs, pieces))

                    after = render(after_rules, gl)
                    before = render(before_rules, before_local) if mode != 'ruby' else after
                    for text in controls:
                        self.assertEqual(after[text], before[text], (lang, edition, mode, text))
                    if mode != 'ruby':
                        for text, expected in positive.items():
                            self.assertEqual(strip(after[text]), expected, (lang, edition, mode, text))
                        self.assertEqual(strip(after['ve']), '哀ⱽ')
                    else:
                        self.assertEqual([m[1] for m in RUBY.finditer(after['@ven@'])], ['ven'])
                    print('ven', lang, edition, mode, 'PASS', flush=True)
                    ed._load_lists_cached.clear()
                    del gg, gl, g2, before_global, before_local, after_rules, before_rules
                    gc.collect()
            # Loading a custom file with the bundled basename does not import
            # the maintenance correction, even when it contains the old value.
            with tempfile.TemporaryDirectory() as temp:
                payload = {ed.GLOBAL: [['ven', '哀ⱽn', '$1$']],
                           ed.LOCAL: [['ven', 'USER', '@1@']], ed.TWO: []}
                path = Path(temp) / '置換リスト_漢字_純粋置換.json'
                path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                self.assertEqual(ed.load_lists_path(path), (payload[ed.GLOBAL], payload[ed.LOCAL], []))
                ed._load_lists_cached.clear()


if __name__ == '__main__':
    unittest.main(verbosity=2)
