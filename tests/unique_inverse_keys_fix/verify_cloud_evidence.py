"""Strict offline verification of browser observations and actual saved Cloud files.

This script does not operate a browser. Missing observations never count as a pass.
"""
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from collections import Counter
import argparse,copy,hashlib,json,re,shutil

HERE=Path(__file__).resolve().parent
BASE_FIXTURE_SHA='4dd8877c1acf30e9bae1d89751185c2fc6bf08ff0a3320f957e7fd2d3a4d48da'
PREFIX={'JA':'変換結果の版: ','ZH':'转换结果使用的版本: '}
CUSTOM_LABEL={'JA':'カスタム CSV','ZH':'自定义 CSV'}
LANGS=('JA','ZH');EDITION=('current','legacy')

def sha(value):return hashlib.sha256(value).hexdigest()
def read(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def local(base,value):
    p=Path(value)
    return p if p.is_absolute() else base/p

def download_name_matches(observed,expected):
    """Allow only Chrome's positive-integer duplicate suffix before extension."""
    if observed==expected:return True
    p=Path(expected)
    return isinstance(observed,str) and re.fullmatch(re.escape(p.stem)+r' \([1-9][0-9]*\)'+re.escape(p.suffix),observed) is not None

class Check:
    def __init__(self):self.errors=[];self.checks=0
    def require(self,condition,description):
        self.checks+=1
        if not condition:self.errors.append(description)
        return condition
    def unique(self,rows,key,expected,label):
        found={};duplicates=[]
        for r in rows:
            try:k=key(r)
            except (KeyError,TypeError):self.errors.append(label+': malformed key');continue
            if k in found:duplicates.append(k)
            found[k]=r
        self.require(not duplicates,label+': duplicate observations '+repr(duplicates))
        self.require(set(found)==set(expected),label+': coverage mismatch missing='+repr(sorted(set(expected)-set(found)))+' extra='+repr(sorted(set(found)-set(expected))))
        return found
    def observation(self,row,label):
        try:
            parsed=urlparse(row['url']);valid=parsed.scheme=='https' and parsed.hostname and parsed.hostname.endswith('.streamlit.app')
            self.require(valid,label+': URL is not an observed HTTPS Streamlit app')
            stamp=datetime.fromisoformat(row['utc'].replace('Z','+00:00'))
            self.require(stamp.tzinfo is not None,label+': timestamp must have timezone')
        except (KeyError,TypeError,ValueError):self.require(False,label+': missing or invalid URL/UTC')
    def file(self,base,row,field,expected,label):
        try:
            p=local(base,row[field]);raw=p.read_bytes()
        except (KeyError,TypeError,OSError) as exc:
            self.require(False,label+': saved file unavailable: '+str(exc));return None
        self.require(raw==expected,label+': saved bytes differ from full expectation')
        self.require(sha(raw)==sha(expected),label+': saved SHA256 differs')
        return {'path':row[field],'bytes':len(raw),'sha256':sha(raw)}

def validate(base,evidence_path=None):
    base=Path(base);check=Check()
    evidence_path=Path(evidence_path) if evidence_path else base/'cloud_evidence.json'
    required=('cloud_fixture.json','cloud_release_fixture.json','cloud_forward_combined.json','cloud_before.json')
    missing=[name for name in required if not (base/name).exists()]
    if not evidence_path.exists():missing.append(str(evidence_path))
    if missing:return {'completed':False,'passed':False,'status':'incomplete','missing_files':missing}
    original=read(base/'cloud_fixture.json');fixture=read(base/'cloud_release_fixture.json')
    combined=read(base/'cloud_forward_combined.json');before=read(base/'cloud_before.json');evidence=read(evidence_path)
    check.require(sha((base/'cloud_fixture.json').read_bytes())==BASE_FIXTURE_SHA,'original fixture bytes changed')
    check.require(fixture['base_fixture_sha256']==BASE_FIXTURE_SHA,'derived fixture does not identify fixed original')
    check.require(fixture['combined_forward_proof_sha256']==sha((base/'cloud_forward_combined.json').read_bytes()),'combined probe proof SHA mismatch')
    check.require(combined.get('passed') is True,'combined forward actual-runtime proof is not passed')
    check.require(fixture['downloads']==original['downloads'],'canonical/effective download expectations were changed in derived fixture')
    check.require(fixture['excluded_ambiguity_controls']==original['excluded_ambiguity_controls'],'known ambiguity controls were altered')
    expected_inverse={(r['language'],r['edition']):r for r in fixture['inverse_cases']}
    expected_original={(r['language'],r['edition']):r for r in original['inverse_cases']}
    expected_forward={(r['language'],r['edition']):r for r in fixture['forward_cases']}
    combined_rows=check.unique(combined.get('cases',[]),lambda r:(r['language'],r['edition']),expected_forward,'combined actual proof')
    check.require(len(fixture['inverse_cases'])==4 and set(expected_inverse)=={(l,e) for l in LANGS for e in EDITION},'release inverse fixture must contain exactly four cases')
    check.require(len(fixture['forward_cases'])==6 and set(expected_forward)=={(l,e) for l in (*LANGS,'KO') for e in EDITION},'release forward fixture must contain exactly six combined cases')
    for key,row in expected_inverse.items():
        initial=expected_original[key];forward=expected_forward[key]
        check.require(row['input']==initial['input']+'\n'+forward['expected_output'],str(key)+': inverse input is not exact old cases plus real forward body')
        check.require(row['expected_output']==initial['expected_output']+'\n'+forward['expected_restored'],str(key)+': inverse expectation is not exact old cases plus original sentence')
        check.require(row['provenance']==initial['provenance'],str(key)+': provenance changed while deriving release fixture')
        check.require(row['expected_output_sha256']==sha(row['expected_output'].encode('utf-8')),str(key)+': inverse expected hash invalid')
    for key,row in expected_forward.items():
        singles=[r for r in original['forward_cases'] if r['edition']==row['edition']]
        check.require(row['input']==' '.join(r['input'] for r in singles),str(key)+': combined original input mismatch')
        check.require(row['expected_output']==' '.join(r['expected_output'] for r in singles),str(key)+': combined output differs from independently checked singles')
        check.require(row['expected_restored']==' '.join(r['expected_restored'] for r in singles),str(key)+': combined restored expectation mismatch')
        check.require(row['expected_output_sha256']==sha(row['expected_output'].encode()),str(key)+': forward expected hash invalid')
        observed=combined_rows.get(key,{})
        check.require(observed.get('input')==row['input'] and observed.get('actual_output')==row['expected_output'],str(key)+': actual full-rule combined proof differs')
        check.require(observed.get('actual_restored')=={l:row['expected_restored'] for l in LANGS},str(key)+': combined proof does not actually restore via both inverse apps')
    expected_custom_fixture={r['language']:r for r in fixture['custom_upload_cases']}
    check.require(set(expected_custom_fixture)==set(LANGS),'custom fixture must cover exactly JA and ZH')
    for lang,row in expected_custom_fixture.items():
        exp=expected_inverse[(lang,'current')]
        check.require(row['upload_kind']=='current_effective' and row['input']==exp['input'] and row['expected_output']==exp['expected_output'],lang+': custom fixture does not replay the current effective dictionary case')

    expected_downloads={(r['language'],r['edition'],r['kind']):r for r in fixture['downloads']}
    expected_files={}
    for key,row in expected_downloads.items():
        raw=local(base,row['expected_file']).read_bytes();expected_files[key]=raw
        check.require(len(raw)==row['expected_bytes'] and sha(raw)==row['expected_sha256'],str(key)+': expected saved dictionary file is stale')
    inverse=check.unique(evidence.get('inverse',[]),lambda r:(r['language'],r['edition']),expected_inverse,'inverse')
    verified_inverse=[];hosts={}
    for key,row in inverse.items():
        if key not in expected_inverse:continue
        exp=expected_inverse[key];label='inverse '+repr(key);check.observation(row,label)
        check.require(row.get('case_id')==exp['case_id'],label+': incorrect case ID')
        check.require(row.get('input')==exp['input'],label+': input differs')
        check.require(row.get('output')==exp['expected_output'],label+': exact output differs')
        expected_caption=PREFIX[key[0]]+exp['provenance']['label']
        check.require(isinstance(row.get('captions'),list) and row['captions'].count(expected_caption)==1,label+': actual result provenance caption missing/duplicated')
        host=urlparse(row.get('url','')).hostname
        if key[0] in hosts:check.require(hosts[key[0]]==host,label+': editions came from different app hostnames')
        hosts[key[0]]=host
        verified_inverse.append({'case_id':row.get('case_id'),'language':key[0],'edition':key[1],'output_sha256':sha(str(row.get('output','')).encode()),'expected_caption':expected_caption,'known_collision_controls_retained_by_full_output':True})

    all_download_keys=set(expected_downloads)|{(l,e,'result') for l,e in expected_inverse}
    downloads=check.unique(evidence.get('downloads',[]),lambda r:(r['language'],r['edition'],r['kind']),all_download_keys,'downloads')
    verified_downloads=[]
    for key,row in downloads.items():
        if key not in all_download_keys:continue
        label='download '+repr(key);check.observation(row,label)
        check.require(bool(row.get('case_id')),label+': missing case ID')
        check.require(urlparse(row.get('url','')).hostname==hosts.get(key[0]),label+': app hostname disagrees with inverse observation')
        if key[2]=='result':
            exp=expected_inverse[key[:2]];expected=exp['expected_output'].encode('utf-8');filename=exp['provenance']['result_filename']
        else:expected=expected_files[key];filename=expected_downloads[key]['expected_filename']
        check.require(download_name_matches(row.get('filename'),filename),label+': downloaded filename/version differs')
        check.require(local(base,row.get('path','')).name==row.get('filename'),label+': filename is not the actual saved path basename')
        observed=check.file(base,row,'path',expected,label)
        if observed:verified_downloads.append({'language':key[0],'edition':key[1],'kind':key[2],**observed,'filename':row.get('filename'),'expected_filename':filename,'duplicate_suffix_only':row.get('filename')!=filename})

    forwards=check.unique(evidence.get('forward',[]),lambda r:(r['language'],r['edition']),expected_forward,'forward')
    verified_forward=[]
    for key,row in forwards.items():
        if key not in expected_forward:continue
        exp=expected_forward[key];label='forward '+repr(key);check.observation(row,label)
        check.require(row.get('case_id')==exp['case_id'],label+': incorrect case ID')
        check.require(row.get('input')==exp['input'],label+': input differs')
        check.require(row.get('visible')==exp['expected_output'],label+': visible raw output differs')
        if 'output' in row:check.require(row['output']==exp['expected_output'],label+': raw pure output differs')
        verified_forward.append({'case_id':row.get('case_id'),'language':key[0],'edition':key[1],'visible_sha256':sha(str(row.get('visible','')).encode())})

    expected_custom={r['language']:r for r in fixture['custom_upload_cases']}
    custom_check=Check();blocked_check=Check();fallback_check=Check()
    custom_rows=[r for r in evidence.get('custom',[]) if r.get('status')!='blocked']
    blocked_rows=evidence.get('custom_blocked',[])+[r for r in evidence.get('custom',[]) if r.get('status')=='blocked']
    blocked_languages={r.get('language') for r in blocked_rows}
    customs=custom_check.unique(custom_rows,lambda r:r['language'],set(expected_custom)-blocked_languages,'custom')
    verified_custom=[]
    for lang,row in customs.items():
        if lang not in expected_custom:continue
        exp=expected_custom[lang];label='custom '+lang;custom_check.observation(row,label)
        custom_check.require(row.get('upload_kind')=='current_effective',label+': wrong uploaded edition/kind')
        custom_check.require(row.get('input')==exp['input'] and row.get('output')==exp['expected_output'],label+': input or restored output differs')
        raw=expected_files[(lang,'current','effective')]
        saved=custom_check.file(base,row,'uploaded_path',raw,label)
        caption=PREFIX[lang]+CUSTOM_LABEL[lang]+' / uploaded / '+sha(raw)[:12]
        custom_check.require(isinstance(row.get('captions'),list) and row['captions'].count(caption)==1,label+': custom provenance caption missing or stale')
        custom_check.require(urlparse(row.get('url','')).hostname==hosts.get(lang),label+': app hostname disagrees')
        if saved:verified_custom.append({'language':lang,'uploaded_file':saved,'expected_caption':caption,'output_sha256':sha(str(row.get('output','')).encode())})

    blocked={};fallback_summary=None
    if blocked_rows:
        blocked=blocked_check.unique(blocked_rows,lambda r:r['language'],set(expected_custom)-set(customs),'custom blocked')
        blocked_check.require(any(r.get('attempted') is True for r in blocked_rows),'no actual failed browser upload attempt is recorded')
        for lang,row in blocked.items():
            blocked_check.observation(row,'custom blocked '+lang)
            blocked_check.require(row.get('status')=='blocked' and isinstance(row.get('attempted'),bool),'blocked upload status/attempt marker missing')
            blocked_check.require(bool(row.get('reason')) and 'Allow access to file URLs' in row.get('error',''),'actual file URL permission rejection is not recorded')
            blocked_check.require(urlparse(row.get('url','')).hostname==hosts.get(lang),'blocked upload app hostname differs')
        fallback_path=base/'cloud_custom_local_fallback.json'
        if fallback_check.require(fallback_path.exists(),'local reimport fallback evidence missing'):
            fallback=read(fallback_path)
            fallback_check.require(fallback.get('passed') is True and fallback.get('not_a_cloud_upload_test') is True and fallback.get('cloud_upload_verified') is False,'fallback must explicitly be local and not a passed Cloud upload')
            fallback_check.require(fallback.get('fixture_sha256')==sha((base/'cloud_release_fixture.json').read_bytes()),'local fallback fixture hash differs')
            local_cases=fallback_check.unique(fallback.get('cases',[]),lambda r:(r['language'],r['edition']),expected_inverse,'local fallback')
            for key,row in local_cases.items():
                if key not in expected_inverse:continue
                exp=expected_inverse[key];expected_file=expected_downloads[(*key,'effective')]
                actual_download=downloads.get((*key,'effective'),{})
                fallback_check.require(row.get('input')==exp['input'] and row.get('actual_output')==exp['expected_output'] and row.get('expected_output')==exp['expected_output'],str(key)+': local fallback full output differs')
                fallback_check.require(row.get('downloaded_sha256')==expected_file['expected_sha256'] and row.get('downloaded_bytes')==expected_file['expected_bytes'],str(key)+': local fallback did not import the expected downloaded bytes')
                fallback_check.require(row.get('downloaded_filename')==actual_download.get('filename') and row.get('download_case_id')==actual_download.get('case_id'),str(key)+': local fallback is not linked to the actual observed download')
                fallback_check.require(row.get('entire_mapping_matches_selected_ui_dictionary') is True and row.get('automatic_alias_injection_into_custom') is False,str(key)+': full mapping/custom isolation check missing')
                fallback_check.require(row.get('custom_provenance',{}).get('dictionary_sha256')==expected_file['expected_sha256'],str(key)+': local custom provenance has wrong file hash')
            source_expected={r['path']:r['sha256'] for r in combined['source_files'] if r['path'].endswith(('esperanto_converter.py','esperanto_converter_zh.py'))}
            fallback_check.require({r['path']:r['sha256'] for r in fallback.get('source_files',[])}==source_expected,'local fallback production source hashes differ from verified source')
            script=base/'verify_downloaded_custom_local.py'
            fallback_check.require(script.exists() and fallback.get('script_sha256')==sha(script.read_bytes()),'local fallback verifier source hash differs')
            fallback_summary={'passed':not fallback_check.errors,'file':'cloud_custom_local_fallback.json','sha256':sha(fallback_path.read_bytes()),'cases':len(local_cases),'cloud_upload_verified':False}

    expected_guards={(l,k) for l in LANGS for k in ('edition_switch','deployment_update')}
    guards=check.unique(evidence.get('guards',[]),lambda r:(r['language'],r['kind']),expected_guards,'guards')
    verified_guards=[]
    base_old_caption=before['captions'][0]
    check.require(base_old_caption.startswith(PREFIX['JA']),'predeployment reference caption malformed')
    for key,row in guards.items():
        if key not in expected_guards:continue
        lang,kind=key;label='guard '+repr(key);check.observation(row,label)
        if kind=='edition_switch':
            exp=expected_inverse[(lang,'current')];old_caption=PREFIX[lang]+exp['provenance']['label'];old_output=exp['expected_output']
            if 'from_edition' in row:check.require(row['from_edition']=='current',label+': wrong from edition')
            if 'to_edition' in row:check.require(row['to_edition']=='legacy',label+': wrong to edition')
        else:
            old_caption=PREFIX[lang]+base_old_caption[len(PREFIX['JA']):];old_output=before['output']
        check.require(row.get('old_caption')==old_caption,label+': generated-result caption not retained')
        check.require(row.get('output')==old_output,label+': old generated result not retained')
        check.require(row.get('download_disabled') is True,label+': stale result download not disabled')
        if 'expected_current_revision' in row:
            check.require(row['expected_current_revision']==expected_inverse[(lang,'current')]['provenance']['inverse_compatibility_revision'],label+': unexpected deployed revision')
        check.require(urlparse(row.get('url','')).hostname==hosts.get(lang),label+': app hostname disagrees')
        verified_guards.append({'language':lang,'kind':kind,'retained_caption':old_caption,'retained_output_sha256':sha(old_output.encode()),'download_disabled':row.get('download_disabled')})

    before_rows=evidence.get('before',[])
    check.require(bool(before_rows),'predeployment observation missing from evidence')
    for row in before_rows:
        lang=row.get('language','JA');check.observation(row,'before '+lang)
        check.require(lang in LANGS,'predeployment observation language invalid')
        check.require(row.get('input')==before['input'] and row.get('output')==before['output'],'predeployment observation differs from saved reference')
        if lang in LANGS:
            caption=PREFIX[lang]+base_old_caption[len(PREFIX['JA']):]
            check.require(caption in row.get('captions',[]),'predeployment result caption not confirmed')
    core_completed=set(inverse)==set(expected_inverse) and set(downloads)==all_download_keys and set(forwards)==set(expected_forward) and set(guards)==expected_guards and bool(before_rows)
    core_passed=core_completed and not check.errors
    cloud_custom_completed=set(customs)==set(expected_custom) and not blocked_rows
    cloud_custom_passed=cloud_custom_completed and not custom_check.errors
    all_passed=core_passed and cloud_custom_passed
    blocked_documented=bool(blocked_rows) and not blocked_check.errors and not custom_check.errors
    local_fallback_passed=bool(fallback_summary) and not fallback_check.errors
    package_allowed=all_passed or (core_passed and blocked_documented and local_fallback_passed)
    errors=check.errors+custom_check.errors+blocked_check.errors+fallback_check.errors
    return {'completed':core_completed and cloud_custom_completed,'passed':all_passed,'core_completed':core_completed,'core_passed':core_passed,'cloud_custom_completed':cloud_custom_completed,'cloud_custom_passed':cloud_custom_passed,'all_requested_checks_passed':all_passed,'evidence_package_allowed':package_allowed,'status':'PASS' if all_passed else 'CORE_PASS_CUSTOM_BLOCKED' if package_allowed else 'FAIL','checks':check.checks+custom_check.checks+blocked_check.checks+fallback_check.checks,'errors':errors,
            'coverage':{'inverse':len(inverse),'dictionary_downloads':sum(k[2]!='result' for k in downloads),'result_downloads':sum(k[2]=='result' for k in downloads),'forward':len(forwards),'guards':len(guards),'custom':len(customs),'before':len(before_rows)},
            'inverse':verified_inverse,'downloads':verified_downloads,'forward':verified_forward,'guards':verified_guards,'custom':verified_custom,'custom_blocked':list(blocked.values()),'custom_local_fallback':fallback_summary,
            'fixture_sha256':sha((base/'cloud_release_fixture.json').read_bytes()),'evidence_sha256':sha(evidence_path.read_bytes()),'validator_sha256':sha(Path(__file__).read_bytes()),
            'scope':'Exact browser-observed outputs, provenance captions, actual saved dictionary/result file bytes, six combined normal/@ forward samples, custom upload and stale-result guards. Known ambiguous outputs are required unchanged. This does not claim arbitrary text has a unique inverse or identify the internal Cloud deployed commit.'}

def package(base,destination):
    base=Path(base);destination=Path(destination);report=validate(base)
    if not report.get('evidence_package_allowed'):raise ValueError('Cannot publish unverified core observations or undocumented fallback')
    destination.mkdir(parents=True,exist_ok=True)
    evidence=copy.deepcopy(read(base/'cloud_evidence.json'))
    for section,field in [('downloads','path'),('custom','uploaded_path')]:
        for i,row in enumerate(evidence[section]):
            src=local(base,row[field])
            rel=Path('cloud_actual')/section/str(i).zfill(2)/src.name
            (destination/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,destination/rel);row[field]=rel.as_posix()
    for name in ('cloud_fixture.json','cloud_release_fixture.json','cloud_forward_combined.json','cloud_before.json'):
        shutil.copyfile(base/name,destination/name)
    for name in ('implementation_scope_final.json','build_cloud_release_fixture.py','cloud_validator_unit_tests.json','cloud_custom_local_fallback.json','verify_downloaded_custom_local.py'):
        if (base/name).exists():shutil.copyfile(base/name,destination/name)
    fixture=read(base/'cloud_release_fixture.json')
    for row in fixture['downloads']:
        rel=Path(row['expected_file']);assert not rel.is_absolute() and '..' not in rel.parts
        (destination/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/rel,destination/rel)
    shutil.copyfile(Path(__file__),destination/'verify_cloud_evidence.py')
    if (base/'test_cloud_evidence_validator.py').exists():
        shutil.copyfile(base/'test_cloud_evidence_validator.py',destination/'test_cloud_evidence_validator.py')
    save(destination/'cloud_evidence.json',evidence)
    public=validate(destination);assert public['evidence_package_allowed'],public['errors']
    save(destination/'cloud_verification.json',public)
    # Captured metadata may contain paths only in fields explicitly copied above.
    for name in ('cloud_evidence.json','cloud_release_fixture.json','cloud_forward_combined.json','cloud_verification.json','implementation_scope_final.json','cloud_custom_local_fallback.json'):
        if not (destination/name).exists():continue
        raw=(destination/name).read_text(encoding='utf-8')
        assert not re.search(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]',raw),('Local absolute path in public evidence',name)
    return public

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,default=HERE);ap.add_argument('--evidence',type=Path);ap.add_argument('--package-dir',type=Path);a=ap.parse_args()
    result=validate(a.base,a.evidence);save(a.base/'cloud_verification.json',result)
    print(json.dumps({k:result.get(k) for k in ('completed','passed','core_passed','cloud_custom_completed','all_requested_checks_passed','evidence_package_allowed','status','coverage','errors','missing_files')},ensure_ascii=False))
    if not result.get('evidence_package_allowed'):raise SystemExit(1)
    if a.package_dir:package(a.base,a.package_dir)

if __name__=='__main__':main()
