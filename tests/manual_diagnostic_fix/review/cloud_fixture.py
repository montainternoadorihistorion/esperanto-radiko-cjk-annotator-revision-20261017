"""Local actual-page expectations for the separate Cloud observations."""
from pathlib import Path
import argparse, hashlib, json, logging, os, re, sys
ROOT=Path(__file__).resolve().parents[3]
GROUP='greganta preganta kordonita @greganta@ @preganta@ @kordonita@ semajno lasis testikito orkidita'

def build(language, report):
    logging.disable(logging.WARNING)
    from streamlit.testing.v1 import AppTest
    app=ROOT/f'Esperanto-Kanji-Ruby-{language}';sys.path.insert(0,str(app));os.chdir(ROOT)
    disk=(app/'app_data/user_corrections.json').read_bytes()
    def run(at):
        at.run(); assert not at.exception,[x.message for x in at.exception]
        assert not at.error,[x.value for x in at.error]
    at=AppTest.from_file(app/'main.py',default_timeout=180);run(at)
    at=AppTest.from_file(next((app/'pages').glob('1_*.py')),default_timeout=180);run(at)
    rows=[]
    for edition in ('current','legacy'):
        at.selectbox(key='_assignment_edition_widget').set_value(edition);run(at)
        for text in (GROUP,'greganta'):
            at.text_input(key='word_probe').set_value(text);at.button[0].click();run(at)
            diag=[m.value for m in at.markdown if re.fullmatch(r'\*\*[^\n]+\*\*: `[^\n]*`',m.value)]
            html=[f.proto.srcdoc for f in at.get('iframe')]
            assert len(diag)==len(html)==2
            rows.append({'language':language,'edition':edition,'input':text,
              'diagnostic_markdown':diag,'decompositions':[re.search(r'`([^`]*)`$',d).group(1) for d in diag],
              'preview_html':html,'preview_sha256':[hashlib.sha256(h.encode()).hexdigest() for h in html]})
            print(language,edition,'group' if text==GROUP else 'single','fixture PASS',flush=True)
    assert (app/'app_data/user_corrections.json').read_bytes()==disk
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'passed':True,'is_cloud_observation':False,'language':language,'rows':rows,
      'method':'Actual local manual-page AppTest; final diagnostic markdown and iframe srcdoc. For independent Cloud comparison.'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();build(a.language,a.report)
