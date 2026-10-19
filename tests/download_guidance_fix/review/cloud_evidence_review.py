"""Read-only verification of saved Cloud downloads and captured page records."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import argparse, ast, hashlib, json, re, sys

ROOT=Path(__file__).resolve().parents[3]
REPO='montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017'
ROLES=('kanji_csv','ruby_csv','decomposition','word_annotations','stem','bundled_corrections','manual_backup')

def sha(raw): return hashlib.sha256(raw).hexdigest()
def normalized(text): return ' '.join(text.replace('**','').split())
def records(path):
    value=json.loads(path.read_text(encoding='utf8'))
    if isinstance(value,list): return value
    for key in ('records','rows','files','pages','manual'):
        if isinstance(value.get(key),list): return value[key]
    raise AssertionError('Unknown record wrapper: '+str(path))

def verify(directory,files_only=False):
    files=records(directory/'file_records.json')
    pages=records(directory/'page_records.json')
    manual=records(directory/'manual_records.json')
    navigation=json.loads((directory/'navigation_records.json').read_text(encoding='utf8'))
    assert len(files)==42,len(files)
    assert Counter(r['role'] for r in files)=={role:6 for role in ROLES}
    assert len({r['filename'] for r in files})==42
    assert len(pages)>=6,len(pages)
    # Keep earlier capture evidence; the last record for each state is the settled recapture.
    page_map={(r['language'],r['edition']):r for r in pages}
    page_indices={(r['language'],r['edition']):index for index,r in enumerate(pages)}
    assert len(page_map)==6
    sys.path.insert(0,str(ROOT/'Esperanto-Kanji-Ruby-JA'))
    import esp_assignment_edition as ed
    import esp_overlay_module as ov
    def selection_matches(value,language,edition):
        text=json.dumps(value,ensure_ascii=False)
        return value==edition or ed.LABELS[language][edition] in text
    file_checks=[];page_checks=[]
    for (lang,edition),page in ([] if files_only else page_map.items()):
        app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
        source=next((app/'pages').glob('2_*.py')).read_text(encoding='utf8')
        tree=ast.parse(source)
        guidance=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GUIDANCE' for t in n.targets))
        guidance=ast.literal_eval(guidance.value)[lang]
        assert selection_matches(page['selected'],lang,edition),(lang,edition,page['selected'])
        visible=normalized(page['bodyText'])
        for key in ('raw','steps','legacy','custom','bundled_note','source_note'):
            assert normalized(guidance[key]) in visible,(lang,edition,key)
        links=page['links'];urls=[r['href'] for r in links]
        commits=[u.rsplit('/',1)[1] for u in urls if u.startswith('https://github.com/'+REPO+'/tree/')]
        assert len(commits)==1 and re.fullmatch('[0-9a-f]{40}',commits[0]),commits
        commit=commits[0]
        assert 'https://github.com/'+REPO+'/archive/'+commit+'.zip' in urls
        for role in ('kanji','pure','ruby'):
            path=ed.resolve_path(data,role,edition)
            expected='https://raw.githubusercontent.com/'+REPO+'/'+commit+'/'+path.relative_to(ROOT).as_posix()
            assert expected in [unquote(url) for url in urls],(lang,edition,role)
        assert guidance['manual_link'] in page['bodyText']
        page_checks.append({'language':lang,'edition':edition,'record_index_zero_based':page_indices[lang,edition],
                            'source_commit':commit,'localized_guidance_present':True,
                            'selected_data_urls_present':3,'source_zip_urls_consistent':True,'selection_matches':True})
    for row in files:
        lang=row['language'];edition=row['edition'];role=row['role'];page=page_map[lang,edition]
        assert selection_matches(row['selected_after_download'],lang,edition),(lang,edition,role,row['selected_after_download'])
        path=directory/row['filename'];raw=path.read_bytes()
        assert path.resolve().parent==directory.resolve()
        assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],row['filename']
        data=ROOT/f'Esperanto-Kanji-Ruby-{lang}'/'app_data'
        # Chrome adds a collision suffix when that name already exists in Downloads.
        actual_download_name=row['downloadBasename']
        download_name=re.sub(r' \(\d+\)(?=\.[^.]+$)','',actual_download_name)
        def result_signature(session):
            corrections=sha(json.dumps(session,ensure_ascii=False,sort_keys=True).encode('utf8'))
            return sha(json.dumps([ed.edition_signature(data,edition),corrections,None,None],sort_keys=True).encode('utf8'))
        if role=='manual_backup':
            parsed=json.loads(raw)
            expected=[dict(ov.build_correction('las/is',str(data),edition),assignment_edition=edition,
                           assignment_signature=ed.edition_signature(data,edition))]
            assert parsed==expected,(lang,edition,'manual payload')
            assert raw==json.dumps(expected,ensure_ascii=False,indent=1).encode('utf8')
            session=[{'word':'lasis','decomp':'las/is','_disabled':None}]
            signature=result_signature(session)
            assert download_name==f'user_corrections_{edition}_{signature[:12]}.json',download_name
            assert ('放' if edition=='current' else '留') in parsed[0]['kanji'][0][1]
            baseline=data/'user_corrections.json'
            assert raw!=baseline.read_bytes()
            detail={'edition_metadata_matches':True,'selected_glyph_matches':True,'different_from_bundled_baseline':True}
        else:
            asset=ed.resolve_path(data,role,edition) if role in ('kanji_csv','ruby_csv') else data/{'decomposition':'分解設定.json','word_annotations':'word_anno.json','stem':'E_stem.json','bundled_corrections':'user_corrections.json'}[role]
            assert raw==asset.read_bytes(),(lang,edition,role)
            if role=='kanji_csv':
                # Captured download pages precede or follow the single manual addition.
                # The bytes are unchanged; the existing name also fingerprints session state.
                known_sessions=([],[{'word':'lasis','decomp':'las/is','_disabled':None}])
                names={f'kanji_assignments_{edition}_{result_signature(s)[:12]}.csv' for s in known_sessions}
                assert download_name in names,(download_name,names)
            else:
                assert download_name==asset.name,(download_name,asset.name)
            detail={'selected_asset':asset.relative_to(ROOT).as_posix(),'matches_original_asset':True}
        file_checks.append({'language':lang,'edition':edition,'role':role,'file':row['filename'],
                            'download_name':actual_download_name,'application_filename':download_name,
                            'browser_collision_suffix_removed':actual_download_name!=download_name,
                            'bytes':len(raw),'sha256':sha(raw),**detail})
    assert len({(r['language'],r['edition']) for r in manual})==6
    manual_checks=[]
    for row in manual:
        lang=row['language'];edition=row['edition']
        assert selection_matches(row['selected'],lang,edition)
        body=normalized(row['bodyText'])
        assert 'las/is' in body and 'lasis' in body
        assert ('放' if edition=='current' else '留') in body
        path=next((ROOT/f'Esperanto-Kanji-Ruby-{lang}'/'pages').glob('1_*.py'))
        tree=ast.parse(path.read_text(encoding='utf8'))
        download_call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='download_button')
        label=ast.literal_eval(download_call.args[0])
        assert normalized(label) in body
        nav_call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='page_link')
        nav_label=ast.literal_eval(next(k.value for k in nav_call.keywords if k.arg=='label'))
        assert normalized(nav_label) in body
        manual_checks.append({'language':lang,'edition':edition,'selected_edition_and_glyph_present':True,
                              'saved_decomposition_present':True,'backup_label_and_data_navigation_present':True})
    assert set(navigation)=={'JA','ZH','KO'}
    for lang,row in navigation.items():
        assert selection_matches(row['selected'],lang,'current') and row['saved_entry'] is True
    result={'passed':True,'issues':[],'download_files_rehashed':42,'small_original_assets_byte_equal':36,
      'manual_session_backups_byte_equal':6,'page_states_verified':len(page_checks),'page_capture_records':len(pages),'recorded_manual_states':len(manual),
      'recorded_navigation_retention_checks':3,
      'record_file_sha256':{name:sha((directory/name).read_bytes()) for name in ('file_records.json','page_records.json','manual_records.json','navigation_records.json')},
      'files':file_checks,'pages':page_checks,'manual':manual_checks,
      'method':'Independent read of saved browser downloads and recorded manual state; compare all raw bytes, filenames, edition labels and metadata with production data. Manual backups must equal a newly built single las/is correction and differ from the bundled baseline. '+('Download-page records are deferred in this files-only result. ' if files_only else 'Page descriptions and fixed source/data link paths are checked from the latest captured text/links for each language/edition; earlier transient captures remain in the source records. ')+'No browser operation or HTTP/ZIP verification performed by this reviewer.'}
    output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    report_name='cloud_files_review.json' if files_only else 'cloud_evidence_review.json'
    (Path(__file__).parent/report_name).write_text(output,encoding='utf8')
    (directory.parent/'review'/report_name).write_text(output,encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','pages','manual','method')},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--files-only',action='store_true');args=parser.parse_args()
    verify(args.directory,args.files_only)
