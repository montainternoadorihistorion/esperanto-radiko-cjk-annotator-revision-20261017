"""Actual Streamlit two-edition forms, stale results, manual and download pages."""
from pathlib import Path
import argparse,html,json,logging,os,re,subprocess,sys,time
logging.disable(logging.WARNING)
H=Path(__file__).resolve().parent
A=H.parent
SOURCE='laso @las@o ananaso @ananas@o grefti @greft@i doto @dot@o tualeto @tualet@o @semajn@tagoj & %amiko%'
EXPECT={'current':'放o 放o 菠o 菠o 移植i 移植i 妆o 妆o 妆ᵀo 妆ᵀo 周日oj & amiko',
        'legacy':'留o 留o 菠萝o 菠萝o 嫁接i 嫁接i 嫁妆o 嫁妆o 妆o 妆o 周日oj & amiko'}
def run(lang):
 from streamlit.testing.v1 import AppTest
 app=A/f'Esperanto-Kanji-Ruby-{lang}';sys.path.insert(0,str(app));os.chdir(A)
 at=AppTest.from_file(app/'main.py',default_timeout=180)
 def execute():
  at.run();assert not at.exception,[x.message for x in at.exception];assert not at.error,[x.value for x in at.error]
  assert Path.cwd()==A
 execute();rows=[];annotation=None
 for edition in ('current','legacy'):
  at.selectbox(key='_assignment_edition_widget').set_value(edition);execute()
  if edition=='legacy':
   assert at.session_state['result_assignment_metadata']['edition_id']=='current'
   assert at.info and len(at.text_area)==1,'Stale previous editor must not remain visible'
  for mode in range(3):
   at.radio[0].set_value(at.radio[0].options[mode]);execute()
   at.text_area(key='text0_value').set_value(SOURCE)
   at.button(key='convert_text').click();execute()
   result=at.session_state['result_html'];meta=dict(at.session_state['result_assignment_metadata'])
   assert meta['edition_id']==edition and meta['signature'] and meta['assignment_signature']
   if mode==2:assert result==EXPECT[edition],(lang,edition,result)
   if mode==0:
    if annotation is None:annotation=result
    else:assert annotation==result,'Annotations must be common across editions'
   rows.append({'edition':edition,'mode':mode,'metadata':meta,'result':result})
  for page in sorted((app/'pages').glob('*.py')):
   at.switch_page(page.relative_to(app).as_posix());execute()
   assert at.session_state['assignment_edition']==edition and at.selectbox(key='_assignment_edition_widget').value==edition,(edition,page.name,at.session_state['assignment_edition'],at.selectbox(key='_assignment_edition_widget').value)
   if page.name.startswith('1_'):
    at.text_input(key='decomp_in').set_value('las/o');execute()
    assert at.table,'Segment preview must exist'
    table=str(at.table[0].value)
    assert ('留' if edition=='legacy' else '放') in table,table
   at.switch_page('main.py');execute()
   assert at.session_state['assignment_edition']==edition
 # Saved decompositions survive a switch but receive the selected rendering.
 at.switch_page(next((app/'pages').glob('1_*.py')).relative_to(app).as_posix());execute()
 at.text_input(key='decomp_in').set_value('las/o');execute()
 save=next(b for b in at.button if b.type=='button' and ('✅' in b.label))
 save.click();execute()
 at.switch_page('main.py');execute()
 assert len(at.text_area)==1,'A changed manual correction invalidates the prior result'
 at.selectbox(key='_assignment_edition_widget').set_value('current');execute()
 at.radio[0].set_value(at.radio[0].options[2]);execute();at.text_area(key='text0_value').set_value('laso')
 at.button(key='convert_text').click();execute()
 assert at.session_state['result_html']=='放o'
 return {'language':lang,'passed':True,'forms':rows,'cross_page_selection':True,'stale_result_hidden':True,'saved_manual_rerendered':True}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--language',choices=('JA','ZH','KO'));p.add_argument('--app-root',type=Path);p.add_argument('--report',type=Path,default=H/'app_ui_editions.json');a=p.parse_args()
 if a.app_root:A=a.app_root.resolve()
 if a.language:print(json.dumps(run(a.language),ensure_ascii=False))
 else:
  cases=[]
  for lang in ('JA','ZH','KO'):
   r=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--language',lang,'--app-root',str(A)],capture_output=True,text=True,encoding='utf-8')
   (a.report.parent/f'app_ui_{lang}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
   assert r.returncode==0,(lang,r.stdout[-4000:],r.stderr[-4000:])
   cases.append(json.loads(r.stdout));print(lang,'PASS',flush=True)
  a.report.write_text(json.dumps({'passed':True,'method':'Streamlit AppTest; not browser automation','cases':cases},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
