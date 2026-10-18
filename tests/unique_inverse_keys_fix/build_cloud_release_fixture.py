"""Derive release cases from immutable singles and full-rule combined observations."""
from pathlib import Path
import copy, hashlib, json

HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    raw=(HERE/'cloud_fixture.json').read_bytes()
    assert sha(raw)=='4dd8877c1acf30e9bae1d89751185c2fc6bf08ff0a3320f957e7fd2d3a4d48da'
    original=json.loads(raw);fixture=copy.deepcopy(original)
    proof_raw=(HERE/'cloud_forward_combined.json').read_bytes();proof=json.loads(proof_raw)
    assert proof['passed'] and proof['original_fixture_sha256']==sha(raw)
    rows=proof['cases'];assert len(rows)==6
    bykey={(r['language'],r['edition']):r for r in rows}
    assert set(bykey)=={(l,e) for l in ('JA','ZH','KO') for e in ('current','legacy')}
    forward=[]
    for row in rows:
        singles=[r for r in original['forward_cases'] if r['edition']==row['edition']]
        assert row['input']==' '.join(r['input'] for r in singles)
        assert row['actual_output']==row['expected_output']==' '.join(r['expected_output'] for r in singles)
        assert row['expected_restored']==' '.join(r['expected_restored'] for r in singles)
        assert row['actual_restored']=={'JA':row['expected_restored'],'ZH':row['expected_restored']}
        forward.append({k:row[k] for k in ('case_id','language','edition','mode','input','expected_output','expected_output_sha256','expected_restored')})
    fixture['schema_version']=2
    fixture['base_fixture_sha256']=sha(raw)
    fixture['combined_forward_proof_sha256']=sha(proof_raw)
    fixture['forward_cases']=forward
    fixture['release_derivation']='Each inverse case preserves its original key and ambiguity-control probes, followed by a newline and an actually rendered combined normal/@ sentence. Provenance and all dictionary download expectations are unchanged.'
    for row in fixture['inverse_cases']:
        f=bykey[(row['language'],row['edition'])]
        row['input']+='\n'+f['actual_output']
        row['expected_output']+='\n'+f['expected_restored']
        row['expected_output_sha256']=sha(row['expected_output'].encode('utf-8'))
        row['forward_roundtrip_input']=f['input']
        row['forward_roundtrip_visible']=f['actual_output']
        row['forward_roundtrip_expected_restored']=f['expected_restored']
        row['forward_roundtrip_case_id']=f['case_id']
    for row in fixture['custom_upload_cases']:
        f=next(r for r in fixture['inverse_cases'] if r['language']==row['language'] and r['edition']=='current')
        row['input']=f['input'];row['expected_output']=f['expected_output']
        row['upload_kind']='current_effective'
        row['expected_output_sha256']=sha(row['expected_output'].encode('utf-8'))
    out=HERE/'cloud_release_fixture.json'
    out.write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert (HERE/'cloud_fixture.json').read_bytes()==raw
    print(json.dumps({'path':out.name,'sha256':sha(out.read_bytes()),'inverse':4,'forward':6,'custom':2},ensure_ascii=False))

if __name__=='__main__':main()
