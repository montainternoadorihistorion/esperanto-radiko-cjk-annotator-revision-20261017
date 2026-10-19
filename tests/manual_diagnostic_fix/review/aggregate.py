"""Publish completed independent review reports without altering application data."""
from pathlib import Path
import argparse, hashlib, json, subprocess
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]

def main(source):
    proof=json.loads((source/'source_review.json').read_text(encoding='utf8'))
    assert proof['passed'] and not proof['issues']
    reports=[];fixtures=[]
    for lang in ('JA','ZH','KO'):
        r=json.loads((source/f'app_{lang}.json').read_text(encoding='utf8'))
        f=json.loads((source/f'cloud_fixture_{lang}.json').read_text(encoding='utf8'))
        assert r['passed'] and r['corrections_disk_unchanged'] and len(r['rows'])==26
        assert all(all(row['iframe_equals_main']) for row in r['rows'])
        assert f['passed'] and f['is_cloud_observation'] is False and len(f['rows'])==4
        expected=next(x for x in proof['rows'] if x['language']==lang)
        app=ROOT/f'Esperanto-Kanji-Ruby-{lang}'
        assert hashlib.sha256((app/'main.py').read_bytes()).hexdigest()==expected['main_sha256']
        assert hashlib.sha256(next((app/'pages').glob('1_*.py')).read_bytes()).hexdigest()==expected['page_sha256']
        reports.append(r);fixtures.append(f)
        for filename in (f'app_{lang}.json',f'cloud_fixture_{lang}.json'):
            (OUT/filename).write_bytes((source/filename).read_bytes())
    (OUT/'source_review.json').write_bytes((source/'source_review.json').read_bytes())
    result={'passed':True,'issues':[],'baseline':proof['baseline'],
      'reviewed_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
      'source_fingerprints_match':True,'languages':['JA','ZH','KO'],
      'editions':['current','legacy'],'manual_page_queries':sum(len(r['rows']) for r in reports),
      'actual_main_conversions':sum(r['main_conversions'] for r in reports),
      'actual_iframe_srcdoc_comparisons':sum(r['preview_comparisons'] for r in reports),
      'displayed_diagnostic_comparisons':sum(r['diagnostic_comparisons'] for r in reports),
      'draft_and_session_guards':sum(len(r['guards']) for r in reports),
      'actual_footer_url_checks':sum(len(r['footer_urls']) for r in reports),
      'local_cloud_fixture_queries':sum(len(f['rows']) for f in fixtures),
      'disk_corrections_unchanged':True,'source_review':proof['review_notes'],
      'method':'Fresh process per language; real Streamlit AppTest main and manual-page controls. Compare both final iframe srcdocs byte for byte against actual main results, and diagnostic markdown against independently parsed visible segmentation. No production conversion function mocked. Session override saved through page button and transferred between independent AppTest sessions. Deliberately different test-only drafts and session overrides are isolated checks, not adopted linguistic corrections; stored data remain unchanged. Cloud fixtures are local expectations only.'}
    raw=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (OUT/'review_summary.json').write_text(raw,encoding='utf8')
    (source/'review_summary.json').write_text(raw,encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_review','method')},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    main(p.parse_args().source)
