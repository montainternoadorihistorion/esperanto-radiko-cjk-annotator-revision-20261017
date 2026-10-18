"""Independently verify actual Cloud files, then optionally export public evidence.

No application, README or Git edits. Incomplete measurements never receive passed=true.
Run after browser measurements: python reverse_verify_cloud_release.py
Export only after successful verification: add --public-dir PATH/tests/reverter_cloud
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,sys
from urllib.parse import urlsplit,urlunsplit

HOSTS={'JA':'esperanto-reverter-revision-ja-20261018.streamlit.app','ZH':'esperanto-reverter-revision-zh-20261018.streamlit.app'}
LABELS={'current':'新版（更新中）','legacy':'旧版（固定）'}
SOURCE_IDS={'current':'pejvo-piv-20260620','legacy':'pre-las-20261017'}
REQUIRED=['cloud_results.json','cloud_csv.json','cloud_guards.json','cloud_normal_results.json']
def private_pattern():
    # Construct path prefixes so this portable verifier contains no literal local path.
    return re.compile(r'(?i)[a-z]:[\\/][a-z_]|'+re.escape('/'+'Users'+'/')+'|'+re.escape('/'+'home'+'/')+r'[^/]+/|'+re.escape('file'+':'+'//'))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def filename_matches(actual,expected):
    if not isinstance(actual,str) or any(c in actual for c in '/\\'):return False
    p=Path(expected)
    return re.fullmatch(re.escape(p.stem)+r'(?: \([1-9][0-9]*\))?'+re.escape(p.suffix),actual) is not None
def safe_file(root,name):
    p=Path(name)
    if p.is_absolute():
        # Older raw browser records may name the actual download absolute path.
        return p
    p=(root/p).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('Relative evidence path escapes source directory')
    return p
def public_url(raw,language,normal=False):
    u=urlsplit(raw)
    assert u.scheme=='https' and u.hostname==HOSTS[language] and not u.username and not u.password,('unexpected Cloud host',raw)
    if normal:assert u.path in ('','/'),('not a normal public URL',raw)
    return urlunsplit((u.scheme,u.netloc,u.path,'',''))
def assert_unique(rows,key,name):
    keys=[key(r) for r in rows];assert len(keys)==len(set(keys)),name+' contains duplicate identities'
def verify_cache_reports(root):
    validation=read(root/'cache_fix_validation.json');invariants=read(root/'cache_fix_invariants.json')
    assert validation['status']=='PASS' and invariants['status']=='PASS'
    assert invariants['dictionary_or_tool_changes']==[] and invariants['unrelated_ast_changes']==[]
    assert invariants['public_private_entrypoint_and_test_bytes_equal'] is True
    assert sha((root/'cache_fix_invariants.json').read_bytes())==validation['invariant_report']['sha256']
    assert len(validation['full_suites'])==2
    for row in validation['full_suites']:
        assert row['passed']==154 and sha(safe_file(root,row['log']).read_bytes())==row['sha256']
    before=validation['before_reproduction']
    assert sha(safe_file(root,before['log']).read_bytes())==before['sha256']
    base=root.parents[1]
    private={'JA':'kanjized-esperanto-reverter/esperanto_converter.py','ZH':'hanzized-esperanto-reverter-zh_更新版20260822/esperanto_converter_zh.py'}
    public={'JA':'Esperanto-Reverter-JA/esperanto_converter.py','ZH':'Esperanto-Reverter-ZH/esperanto_converter_zh.py'}
    layout,paths=('public',public) if (base/public['JA']).is_file() else ('private',private)
    runtime=[]
    for language,relative in paths.items():
        p=base/relative
        if p.is_file():
            row=next(r for r in invariants['apps'] if r['label']==layout+'_'+language)
            assert sha(p.read_bytes())==row['entrypoint_sha256_after']
            runtime.append({'language':language,'path':relative,'sha256':sha(p.read_bytes())})
    return {'validation_sha256':sha((root/'cache_fix_validation.json').read_bytes()),'invariants_sha256':sha((root/'cache_fix_invariants.json').read_bytes()),'local_suites_passed_each':154,'historical_cloud_pending_note_preserved':True,'available_runtime_entrypoints_verified':runtime}
def validate(root):
    fixture=read(root/'reverse_cloud_fixture.json');assert fixture['passed']
    expected={r['case_id']:r for r in fixture['cases']};assert len(expected)==14
    assert_unique(fixture['cases'],lambda r:r['case_id'],'fixture')
    counts={k:sum(r['kind']==k for r in expected.values()) for k in ['paired_sentence','plain','raw_html_constraint','legacy_known_constraints']}
    assert counts=={'paired_sentence':4,'plain':4,'raw_html_constraint':4,'legacy_known_constraints':2}
    for r in expected.values():
        assert sha(r['expected_output'].encode())==r['expected_output_sha256']
        assert r['source_id']==SOURCE_IDS[r['edition']] and r['visible_label']==LABELS[r['edition']]
        if r['kind']=='paired_sentence':assert r['expected_output']==r['original_esperanto'].lower()
        if r['kind']=='raw_html_constraint':assert '<ruby>' in r['expected_output'] and '<rt>' in r['expected_output']
        if r['kind']=='legacy_known_constraints':assert r['expected_output']=='testikkatarᵀo orkidkatarᵀo\ntestikito orkidito' and r['roundtrip_exact'] is False
    paired=read(root/'reverse_paired_verification.json');assert paired['passed'] and paired['cases']==4
    assert len(paired['captures'])==4
    for row in paired['captures']:
        exp=expected[f"{row['language']}-{row['edition']}-paired_sentence"]
        assert row['original']==paired['same_original']==exp['original_esperanto']
        assert row['expected_original_lower']==row['original'].lower()==exp['expected_output']
        assert row['forward_output']==exp['input'] and row['restored']==exp['expected_output'] and row['roundtrip_exact'] is True
    downloads=read(root/'reverse_download_expectations.json');assert downloads['passed']
    exp_csv={(r['language'],r['edition'],r['kind']):r for r in downloads['records']};assert len(exp_csv)==8
    for r in exp_csv.values():
        raw=safe_file(root,r['file']).read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256']
        if r['edition']=='legacy':assert r['sha256']==({'full':'eed2a8bfc21a97b719e40b703ca356a6b9cd37e772811bd6d62203cfc00c4c14','two_column':'535ba2b65eb799ccbb6cc8400a705f23b06fe2e5207ccf3c3d460641d53d1a19'}[r['kind']])
    missing=[p for p in REQUIRED+['cache_fix_validation.json','cache_fix_invariants.json'] if not (root/p).is_file()]
    if missing:return {'status':'incomplete','missing_files':missing},None
    results=read(root/'cloud_results.json');csvs=read(root/'cloud_csv.json');guards=read(root/'cloud_guards.json');normal=read(root/'cloud_normal_results.json')
    assert all(isinstance(x,list) for x in [results,csvs,guards,normal])
    assert_unique(results,lambda r:r['case_id'],'cloud_results')
    assert_unique(csvs,lambda r:(r['language'],r['edition'],r['kind']),'cloud_csv')
    assert_unique(guards,lambda r:r['language'],'cloud_guards')
    assert_unique(normal,lambda r:r['case_id'],'cloud_normal_results')
    coverage={'cloud_results':len(results),'cloud_csv':len(csvs),'cloud_guards':len(guards),'cloud_normal_results':len(normal)}
    if coverage!={'cloud_results':14,'cloud_csv':8,'cloud_guards':2,'cloud_normal_results':4}:
        return {'status':'incomplete','coverage':coverage,'required_coverage':{'cloud_results':14,'cloud_csv':8,'cloud_guards':2,'cloud_normal_results':4}},None
    assert {r['case_id'] for r in results}==set(expected)
    assert {(r['language'],r['edition'],r['kind']) for r in csvs}==set(exp_csv)
    assert {r['language'] for r in guards}=={'JA','ZH'}
    assert {r['case_id'] for r in normal}=={k for k,v in expected.items() if v['kind']=='paired_sentence'}
    cache=verify_cache_reports(root)
    referenced=[];captions_independently_checked=0
    for row in results:
        exp=expected[row['case_id']]
        assert all(row[k]==exp[k] for k in ('language','edition','kind')),row['case_id']
        public_url(row['url'],row['language'])
        assert row['visible_output']==exp['expected_output'],('visible text differs',row['case_id'])
        raw=safe_file(root,row['local_path']).read_bytes()
        assert raw==exp['expected_output'].encode('utf-8'),('download full bytes differ',row['case_id'])
        assert sha(raw)==row['sha256']==exp['expected_output_sha256'] and len(raw)==row['bytes']
        assert filename_matches(row['filename'],exp['provenance']['result_filename']),('wrong version filename',row['case_id'])
        assert all(row[k] is True for k in ('visible_exact','download_exact','filename_exact','provenance_caption_exact'))
        if 'provenance_caption' in row:
            assert exp['provenance']['label'] in row['provenance_caption'];captions_independently_checked+=1
        referenced.append((row['local_path'],'cloud_outputs/'+row['case_id']+'.txt'))
    for row in csvs:
        exp=exp_csv[(row['language'],row['edition'],row['kind'])]
        public_url(row['url'],row['language'])
        raw=safe_file(root,row['local_path']).read_bytes();want=safe_file(root,exp['file']).read_bytes()
        assert raw==want,('CSV full bytes differ',row['language'],row['edition'],row['kind'])
        assert sha(raw)==row['sha256']==exp['sha256'] and len(raw)==row['bytes']==exp['bytes']
        assert filename_matches(row['filename'],exp['expected_download_filename']),('wrong CSV edition filename',row)
        assert all(row[k] is True for k in ('bytes_exact','sha_exact','filename_exact'))
        referenced.append((row['local_path'],'cloud_outputs/'+'-'.join((row['language'],row['edition'],row['kind']))+'.csv'))
    for row in normal:
        exp=expected[row['case_id']]
        assert row['language']==exp['language'] and row['edition']==exp['edition']
        public_url(row['url'],row['language'],normal=True)
        assert row['visible_output']==exp['expected_output'] and row['visible_exact'] is True and row['provenance_caption_exact'] is True
        if 'provenance_caption' in row:
            assert exp['provenance']['label'] in row['provenance_caption'];captions_independently_checked+=1
    for row in guards:
        assert row['from_edition']=='current' and row['to_edition']=='legacy'
        assert row['options']==[LABELS['current'],LABELS['legacy']] and row['selected_label']==LABELS['legacy']
        assert all(row[k] is True for k in ('download_disabled','old_caption_retained','reconvert_enabled'))
        if 'caption_before_switch' in row and 'caption_after_switch' in row:
            exp=next(r for r in expected.values() if r['language']==row['language'] and r['edition']=='current')
            assert exp['provenance']['label'] in row['caption_before_switch'] and exp['provenance']['label'] in row['caption_after_switch']
            captions_independently_checked+=1
    bundle={'results':results,'csvs':csvs,'guards':guards,'normal':normal,'fixture':fixture,'downloads':downloads,'referenced':referenced}
    report={'status':'passed','passed':True,'coverage':coverage,'case_kinds':counts,'successful_original_lower_roundtrips':4,'mixed_form_behavior_cases':4,'html_tags_preserved_constraint_cases':4,'known_legacy_failure_and_at_success_controls':2,'normal_public_url_paired_checks':4,'download_full_bytes_and_sha_verified':22,'filename_rule':'Expected edition/revision/hash filename; only a browser-added final (positive integer) suffix is accepted.','captions_independently_checked_from_text':captions_independently_checked,'ui_guard_observations':'Options and selection values verified. Disabled/reconvert states are browser observations supplied by the executing parent. Caption text is independently matched when recorded.','cache_fix_local_evidence':cache,'cache_fix_cloud_note':'cache_fix_validation.json records the earlier local-only stage, including its original pending Cloud note. The present report verifies the later actual Cloud observations.','universal_restoration_claimed':False,'fixture_sha256':sha((root/'reverse_cloud_fixture.json').read_bytes()),'download_expectations_sha256':sha((root/'reverse_download_expectations.json').read_bytes()),'inputs':[{'file':n,'sha256':sha((root/n).read_bytes())} for n in REQUIRED],'download_files':[{'source_record_path':src,'export_path':dest,'sha256':sha(safe_file(root,src).read_bytes())} for src,dest in referenced]}
    report['paired_roundtrip_comparison_rule']='Exact match against the same original Esperanto lowercased. Preservation of original capitalization is not claimed.'
    report['actual_forward_paired_evidence']={'file':'reverse_paired_verification.json','sha256':sha((root/'reverse_paired_verification.json').read_bytes()),'cases':4}
    context=root/'reverse_cloud_observation_context.json'
    if context.is_file():report['deployment_observation_context']=read(context)
    visual=root/'reverse_cloud_visual_review.json'
    if visual.is_file():
        review=read(visual)
        for row in review['screenshots']:assert sha(safe_file(root,row['file']).read_bytes())==row['sha256']
        report['visual_review']={'report':'reverse_cloud_visual_review.json','sha256':sha(visual.read_bytes()),'screenshots':len(review['screenshots'])}
    return report,bundle
def sanitize(row,allowed):return {k:v for k,v in row.items() if k in allowed}
def export(root,dest,report,bundle):
    assert report.get('passed') is True
    dest.mkdir(parents=True,exist_ok=True)
    for src,target in bundle['referenced']:
        p=dest/target;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(safe_file(root,src).read_bytes())
    for name in ['reverse_cloud_fixture.json','reverse_download_expectations.json']:
        (dest/name).write_bytes((root/name).read_bytes())
    paired=read(root/'reverse_paired_verification.json')
    paired['publication_note']={'comparison_rule':'restored == original.lower(); exact capitalization preservation is not claimed.','fixture_hash_at_capture':paired['fixture_sha256'],'final_cloud_fixture_sha256':sha((root/'reverse_cloud_fixture.json').read_bytes()),'source_paired_report_sha256':sha((root/'reverse_paired_verification.json').read_bytes())}
    save(dest/'reverse_paired_verification.json',paired)
    for name in ['reverse_paired_original.txt','reverse_paired_expected.txt']:
        (dest/name).write_bytes((root/name).read_bytes())
    for row in bundle['downloads']['records']:(dest/row['file']).write_bytes(safe_file(root,row['file']).read_bytes())
    common={'case_id','language','edition','kind','url','visible_output','visible_exact','download_exact','sha256','bytes','filename','filename_exact','provenance_caption_exact','provenance_caption','utc'}
    out=[]
    for row in bundle['results']:
        r=sanitize(row,common);r['url']=public_url(r['url'],r['language']);r['local_path']='cloud_outputs/'+r['case_id']+'.txt';out.append(r)
    save(dest/'cloud_results.json',out)
    out=[]
    for row in bundle['csvs']:
        r=sanitize(row,common|{'bytes_exact','sha_exact'});r['url']=public_url(r['url'],r['language']);r['local_path']='cloud_outputs/'+'-'.join((r['language'],r['edition'],r['kind']))+'.csv';out.append(r)
    save(dest/'cloud_csv.json',out)
    save(dest/'cloud_guards.json',[sanitize(r,{'language','from_edition','to_edition','options','selected_label','download_disabled','old_caption_retained','reconvert_enabled','caption_before_switch','caption_after_switch','utc'}) for r in bundle['guards']])
    save(dest/'cloud_normal_results.json',[{**sanitize(r,common),'url':public_url(r['url'],r['language'],normal=True)} for r in bundle['normal']])
    cache=read(root/'cache_fix_validation.json')
    (dest/'cache_fix_invariants.json').write_bytes((root/'cache_fix_invariants.json').read_bytes())
    for row in cache['full_suites']:
        raw=safe_file(root,row['log']).read_bytes()
        assert not private_pattern().search(raw.decode('utf-8')),'A passing-suite log contains a local path; keep it private and add a summary first.'
        (dest/row['log']).write_bytes(raw)
    before=cache['before_reproduction'];log=safe_file(root,before['log'])
    if log.is_file() and not private_pattern().search(log.read_text(encoding='utf-8')):
        (dest/before['log']).write_bytes(log.read_bytes())
    else:
        summary_name='cache_reproduction_before_summary.json'
        save(dest/summary_name,{'result':before['result'],'cause':cache['cause'],'private_log_name':before['log'],'private_log_sha256':before['sha256'],'raw_log_published':False,'reason':'The original traceback includes local filesystem paths. Its checksum and reproduction result are retained.'})
        cache['before_reproduction']={'result':before['result'],'original_private_log_name':before['log'],'original_private_log_sha256':before['sha256'],'log':summary_name,'sha256':sha((dest/summary_name).read_bytes()),'raw_log_published':False}
    cache['publication_note']={'source_validation_sha256':sha((root/'cache_fix_validation.json').read_bytes()),'historical_cloud_validation_note_unchanged':True,'later_cloud_verification':'reverse_cloud_release_verification.json'}
    save(dest/'cache_fix_validation.json',cache)
    if (root/'reverse_cloud_observation_context.json').is_file():
        (dest/'reverse_cloud_observation_context.json').write_bytes((root/'reverse_cloud_observation_context.json').read_bytes())
    if (root/'reverse_cloud_visual_review.json').is_file():
        visual=read(root/'reverse_cloud_visual_review.json')
        for row in visual['screenshots']:
            raw=safe_file(root,row['file']).read_bytes();assert sha(raw)==row['sha256']
            target=Path('screenshots')/Path(row['file']).name
            (dest/target).parent.mkdir(parents=True,exist_ok=True);(dest/target).write_bytes(raw)
            row['file']=target.as_posix()
        save(dest/'reverse_cloud_visual_review.json',visual)
    # Publish a portable verifier, not private preparation scripts or browser logs.
    (dest/'verify_cloud_evidence.py').write_bytes(Path(__file__).read_bytes())
    for p in dest.rglob('*'):
        if p.is_file() and p.suffix in ('.json','.py','.txt','.md','.csv','.log'):
            assert not private_pattern().search(p.read_text(encoding='utf-8-sig')),('private absolute path in export',p.name)
    exported_report,_=validate(dest);assert exported_report['passed']
    # Source browser paths are not carried into the public verification report.
    for r in exported_report['download_files']:r['source_record_path']=r['export_path']
    save(dest/'reverse_cloud_release_verification.json',exported_report)
    files=[{'path':p.relative_to(dest).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='evidence_manifest.json']
    save(dest/'evidence_manifest.json',{'passed':True,'public_absolute_local_paths_found':0,'files':files,'scope':'Observed Cloud exact-output behavior and CSV bytes. Four matching-edition roundtrips; mixed text, raw HTML and preserved old mismatches are separate cases.'})
    return {'directory_name':dest.name,'files':len(files),'manifest_sha256':sha((dest/'evidence_manifest.json').read_bytes())}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parent);parser.add_argument('--public-dir',type=Path);args=parser.parse_args()
    root=args.source.resolve()
    try:
        report,bundle=validate(root)
        if args.public_dir and report.get('passed') is True:report['public_export']=export(root,args.public_dir.resolve(),report,bundle)
    except Exception as exc:
        report={'status':'failed','passed':False,'error_type':type(exc).__name__,'error':str(exc)}
    save(root/'reverse_cloud_release_verification.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('inputs','download_files')},ensure_ascii=False))
    return 0 if report.get('passed') is True else 2 if report['status']=='incomplete' else 1
if __name__=='__main__':raise SystemExit(main())
