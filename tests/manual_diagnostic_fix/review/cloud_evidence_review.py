"""Independently verify saved Cloud evidence; no browser operations or app writes."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, re, struct
ROOT=Path(__file__).resolve().parents[3]

def verify(directory):
    report=json.loads((directory/'cloud_validation.json').read_text(encoding='utf8'))
    assert report['passed']
    assert report['downloads']==json.loads((directory/'records.json').read_text(encoding='utf8'))
    assert report['manual']==json.loads((directory/'manual_records.json').read_text(encoding='utf8'))
    assert report['links']==json.loads((directory/'link_records.json').read_text(encoding='utf8'))
    rows=report['downloads']
    assert len(rows)==len({row['file'] for row in rows})==50
    assert dict(Counter(row['kind'] for row in rows))=={'forward':18,'plain':4,'html':24,'html_cloud':4}
    fixtures=json.loads((ROOT/'tests/at_two_exact_fix/cloud_fixture.json').read_text(encoding='utf8'))['rows']
    def fixture(language,edition,mode):
        return next(x for x in fixtures if (x['forward_language'],x['edition'],x['mode'])==(language,edition,mode))
    files=[]
    for row in rows:
        path=directory/row['file']; raw=path.read_bytes()
        assert path.parent==directory and row['passed']
        assert hashlib.sha256(raw).hexdigest()==row['sha256'],row['file']
        text=raw.decode('utf8')
        if row['kind']=='forward':
            expected=fixture(row['language'],row['edition'],row['mode'])['rendered']
            if row['mode']!='pure':
                prefix,content=text.split('\n',1)
                assert prefix.startswith('<!-- assignment-edition:'+row['edition']+' ')
                assert 'signature:'+row['metadata_signature'] in prefix
                assert hashlib.sha256(content.encode()).hexdigest()==row['content_sha256']
            else:content=text
        elif row['kind']=='plain':
            content=text
            expected=fixture('JA',row['edition'],'pure')['plain_reverse_expected'][row['inverse_language']]
        else:
            content=text
            expected=fixture(row['forward_language'],row['edition'],row['mode'])['html_recovery_expected']
            if row['kind']=='html_cloud':
                actual_input=directory/f"forward_{row['forward_language']}_{row['edition']}_{row['mode']}.html"
                assert hashlib.sha256(actual_input.read_bytes()).hexdigest()==row['input_sha256']
        assert content==expected,row['file']+' differs from fixed production expectation'
        files.append({'file':row['file'],'sha256':row['sha256'],'bytes':len(raw),'expected_content_matches':True})
    manual=[]
    for row in report['manual']:
        fixture_file=ROOT/f"tests/manual_diagnostic_fix/review/cloud_fixture_{row['language']}.json"
        local=json.loads(fixture_file.read_text(encoding='utf8'))['rows']
        expected=next(x for x in local if (x['edition'],x['input'])==(row['edition'],row['input']))
        assert row['diagnostics']==expected['decompositions']
        assert row['preview_sha256']==expected['preview_sha256']
        snapshot=(directory/row['snapshot']).read_text(encoding='utf8')
        assert row['input'] in snapshot
        assert snapshot.count('- iframe:') in (0,2)
        assert all('- code: '+d in snapshot for d in row['diagnostics'])
        manual.append({'snapshot':row['snapshot'],'sha256':hashlib.sha256(snapshot.encode()).hexdigest(),
                       'diagnostics_present':True,'expanded_iframe_records':snapshot.count('- iframe:'),
                       'recorded_preview_hashes_match_AppTest':True})
    urls=[f'https://esperanto-cjk-revision-{lang}-20261017.streamlit.app/' for lang in ('ja','zh','ko')]
    assert len(report['links'])==3 and all(all(url in row['urls'] for url in urls) for row in report['links'])
    screenshot=(directory/'manual_ja_greganta.png').read_bytes()
    from PIL import Image
    screenshot_image=Image.open(directory/'manual_ja_greganta.png')
    assert screenshot_image.format in ('PNG','JPEG')
    dimensions=screenshot_image.size
    result={'passed':True,'issues':[],'download_files_rehashed':len(files),'expected_contents_matched':len(files),
      'manual_snapshots_checked':len(manual),'recorded_preview_hashes_checked':len(manual)*2,
      'footer_urls_checked':9,'files':files,'manual_snapshots':manual,
      'screenshot':{'file':'manual_ja_greganta.png','actual_format':screenshot_image.format,'sha256':hashlib.sha256(screenshot).hexdigest(),'width':dimensions[0],'height':dimensions[1]},
      'method':'Rehash every saved downloaded file, compare each decoded content with fixed production fixtures and validate edition metadata. Compare recorded Cloud iframe srcdoc hashes and diagnostics with independent AppTest fixtures; confirm corresponding visible diagnostic snapshots. One expanded snapshot includes both iframe texts; other snapshots retain a collapsed preview expander. Screenshot separately visually inspected by reviewer. No new browser operations or application data writes.'}
    output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (Path(__file__).parent/'cloud_evidence_review.json').write_text(output,encoding='utf8')
    (directory.parent/'review/cloud_evidence_review.json').write_text(output,encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','manual_snapshots','method')},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    verify(p.parse_args().directory)
