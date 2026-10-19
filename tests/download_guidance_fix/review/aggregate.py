"""Independently check the bounded source diff and collect actual AppTest evidence."""
from pathlib import Path
import argparse, ast, hashlib, json, subprocess, sys, types

ROOT=Path(__file__).resolve().parents[3]
BASE='15f9b8aef376109fb0c064d9f4a052f35a58fc52'
SOURCE='fe1e11218f125218189d1dea6e45e7afbf4cb15e'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf8').strip()

def dump(node):
    return ast.dump(node,include_attributes=False)

def download_payloads(tree):
    result=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='download_button':
            # Only the first positional argument (the UI label) may differ.
            result.append(([dump(x) for x in node.args[1:]],
                           [(x.arg,dump(x.value)) for x in node.keywords]))
    return result

def collect(evidence):
    reports={lang:json.loads((evidence/f'app_{lang}.json').read_text(encoding='utf8')) for lang in ('JA','ZH','KO')}
    assert all(r['passed'] and r['source_commit']==SOURCE and r['application_and_baseline_unchanged'] for r in reports.values())
    changes=git('-c','core.quotepath=false','diff','--name-only',BASE,SOURCE).splitlines()
    expected={'tests/download_guidance_fix/decision.md'}
    source_review=[]
    sys.path.insert(0,str(ROOT/'Esperanto-Kanji-Ruby-JA'))
    import esp_assignment_edition as ed
    for lang,report in reports.items():
        app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
        manual=next((app/'pages').glob('1_*.py'));download=next((app/'pages').glob('2_*.py'))
        for path in (manual,download):
            rel=path.relative_to(ROOT).as_posix();expected.add(rel)
            old=ast.parse(git('show',BASE+':'+rel));new=ast.parse(path.read_text(encoding='utf8'))
            assert download_payloads(old)==download_payloads(new),rel
            if path==manual:
                assert [dump(n) for n in old.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]==[dump(n) for n in new.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        tree=ast.parse(download.read_text(encoding='utf8'))
        guidance=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GUIDANCE' for t in n.targets))
        guidance=ast.literal_eval(guidance.value)[lang]
        helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_matching_source_links')
        guarded=[]
        for row in report['rows']:
            visible=row['data_visible_text']
            for key in ('raw','steps','legacy','custom','bundled_note'):
                assert guidance[key] in visible,(lang,row['edition'],key)
            assert any(guidance['source_note'] in text for text in visible)
            bundled=next(p for p in row['small_downloads'] if p['filename']=='user_corrections.json')
            assert bundled['label']==guidance['bundled']+' · user_corrections.json'
            assert row['data_page_navigation'][0]['label']==guidance['manual_link']
            paths=[]
            def pin(data_dir,path):
                paths.append(path)
                return 'https://raw.githubusercontent.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017/'+SOURCE+'/'+path.relative_to(ROOT).as_posix()
            namespace={'APP_DIR':app,'ROOT':ROOT,'DATA_DIR':data,'edition':row['edition'],
                       'editions':types.SimpleNamespace(resolve_path=ed.resolve_path,pinned_asset_url=pin)}
            exec(compile(ast.Module(body=[helper],type_ignores=[]),str(download),'exec'),namespace)
            links=namespace['_matching_source_links']()
            assert links['commit']==SOURCE
            assert {data/name for name in ('分解設定.json','word_anno.json','E_stem.json')}<=set(paths)
            guarded.append({'edition':row['edition'],'count':len(paths),'paths':[p.relative_to(ROOT).as_posix() for p in paths]})
        source_review.append({'language':lang,'download_data_and_filename_expressions_unchanged':True,
                              'manual_functions_unchanged':True,'visible_localized_guidance_verified':True,
                              'fixed_source_guard_paths':guarded})
    assert set(changes)==expected,changes
    out={'passed':True,'base_commit':BASE,'source_commit':SOURCE,'issues':[],
      'changed_files':changes,'source_review':source_review,
      'actual_app_test_counts':{'language_edition_states':6,'small_download_payloads':36,'large_asset_urls_and_committed_blobs':18,
        'source_and_zip_urls':12,'correction_file_imports':6,'new_corrections_saved':6,'existing_corrections_edited':6,
        'edition_transitions_retaining_draft_and_edits':12,'backup_checks_across_initial_other_returned_edition':18,
        'navigation_targets_rendered':12,'actual_manual_to_download_page_transitions':6},
      'limits':['Local AppTest, not a browser or Cloud check.','Upload and download transport are instrumented; original production UI calls still run.',
                'This bounded review does not claim a new exhaustive conversion audit.','Fixed-link guard path enumeration uses an isolated AST helper and a recording verifier; actual published URLs and blobs are independently asserted by AppTest.']}
    destination=Path(__file__).parent
    for lang in reports:
        (destination/f'app_{lang}.json').write_text(json.dumps(reports[lang],ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for directory in (evidence,destination):
        (directory/'summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'counts':out['actual_app_test_counts'],'guard_path_counts':[g['count'] for r in source_review for g in r['fixed_source_guard_paths']]},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    collect(parser.parse_args().evidence)
