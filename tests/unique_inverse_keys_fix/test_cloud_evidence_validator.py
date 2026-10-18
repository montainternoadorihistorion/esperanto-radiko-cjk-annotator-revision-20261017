"""Synthetic validator tests; these are not observations of Cloud behavior."""
from pathlib import Path
import copy,hashlib,importlib.util,json,shutil,tempfile,unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('unique_cloud_validator',HERE/'verify_cloud_evidence.py')
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)

def synthetic(base):
    fixture=validator.read(base/'cloud_release_fixture.json');before=validator.read(base/'cloud_before.json')
    stamp='2026-10-18T12:00:00+00:00'
    url=lambda lang:f'https://example-reverter-{lang.lower()}.streamlit.app/'
    out={'before':[dict(before,language='JA')],'inverse':[],'downloads':[],'forward':[],'guards':[],'custom':[],'synthetic_validator_test_only':True}
    for r in fixture['inverse_cases']:
        lang,ed=r['language'],r['edition'];case=r['case_id']
        out['inverse'].append({'case_id':case,'language':lang,'edition':ed,'input':r['input'],'output':r['expected_output'],'captions':[validator.PREFIX[lang]+r['provenance']['label']],'url':url(lang),'utc':stamp})
        path=base/(case+'_result')/r['provenance']['result_filename'];path.parent.mkdir();path.write_bytes(r['expected_output'].encode())
        out['downloads'].append({'case_id':case+'_result','language':lang,'edition':ed,'kind':'result','path':str(path),'filename':r['provenance']['result_filename'],'url':url(lang),'utc':stamp})
    for r in fixture['downloads']:
        lang,ed=r['language'],r['edition'];case=f'{lang}_{ed}_{r["kind"]}';path=base/case/r['expected_filename'];path.parent.mkdir()
        shutil.copyfile(base/r['expected_file'],path)
        out['downloads'].append({'case_id':case,'language':lang,'edition':ed,'kind':r['kind'],'path':str(path),'filename':r['expected_filename'],'url':url(lang),'utc':stamp})
    for r in fixture['forward_cases']:
        out['forward'].append({'case_id':r['case_id'],'language':r['language'],'edition':r['edition'],'input':r['input'],'visible':r['expected_output'],'url':'https://example-forward.streamlit.app/','utc':stamp})
    for r in fixture['custom_upload_cases']:
        lang=r['language'];path=Path(next(v['path'] for v in out['downloads'] if v['language']==lang and v['edition']=='current' and v['kind']=='effective'));digest=validator.sha(path.read_bytes())
        out['custom'].append({'case_id':lang+'_custom','language':lang,'edition':'custom','upload_kind':r['upload_kind'],'uploaded_path':str(path),'input':r['input'],'output':r['expected_output'],'captions':[validator.PREFIX[lang]+validator.CUSTOM_LABEL[lang]+' / uploaded / '+digest[:12]],'url':url(lang),'utc':stamp})
    for lang in ('JA','ZH'):
        current=next(r for r in fixture['inverse_cases'] if r['language']==lang and r['edition']=='current')
        for kind in ('edition_switch','deployment_update'):
            caption=(validator.PREFIX[lang]+current['provenance']['label'] if kind=='edition_switch' else validator.PREFIX[lang]+before['captions'][0][len(validator.PREFIX['JA']):])
            output=current['expected_output'] if kind=='edition_switch' else before['output']
            out['guards'].append({'language':lang,'kind':kind,'old_caption':caption,'output':output,'download_disabled':True,'expected_current_revision':current['provenance']['inverse_compatibility_revision'],'url':url(lang),'utc':stamp})
    return out

class ValidatorTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        for name in ('cloud_fixture.json','cloud_release_fixture.json','cloud_forward_combined.json','cloud_before.json'):
            shutil.copyfile(HERE/name,self.base/name)
        fixture=validator.read(self.base/'cloud_release_fixture.json')
        for row in fixture['downloads']:
            p=self.base/row['expected_file'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/row['expected_file'],p)
        self.evidence=synthetic(self.base)
    def tearDown(self):self.temp.cleanup()
    def result(self):
        validator.save(self.base/'cloud_evidence.json',self.evidence)
        return validator.validate(self.base)
    def block_uploads_with_local_fallback(self):
        self.evidence['custom']=[]
        self.evidence['custom_blocked']=[{'language':lang,'status':'blocked','attempted':lang=='JA','reason':'Synthetic browser permission rejection for validator testing only.','error':'Allow access to file URLs is disabled','url':f'https://example-reverter-{lang.lower()}.streamlit.app/','utc':'2026-10-18T12:00:00+00:00'} for lang in ('JA','ZH')]
        fallback=validator.read(HERE/'cloud_custom_local_fallback.json')
        fallback['synthetic_validator_test_only']=True
        for row in fallback['cases']:
            observed=next(r for r in self.evidence['downloads'] if r['language']==row['language'] and r['edition']==row['edition'] and r['kind']=='effective')
            row['download_case_id']=observed['case_id'];row['downloaded_filename']=observed['filename']
        validator.save(self.base/'cloud_custom_local_fallback.json',fallback)
        shutil.copyfile(HERE/'verify_downloaded_custom_local.py',self.base/'verify_downloaded_custom_local.py')
    def test_complete_synthetic_contract_passes(self):
        r=self.result();self.assertTrue(r['passed'],r.get('errors'))
        self.assertEqual(r['coverage'],{'inverse':4,'dictionary_downloads':12,'result_downloads':4,'forward':6,'guards':4,'custom':2,'before':1})
    def test_omission_of_each_required_section_fails(self):
        original=copy.deepcopy(self.evidence)
        for name in ('inverse','downloads','forward','guards','custom','before'):
            with self.subTest(name=name):
                self.evidence=copy.deepcopy(original);self.evidence[name].pop();self.assertFalse(self.result()['passed'])
    def test_duplicate_observation_fails(self):
        self.evidence['inverse'].append(dict(self.evidence['inverse'][0]));self.assertFalse(self.result()['passed'])
    def test_wrong_edition_fails(self):
        self.evidence['inverse'][0]['edition']='legacy';self.assertFalse(self.result()['passed'])
    def test_output_identifier_or_spacing_change_fails(self):
        self.evidence['inverse'][0]['output']+=' ';self.assertFalse(self.result()['passed'])
    def test_stale_caption_fails(self):
        self.evidence['inverse'][0]['captions']=self.evidence['before'][0]['captions'];self.assertFalse(self.result()['passed'])
    def test_saved_dictionary_corruption_is_read_and_rejected(self):
        row=next(r for r in self.evidence['downloads'] if r['kind']=='full');p=Path(row['path']);p.write_bytes(p.read_bytes()+b'x')
        self.assertFalse(self.result()['passed'])
    def test_saved_result_corruption_is_read_and_rejected(self):
        row=next(r for r in self.evidence['downloads'] if r['kind']=='result');p=Path(row['path']);p.write_bytes(p.read_bytes()+b'\n')
        self.assertFalse(self.result()['passed'])
    def test_download_filename_revision_change_fails(self):
        self.evidence['downloads'][0]['filename']='old.txt';self.assertFalse(self.result()['passed'])
    def test_chrome_duplicate_suffix_is_preserved_and_allowed(self):
        row=self.evidence['downloads'][0];path=Path(row['path']);new=path.with_name(path.stem+' (2)'+path.suffix);path.rename(new)
        row['path']=str(new);row['filename']=new.name
        result=self.result();self.assertTrue(result['passed'],result.get('errors'))
        self.assertTrue(next(r for r in result['downloads'] if r['kind']=='result')['duplicate_suffix_only'])
    def test_arbitrary_filename_suffix_is_not_allowed(self):
        for suffix in (' (0)',' (old)','-1',' (1) extra'):
            with self.subTest(suffix=suffix):self.assertFalse(validator.download_name_matches('name'+suffix+'.csv','name.csv'))
    def test_actual_basename_must_be_reported(self):
        row=self.evidence['downloads'][0];path=Path(row['path']);new=path.with_name('pretend.txt');path.rename(new);row['path']=str(new)
        self.assertFalse(self.result()['passed'])
    def test_false_combined_actual_proof_is_rejected(self):
        path=self.base/'cloud_forward_combined.json';proof=validator.read(path);proof['cases'][0]['actual_output']='wrong';validator.save(path,proof)
        fixture=validator.read(self.base/'cloud_release_fixture.json');fixture['combined_forward_proof_sha256']=validator.sha(path.read_bytes());validator.save(self.base/'cloud_release_fixture.json',fixture)
        self.assertFalse(self.result()['passed'])
    def test_wrong_forward_body_fails(self):
        self.evidence['forward'][0]['visible']='';self.assertFalse(self.result()['passed'])
    def test_stale_download_enabled_fails(self):
        self.evidence['guards'][0]['download_disabled']=False;self.assertFalse(self.result()['passed'])
    def test_guard_relabelled_as_new_revision_fails(self):
        row=next(r for r in self.evidence['guards'] if r['kind']=='deployment_update');row['old_caption']=self.evidence['inverse'][0]['captions'][0]
        self.assertFalse(self.result()['passed'])
    def test_custom_upload_wrong_bytes_fails(self):
        row=self.evidence['custom'][0];path=self.base/'wrong.csv';path.write_bytes(b'root,hanzi\n');row['uploaded_path']=str(path)
        self.assertFalse(self.result()['passed'])
    def test_missing_actual_saved_file_fails(self):
        self.evidence['downloads'][0]['path']='missing.txt';self.assertFalse(self.result()['passed'])
    def test_missing_fixture_is_incomplete(self):
        (self.base/'cloud_release_fixture.json').unlink();r=self.result();self.assertFalse(r['passed']);self.assertEqual(r['status'],'incomplete')
    def test_packaged_evidence_has_no_private_absolute_paths(self):
        self.result();target=self.base/'package';r=validator.package(self.base,target);self.assertTrue(r['passed'])
        self.assertTrue(validator.validate(target)['passed'])
    def test_blocked_custom_is_never_reported_as_all_passed(self):
        self.block_uploads_with_local_fallback();r=self.result()
        self.assertTrue(r['core_passed']);self.assertTrue(r['evidence_package_allowed'])
        self.assertFalse(r['completed']);self.assertFalse(r['passed']);self.assertFalse(r['all_requested_checks_passed']);self.assertFalse(r['cloud_custom_completed'])
        self.assertEqual(r['status'],'CORE_PASS_CUSTOM_BLOCKED')
    def test_blocked_custom_requires_actual_rejection_evidence(self):
        self.block_uploads_with_local_fallback()
        for r in self.evidence['custom_blocked']:r['attempted']=False
        self.assertFalse(self.result()['evidence_package_allowed'])
    def test_blocked_custom_requires_local_fallback_file(self):
        self.block_uploads_with_local_fallback();(self.base/'cloud_custom_local_fallback.json').unlink()
        self.assertFalse(self.result()['evidence_package_allowed'])
    def test_blocked_custom_does_not_hide_core_failure(self):
        self.block_uploads_with_local_fallback();self.evidence['inverse'][0]['output']='wrong'
        r=self.result();self.assertFalse(r['core_passed']);self.assertFalse(r['evidence_package_allowed'])
    def test_local_fallback_bad_output_is_rejected(self):
        self.block_uploads_with_local_fallback();path=self.base/'cloud_custom_local_fallback.json';r=validator.read(path);r['cases'][0]['actual_output']='wrong';validator.save(path,r)
        self.assertFalse(self.result()['evidence_package_allowed'])
    def test_blocked_package_retains_incomplete_status(self):
        self.block_uploads_with_local_fallback();self.result();target=self.base/'package';r=validator.package(self.base,target)
        self.assertTrue(r['evidence_package_allowed']);self.assertFalse(r['all_requested_checks_passed']);self.assertFalse(r['cloud_custom_completed'])

if __name__=='__main__':unittest.main()
