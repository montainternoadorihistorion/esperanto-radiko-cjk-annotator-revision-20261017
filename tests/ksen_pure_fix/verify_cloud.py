"""Verify observed Cloud results and real downloaded text, not simulated UI."""
from pathlib import Path
import hashlib,json,re

HERE=Path(__file__).resolve().parent

def main():
    fixture=json.loads((HERE/'cloud_fixture.json').read_text(encoding='utf8'))
    evidence=json.loads((HERE/'cloud_evidence.json').read_text(encoding='utf8'))
    expected={(r['forward_language'],r['edition'],r['mode']):r for r in fixture['rows']}
    observed={(r['language'],r['edition'],r['mode']):r for r in evidence['forward']}
    assert len(evidence['forward'])==len(observed)==len(expected)==12
    assert set(observed)==set(expected)
    for key,row in observed.items():
        want=expected[key]
        assert row['input']==want['input'],key
        assert row['output']==want['rendered'],key
        assert row['url'].startswith(f'https://esperanto-cjk-revision-{key[0].lower()}-20261017.streamlit.app/'),key
    rexp={(r['language'],r['edition']):r for r in fixture['reverse_rows']}
    robs={(r['language'],r['edition']):r for r in evidence['reverse']}
    assert len(evidence['reverse'])==len(robs)==len(rexp)==4
    assert set(robs)==set(rexp)
    for key,row in robs.items():
        assert row['input']==rexp[key]['input'] and row['output']==rexp[key]['output'],key
        assert row['url'].startswith(f'https://esperanto-reverter-revision-{key[0].lower()}-20261018.streamlit.app/'),key
    downloaded=[]
    assert len(evidence['downloads'])==6
    identities=set()
    for row in evidence['downloads']:
        key=(row['language'],row['edition'],'pure');assert key not in identities;identities.add(key)
        path=HERE/row['path'];raw=path.read_bytes()
        assert raw==expected[key]['rendered'].encode('utf8'),key
        assert re.search('_'+row['edition']+r'_[0-9a-f]{12}(?: \([0-9]+\))?\.txt$',row['filename']),key
        downloaded.append({'language':key[0],'edition':key[1],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    assert identities=={key for key in expected if key[2]=='pure'}
    assert all(r['old_download_absent'] for r in evidence['edition_switch_guards'])
    assert len(evidence['edition_switch_guards'])==3
    result={'passed':True,'forward_routes':len(observed),'inverse_routes':len(robs),'real_text_downloads':downloaded,'switch_guards':3,'scope':'Cloud observations after public main deployment; expected existing ambiguous restorations are preserved. This does not inspect the running Cloud commit.'}
    (HERE/'cloud_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
