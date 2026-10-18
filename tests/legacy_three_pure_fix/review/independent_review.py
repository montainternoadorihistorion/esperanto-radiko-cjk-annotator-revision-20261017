"""Independent behavioral comparison with the shipped pre-fix helper.

Uses the real production engine, full tables and saved/automatic overlays.
Run each language separately to avoid identical module names sharing caches.
No app/data files are modified. Baseline 7f24a8d must exist in Git history.
"""
from pathlib import Path
import argparse, gc, hashlib, html, importlib.util, json, logging, re, subprocess, sys, tempfile, types

logging.disable(logging.WARNING)
ROOT = Path(__file__).resolve().parents[3]
BASELINE = '7f24a8ddb1ccea042e5c26a7ac7f19a95e3f2e0b'
FORMATS = {'pure': '替换后文字列のみ(仅)保留(简单替换)', 'kanji': 'HTML格式_Ruby文字_大小调整_汉字替换', 'ruby': 'HTML格式_Ruby文字_大小调整'}
WORDS = ('greganta', 'preganta', 'kordonita')
GLYPHS = ('群ᴳ在a', '压ᴾᴳ在a', 'kordonita')

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result

def strip_ruby(text):
    return re.sub(r'</?ruby>', '', re.sub(r'<rt[^>]*>.*?</rt>', '', text, flags=re.S|re.I), flags=re.I)

def contexts():
    approved = []
    untouched = []
    for word, glyph in zip(WORDS, GLYPHS):
        for template in ('{}', '({}),', '{}!', '{} {}', 'A: {};', '{}-{}'):
            approved.append((template.format(word, word), template.format(glyph, glyph)))
        untouched.extend((word.title(), word.upper(), word+'j', word+'n', word+'jn', 'x'+word,
                          word+'x', '3'+word, word+'3', 'ü'+word, '@'+word+'@', '%'+word+'%',
                          '%@'+word+'@%', '@'+word+'@x', 'x@'+word+'@', word+"'s", word+'’s'))
    untouched += ['g@dominant@a', 'p@dominant@a', 'k@komandit@a', 'dominanta', 'komandita',
                  'sene', '@sene@', 'kseno', '@kseno@', '%kseno%', 'ksenulo', 'semajno', '@semajno@',
                  'testikito', 'orkidita', '@orkidita@', 'spermatofitoj', 'lasis', '@lasis@',
                  '%丸ᵀ炎ᵀ 丸ᴼ炎ᵀ 气胶ˢ 精子ˢᶻ%', '%A < B & C > D%', 'gregant', 'pregant', 'kordonit',
                  'gregantaj', 'pregantaj', 'kordonitaj', 'gregantax', 'pregantax', 'kordonitax']
    return approved, untouched

def check(language, output):
    app = ROOT / f'Esperanto-Kanji-Ruby-{language}'
    data = app / 'app_data'
    sys.path.insert(0, str(app))
    import esp_text_replacement_module as engine
    import esp_assignment_edition as editions
    import esp_overlay_module as overlay
    before = types.ModuleType('old3_baseline_edition_'+language)
    before.__file__ = str(app / 'esp_assignment_edition.py')
    sys.modules[before.__name__] = before
    old_code = subprocess.check_output(['git', 'show', f'{BASELINE}:Esperanto-Kanji-Ruby-{language}/esp_assignment_edition.py'], cwd=ROOT).decode('utf8')
    exec(compile(old_code, before.__file__, 'exec'), before.__dict__)
    inverse = {}
    parsers = {}
    for il, filename in [('JA','esperanto_converter.py'), ('ZH','esperanto_converter_zh.py')]:
        im = module(ROOT / f'Esperanto-Reverter-{il}' / filename, 'old3_inv_'+il)
        parsers[il] = module(ROOT / f'Esperanto-Reverter-{il}' / 'html_source_recovery.py', 'old3_html_'+il)
        for edition, sid in [('current','pejvo-piv-20260620'), ('legacy','pre-las-20261017')]:
            inverse[edition,il] = (im, im.build_mapping_index_cached(im.effective_mapping_records(sid, im.load_dictionary_source(sid))))
    ps = engine.import_placeholders(str(data / 'placeholders_skip.txt'))
    pl = engine.import_placeholders(str(data / 'placeholders_localcapture.txt'))
    approved, untouched = contexts()
    source = '\n'.join([s for s,_ in approved] + untouched)
    rows = []; assertions = []
    corrections_hash = hashlib.sha256((data / 'user_corrections.json').read_bytes()).hexdigest()

    def render(text, lists, mode, edition, manual=None, parallel=False):
        gg, gl, g2 = lists
        om = 'kanji' if mode == 'pure' else mode
        stored = overlay.load_overlay_entries(str(data), om, edition)
        if mode == 'pure': stored = [[a,strip_ruby(b),c] for a,b,c in stored]
        gg = overlay.merge_overlay(gg,stored)
        if manual: gg = overlay.merge_overlay(gg,manual)
        def run(rules):
            args = (text, ps, gl, pl, rules, g2, FORMATS[mode])
            return engine.parallel_process(text, 2, *args[1:]) if parallel else engine.orchestrate_comprehensive_esperanto_text_replacement(*args)
        first = run(gg)
        auto = overlay.auto_overlay_entries(first, str(data), om, edition)
        if mode == 'pure': auto = [[a,strip_ruby(b),c] for a,b,c in auto]
        return run(overlay.merge_overlay(gg,auto)) if auto else first

    for edition in ('current','legacy'):
        for mode in ('pure','kanji','ruby'):
            original = before.load_lists(data,mode,edition)
            patched = editions.load_lists(data,mode,edition)
            assert original[1:] == patched[1:], (edition,mode,'local/two altered')
            prior = render(source,original,mode,edition)
            result = render(source,patched,mode,edition)
            row = {'edition':edition,'mode':mode,'inputs':len(approved)+len(untouched),
                   'before_sha256':hashlib.sha256(prior.encode()).hexdigest(),
                   'after_sha256':hashlib.sha256(result.encode()).hexdigest()}
            if (edition,mode) != ('legacy','pure'):
                assert result == prior, (edition,mode,'unexpected output change')
                assert patched == original, (edition,mode,'unexpected rule change')
                row['unchanged'] = True
            else:
                old_lines = prior.splitlines(); new_lines = result.splitlines()
                assert len(old_lines) == len(new_lines) == len(approved)+len(untouched)
                assert new_lines[:len(approved)] == [v for _,v in approved], new_lines[:len(approved)]
                assert new_lines[len(approved):] == old_lines[len(approved):], 'control changed'
                row['changed_inputs'] = [s for (s,_),a,b in zip(approved,old_lines,new_lines) if a!=b]
                for word,glyph in zip(WORDS,GLYPHS):
                    for il in ('JA','ZH'):
                        im, index = inverse[edition,il]
                        assert im.convert_kanji_esperanto_to_alphabet(glyph,index) == word
                row['target_inverse_checks'] = 6
            if mode!='pure':
                document = engine.apply_ruby_html_header_and_footer(result, FORMATS[mode])
                for il, parser in parsers.items():
                    original_document = engine.apply_ruby_html_header_and_footer(prior, FORMATS[mode])
                    recovered = parser.recover_standard_html(document,'annotation' if mode=='ruby' else 'kanji')['text']
                    expected = parser.recover_standard_html(original_document,'annotation' if mode=='ruby' else 'kanji')['text']
                    assert recovered == expected, (edition,mode,il)
                row['html_baseline_checks'] = 2
            else:
                for il in ('JA','ZH'):
                    im, index = inverse[edition,il]
                    old_inverse = im.convert_kanji_esperanto_to_alphabet(prior,index)
                    new_inverse = im.convert_kanji_esperanto_to_alphabet(result,index)
                    assert old_inverse.splitlines()[len(approved):] == new_inverse.splitlines()[len(approved):]
                row['inverse_control_checks'] = 2*len(untouched)
                parallel_text = '\n'.join(WORDS) + '\n%greganta% @preganta@\ng@dominant@a\nsene kseno'
                assert render(parallel_text,patched,mode,edition,parallel=True) == render(parallel_text,patched,mode,edition)
                row['parallel_matches'] = True
                manual = [[word,'MANUAL'+str(i),f'${9000500+i}$'] for i,word in enumerate(WORDS)]
                assert render(' '.join(WORDS),patched,mode,edition,manual=manual) == 'MANUAL0 MANUAL1 MANUAL2'
                row['manual_priority'] = True
                with tempfile.TemporaryDirectory() as td:
                    custom = Path(td)/'pure.json.gz'
                    import gzip
                    with gzip.open(custom,'wt',encoding='utf8') as f:
                        json.dump({editions.GLOBAL:[[w,'CUSTOM'+str(i),f'${8000050+i}$'] for i,w in enumerate(WORDS)],editions.LOCAL:[],editions.TWO:[]},f)
                    expected_custom = before.load_lists_path(custom)
                    actual_custom = editions.load_lists_path(custom)
                    assert expected_custom == actual_custom, 'custom loader changed'
                row['custom_loader_unchanged'] = True
            rows.append(row)
            print(language,edition,mode,'PASS',flush=True)
            del original, patched
            before._load_lists_cached.clear(); editions._load_lists_cached.clear(); gc.collect()
    assert hashlib.sha256((data/'user_corrections.json').read_bytes()).hexdigest() == corrections_hash
    report = {'passed':True,'language':language,'baseline':BASELINE,'source_sha256':hashlib.sha256((app/'esp_assignment_edition.py').read_bytes()).hexdigest(),
              'method':'Real production engine, saved and automatic overlays; comparison with Git baseline helper. No data writes.',
              'contexts':{'approved':[s for s,_ in approved],'controls':untouched},'rows':rows,'saved_corrections_unchanged':True}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--language',required=True); parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args(); check(args.language,args.report)
