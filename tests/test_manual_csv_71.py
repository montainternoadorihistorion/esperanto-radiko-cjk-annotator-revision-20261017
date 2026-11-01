"""Portable guards for the approved 71-row manual dictionary completion.

The fixture records each edition separately. Removing the added rows must
reproduce every original CSV byte, after reversing explicitly approved later
current assignments only. Fixed legacy bytes remain untouched.
"""
from pathlib import Path
import argparse, csv, gc, hashlib, html, importlib.util, io, json, logging, re
import sys, unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).with_name('manual_csv_71_completion.json')
FIXTURE_SHA = '0185a5567250a28591b783cf203fec7a73d996c3d924576e3eb02090486bcfce'
raw = FIXTURE.read_bytes()
if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA:
    raise ValueError('Reviewed manual CSV scope changed')
SCOPE = json.loads(raw)
ADDED = {r['root']: r for r in SCOPE['added_rows']}
REPORT = {'csv': [], 'manual': [], 'runtime': [], 'metadata': []}
FORMATS = {'pure':'替换后文字列のみ(仅)保留(简单替换)',
           'kanji':'HTML格式_Ruby文字_大小调整_汉字替换',
           'ruby':'HTML格式_Ruby文字_大小调整'}
logging.disable(logging.WARNING)

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def norm(value):
    for old, new in zip(('c^','g^','h^','j^','s^','u^','C^','G^','H^','J^','S^','U^'), 'ĉĝĥĵŝŭĈĜĤĴŜŬ'):
        value = value.replace(old, new)
    return value

def mapping(raw):
    rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    if not all(len(r) == 2 and r[0] and r[1] for r in rows):
        raise ValueError('Invalid CSV row')
    result = {norm(r[0]):r[1] for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate normalized root')
    return result


# Later explicitly approved current-edition changes are reversed only for the
# historical byte-preservation check; the frozen legacy is never normalized.
LATER_CURRENT_ASSIGNMENTS = {
    'ligatur': ('结扎', '结ᴸᵀ'),
    # 2026-11-01 adopted labels and their identifier-only collision owners.
    'karot': ("胡萝卜", "参ᴷ"),
    'panak': ("草ᴾᴺ", "参ᴾ"),
    'ginseng': ("草ᴳᴳ", "参ᴳ"),
    'karoten': ("萝卜素", "参ᴷ素"),
    'instig': ("唆", "促ᴵ"),
    'elegi': ("挽歌", "哀歌"),
    'delic': ("珍", "悦ᴰ"),
    'delekt': ("悦ᴰ", "悦ᴰᴷ"),
    'pense': ("草ᴾˢ", "草ᴾᴺ"),
    'psilofit': ("草ᴾᶠ", "草ᴾˢ"),
    'pasiflor': ("草ᴾᴬˢ", "草ᴾᶠ"),
    # 2026-11-02 approved display changes; no frozen legacy edits.
    'eŭfori': ("欣快", "快ᴱ"),
    'sofism': ("诡辩", "伪辩"),
}

def historical_current_bytes(raw):
    restored, seen = [], set()
    for line in raw.splitlines(keepends=True):
        body = line.rstrip(b'\r\n'); ending = line[len(body):]
        cells = next(csv.reader([body.decode('utf-8-sig')]))
        root = norm(cells[0])
        if root in LATER_CURRENT_ASSIGNMENTS:
            old, new = LATER_CURRENT_ASSIGNMENTS[root]
            if root in seen or body.decode('utf-8') != root + ',' + new:
                raise ValueError('Unexpected later assignment row: ' + root)
            seen.add(root)
            line = (root + ',' + old).encode('utf-8') + ending
        restored.append(line)
    if seen != set(LATER_CURRENT_ASSIGNMENTS):
        raise ValueError('Missing later approved current assignment')
    return b''.join(restored)

def strip_ruby(value):
    return re.sub(r'</?ruby>', '', re.sub(r'<rt[^>]*>.*?</rt>', '', value, flags=re.S))

def visible(value):
    return html.unescape(re.sub('<[^>]*>', '', strip_ruby(value))).replace('\xa0', ' ')

def original(value):
    value = re.sub(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', lambda m:m[2], value, flags=re.S)
    return html.unescape(re.sub('<[^>]*>', '', value)).replace('\xa0', ' ')

class ManualCsv71Tests(unittest.TestCase):
    def test_01_exact_append_language_consistency_and_legacy_authority(self):
        self.assertEqual(len(ADDED), 71)
        maps = {}
        for item in SCOPE['files']:
            raw = (ROOT/item['relative_path']).read_bytes()
            rows = mapping(raw)
            retained, appended = [], []
            for line in raw.splitlines(keepends=True):
                root = norm(next(csv.reader([line.decode('utf-8-sig')]))[0])
                (appended if root in ADDED else retained).append(line)
            retained_bytes = b''.join(retained)
            before = historical_current_bytes(retained_bytes) if item['edition'] == 'current' else retained_bytes
            self.assertEqual(len(before), item['before_bytes'])
            self.assertEqual(hashlib.sha256(before).hexdigest(), item['before_sha256'])
            self.assertTrue(raw.startswith(retained_bytes))
            self.assertEqual(len(appended), 71)
            self.assertEqual(len(rows), item['authority_rows'])
            self.assertEqual(mapping(b''.join(appended)), {r:v[item['edition']] for r,v in ADDED.items()})
            maps[item['edition'], item['lang']] = rows
            REPORT['csv'].append({'edition':item['edition'], 'language':item['lang'],
                                  'rows':len(rows), 'original_bytes_reconstructed':True,
                                  'later_approved_current_changes_reversed':list(LATER_CURRENT_ASSIGNMENTS) if item['edition']=='current' else []})
        for edition in ('current', 'legacy'):
            self.assertEqual(maps[edition,'JA'], maps[edition,'ZH'])
            self.assertEqual(maps[edition,'JA'], maps[edition,'KO'])
        legacy = ROOT/'assignment_editions/legacy'
        authority = {}
        for row in csv.reader(io.StringIO((legacy/'_kanji_map_master.tsv').read_text('utf-8-sig')), delimiter='\t'):
            if len(row) >= 3 and row[1] and row[2]:
                root = norm(row[1].strip())
                authority[root] = root if row[2] == '未対応' else row[2]
        for row in csv.DictReader(io.StringIO((legacy/'_identifier_sidecar.tsv').read_text('utf-8-sig')), delimiter='\t'):
            if row['disp'] != '未対応':
                authority[norm(row['root'])] = row['disp']
        self.assertEqual(maps['legacy','JA'], authority)
        for root in ('prioritat', 'spermatozo'):
            self.assertNotIn(root, authority)
        self.assertEqual({r for r,v in ADDED.items() if v['current'] != v['legacy']}, {'endoskopi','mikroskopi'})

    def test_02_every_added_root_manual_preview_variants_and_stored_decomposition(self):
        for lang in ('JA','ZH','KO'):
            app = ROOT/f'Esperanto-Kanji-Ruby-{lang}'
            ov = load(app/'esp_overlay_module.py', 'csv71_manual_'+lang)
            data = str(app/'app_data')
            prior = {}
            for edition in ('legacy','current'):
                for root, values in ADDED.items():
                    decomp = root+'/o'
                    segments = ov.segment_glosses(decomp, data, edition)
                    correction = ov.build_correction(decomp, data, edition)
                    self.assertEqual(visible(segments[0][2]), values[edition])
                    self.assertEqual(correction['decomp'], decomp)
                    self.assertEqual(correction['word'], root+'o')
                    for word, rendered in correction['kanji']:
                        self.assertEqual(original(rendered), word)
                        self.assertEqual(visible(rendered), values[edition] + ('O' if word.isupper() else 'o'))
                    if edition == 'legacy':
                        prior[root] = correction
                    else:
                        self.assertEqual(prior[root]['ruby'], correction['ruby'])
                    REPORT['manual'].append({'language':lang,'edition':edition,'root':root,**correction})
                # Session/backup entries are regenerated using the selected edition.
                stored = [{'word':'endoskopio','decomp':'endoskopi/o','kanji':[['endoskopio','OLD']]}]
                with patch.object(ov, 'load_corrections', return_value=stored):
                    entries = ov.load_overlay_entries(data, 'kanji', edition)
                self.assertEqual(dict((r[0],r[1]) for r in entries)['endoskopio'],
                                 ov.build_correction('endoskopi/o',data,edition)['kanji'][0][1])
                self.assertEqual(stored[0]['decomp'], 'endoskopi/o')

    def test_03_normal_at_annotations_and_custom_rules_keep_existing_behavior(self):
        expected = {(r['language'],r['edition'],r['mode'],r['input']):r['output']
                    for r in SCOPE['normal_expected']}
        inputs = SCOPE['normal_inputs']
        for lang in ('JA','ZH','KO'):
            app = ROOT/f'Esperanto-Kanji-Ruby-{lang}';data = app/'app_data'
            rt = load(app/'esp_text_replacement_module.py','csv71_rt_'+lang)
            ov = load(app/'esp_overlay_module.py','csv71_runtime_overlay_'+lang)
            ed = load(app/'esp_assignment_edition.py','csv71_ed_'+lang)
            ps = rt.import_placeholders(str(data/'placeholders_skip.txt'))
            pl = rt.import_placeholders(str(data/'placeholders_localcapture.txt'))
            for edition in ('current','legacy'):
                for mode, fmt in FORMATS.items():
                    gg, gl, g2 = ed.load_lists(data, mode, edition)
                    om = 'kanji' if mode == 'pure' else mode
                    overlay = ov.load_overlay_entries(str(data), om, edition)
                    if mode == 'pure': overlay = [[a,strip_ruby(b),c] for a,b,c in overlay]
                    gg = ov.merge_overlay(gg, overlay)
                    def render(text, rules):
                        return rt.orchestrate_comprehensive_esperanto_text_replacement(
                            text,ps,gl,pl,rules,g2,fmt,reviewed_local_decompositions=True)
                    parts = [x.strip() for x in render(' ◆ '.join(inputs),gg).split('◆')]
                    self.assertEqual(len(parts),len(inputs))
                    groups = {}
                    outputs = dict(zip(inputs,parts))
                    for word, value in zip(inputs,parts):
                        auto = ov.auto_overlay_entries(value,str(data),om,edition)
                        if mode == 'pure': auto = [[a,strip_ruby(b),c] for a,b,c in auto]
                        if auto: groups.setdefault(json.dumps(auto,ensure_ascii=False),[]).append(word)
                    for encoded, words in groups.items():
                        values = [x.strip() for x in render(' ◆ '.join(words),ov.merge_overlay(gg,json.loads(encoded))).split('◆')]
                        outputs.update(zip(words,values))
                    for word,value in outputs.items():
                        self.assertEqual(value,expected[lang,edition,mode,word],(lang,edition,mode,word))
                        REPORT['runtime'].append({'language':lang,'edition':edition,'mode':mode,'input':word,'output':value})
                    ed._load_lists_cached.clear();del gg,gl,g2;gc.collect()
            # Arbitrary uploaded tables retain their own mapping and local rules.
            out = rt.orchestrate_comprehensive_esperanto_text_replacement(
                'aerosolo @aerosol@o',ps,[['aerosol','LOCAL','@990000@']],pl,
                [['aerosolo','CUSTOM','$990000$']],[],FORMATS['pure'],reviewed_local_decompositions=False)
            self.assertEqual(out,'CUSTOM LOCALo')

    def test_04_cache_refresh_metadata_edition_mode_and_download_identity(self):
        for lang in ('JA','ZH','KO'):
            app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
            ed=load(app/'esp_assignment_edition.py','csv71_metadata_'+lang)
            ov=load(app/'esp_overlay_module.py','csv71_cache_'+lang)
            signatures={}
            with patch.object(ed.st,'session_state',{}):
                for edition in ('current','legacy'):
                    options={'mode':'kanji','format':FORMATS['kanji'],'letters':'circumflex'}
                    meta=ed.result_metadata(data,edition,render_options=options)
                    signatures[edition]=meta['signature']
                    self.assertTrue(ed.result_matches(meta,data,edition,render_options=options))
                    self.assertFalse(ed.result_matches(meta,data,'legacy' if edition=='current' else 'current',render_options=options))
                    self.assertFalse(ed.result_matches(meta,data,edition,render_options={**options,'mode':'ruby'}))
                    self.assertIn(edition,ed.download_filename('result',meta,'html'))
                    self.assertIn(meta['signature'],ed.html_download_metadata(meta))
                    # A stale pre-completion cache entry cannot conceal newly appended rows.
                    path=ed.resolve_path(data,'kanji_csv',edition)
                    widths=data/'char_widths.json';ws=widths.stat();stamp=path.stat()
                    key=(str(path.resolve()),ov.KANJI_FMT,edition)
                    ov._ROOT_DICT_CACHE[key]=((stamp.st_mtime_ns,stamp.st_size-1,ws.st_mtime_ns,ws.st_size),{})
                    refreshed=ov._build_root_dict(str(data),ov.KANJI_CSV,ov.KANJI_FMT,edition)
                    self.assertEqual(visible(refreshed['endoskopi']),ADDED['endoskopi'][edition])
                    REPORT['metadata'].append({'language':lang,'edition':edition,'signature':meta['signature'],'cache_refreshed':True})
                self.assertNotEqual(signatures['current'],signatures['legacy'])
                custom=ed.result_metadata(data,'current','custom-bytes',{'mode':'pure'})
                self.assertIsNone(custom['edition_id'])
                self.assertEqual(custom['source_id'],'custom_json')

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ManualCsv71Tests))
    if args.report:
        args.report.write_text(json.dumps({'passed':result.wasSuccessful(),'tests':result.testsRun,**REPORT},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
