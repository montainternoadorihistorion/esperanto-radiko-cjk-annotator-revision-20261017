"""Actual local Streamlit download pages; browser transport remains a separate check."""
from pathlib import Path
from unittest.mock import patch
import argparse,hashlib,io,json,logging,os,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[2]
LANGUAGES=('JA','ZH','KO')
LABELS={'JA':'漢字割り当て一覧HTML一式（新版・日本語の語義）','ZH':'汉字分配一览HTML文件包（新版・日语释义）','KO':'한자 배정 목록 HTML 묶음（신판·일본어 뜻풀이）'}
def sha(raw):return hashlib.sha256(raw).hexdigest()

def check(lang,require_source_links=False):
    logging.disable(logging.WARNING)
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
    sys.path.insert(0,str(app));os.chdir(ROOT)
    import esp_assignment_edition as ed
    page=next((app/'pages').glob('2_*.py'))
    raw_zip=(ROOT/'references/kanji_reference_current.zip').read_bytes()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    captured=[];real_download=st.download_button
    def download(label,data,*args,**kwargs):
        if hasattr(data,'read'):
            position=data.tell();raw=data.read();data.seek(position)
        else:
            raw=data if isinstance(data,bytes) else data.encode('utf-8')
        captured.append({'label':label,'filename':kwargs.get('file_name'),'mime':kwargs.get('mime'),'raw':raw})
        return real_download(label,data,*args,**kwargs)
    def run(at):
        captured.clear();at.run()
        assert not at.exception,[x.message for x in at.exception]
        assert not at.error,[x.value for x in at.error]
    rows=[]
    with patch.object(st,'download_button',side_effect=download):
        at=AppTest.from_file(app/'main.py',default_timeout=120);run(at)
        at.switch_page(page.relative_to(app).as_posix());run(at)
        for edition in ('current','legacy'):
            at.selectbox(key='_assignment_edition_widget').set_value(edition);run(at)
            assert at.session_state['assignment_edition']==edition
            matches=[x for x in captured if x['filename']=='kanji_reference_current.zip']
            assert len(matches)==(1 if edition=='current' else 0),(lang,edition,len(matches))
            if matches:
                entry=matches[0]
                assert entry['label']==LABELS[lang] and entry['mime']=='application/zip'
                assert entry['raw']==raw_zip
                with zipfile.ZipFile(io.BytesIO(entry['raw'])) as z:
                    assert z.namelist()==['kanji.html','words.html']
                    assert all(z.read(n)==(ROOT/'references'/n).read_bytes() for n in z.namelist())
            csv_entry=next(x for x in captured if x['filename'].startswith('kanji_assignments_'))
            selected=ed.resolve_path(data,'kanji_csv',edition)
            assert csv_entry['raw']==selected.read_bytes()
            assert csv_entry['filename'].startswith('kanji_assignments_'+edition+'_')
            ruby=ed.resolve_path(data,'ruby_csv',edition)
            expected={p.name:p for p in [ruby,*[data/n for n in ('分解設定.json','word_anno.json','E_stem.json','user_corrections.json')]]}
            for name,p in expected.items():
                items=[x for x in captured if x['filename']==name];assert len(items)==1
                assert items[0]['raw']==p.read_bytes(),name
            assert len(captured)==6+(edition=='current'),(edition,len(captured))
            markdown=[x.value for x in at.markdown]
            source=[s for s in markdown if '/tree/'+head in s and '/archive/'+head+'.zip' in s]
            if require_source_links:assert len(source)==1,(lang,edition,'Matching committed source links missing')
            rows.append({'language':lang,'edition':edition,'passed':True,'reference_button_visible':bool(matches),
                'existing_download_count':len(captured)-len(matches),'selected_kanji_csv':selected.relative_to(ROOT).as_posix(),
                'matching_source_links_present':bool(source),'downloads':[{k:v for k,v in x.items() if k!='raw'}|{'bytes':len(x['raw']),'sha256':sha(x['raw'])} for x in captured]})
    return {'head':head,'language':lang,'cases':rows,'cloud_test':False,'method':'Actual local Streamlit AppTest; real download button is called and its supplied bytes inspected. Browser transport is not simulated as a Cloud test.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',choices=LANGUAGES,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-source-links',action='store_true');a=p.parse_args()
    result=check(a.language,a.require_source_links)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps({'language':a.language,'cases':len(result['cases']),'passed':True},ensure_ascii=False))
