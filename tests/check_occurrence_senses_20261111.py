"""Real app regression: explicit mineral sense with fixed/default routes intact."""
from pathlib import Path
import argparse,sys,os,json,re,hashlib
from unittest.mock import patch

def run(root,lang,out):
 app=root/f'Esperanto-Kanji-Ruby-{lang}';sys.path.insert(0,str(app));os.chdir(root)
 import esp_occurrence_senses as senses
 import esp_assignment_edition as ed
 import esp_text_replacement_module as rt
 import esp_overlay_module as ov
 data=app/'app_data'
 formats={'pure':'替换后文字列のみ(仅)保留(简单替换)','kanji':ov.KANJI_FMT,'ruby':ov.RUBY_FMT}
 skip=rt.import_placeholders(str(data/'placeholders_skip.txt'));local=rt.import_placeholders(str(data/'placeholders_localcapture.txt'))
 rows=[]
 source='nefrito @nefrito@ %nefrito @nefrito@% nefrito\n  nefrIT nefritology nefrite nefritojn NEFRITO Nefrito molgemo'
 candidates=senses.find_occurrences(source)
 assert [r['source'] for r in candidates]==['nefrito','nefrito','nefrito','nefrite','nefritojn','NEFRITO','Nefrito']
 assert not senses.find_occurrences('nefrito@example.org xnefrito nefritologo %nefrito% nefrIt nefrith')
 assert len(senses.find_occurrences('@nefrito@'))==1
 guards=0
 for edition in ('current','legacy'):
  for mode,fmt in formats.items():
   gg,ll,tw=ed.load_lists(data,mode,edition)
   kwargs=dict(placeholders_for_skipping_replacements=skip,replacements_list_for_localized_string=ll,
      placeholders_for_localized_replacement=local,replacements_final_list=gg,replacements_list_for_2char=tw,format_type=fmt,reviewed_local_decompositions=True)
   selected=senses.render_selections(source,[1,3,4,5,6],data,fmt,edition=edition,bundled=True)
   base=rt.orchestrate_comprehensive_esperanto_text_replacement(source,**kwargs)
   got=rt.orchestrate_comprehensive_esperanto_text_replacement(source,explicit_occurrences=selected,**kwargs)
   if edition=='legacy':assert not selected and base==got
   else:
    assert len(selected)==5
    if mode!='ruby':assert got.count('软玉ᴺ')==5,(mode,got)
    else: assert senses.load_sense(data)['annotations'][lang] in got
    assert 'nefrito @nefrito@' in got
    parallel=rt.parallel_process(source,num_processes=2,explicit_occurrences=selected,**kwargs)
    assert parallel==got
    try:rt.orchestrate_comprehensive_esperanto_text_replacement('X'+source,explicit_occurrences=selected,**kwargs)
    except ValueError:guards+=1
    else:raise AssertionError('stale selection accepted')
    # Existing conversion of unselected identical spellings remains identical.
    assert got.split(' ',1)[0]==base.split(' ',1)[0]
   assert not senses.render_selections(source,[1],data,fmt,edition=edition,bundled=False)
   rows.append(dict(language=lang,edition=edition,mode=mode,source=source,selected=[1,3,4,5,6] if selected else [],output=rt.apply_ruby_html_header_and_footer(got,fmt)))
   # Every reviewed ending, all three casing forms, normal and @ rendering.
   for prefix,suffix in (('',''),('@','@')):
    words=sorted(senses._FORMS)
    forms_source='\n'.join(prefix+w+suffix for w in words)
    choice=list(range(len(words)))
    payload=senses.render_selections(forms_source,choice,data,fmt,edition=edition,bundled=True)
    result=rt.orchestrate_comprehensive_esperanto_text_replacement(forms_source,explicit_occurrences=payload,**kwargs)
    if edition=='current':
     assert len(payload)==len(words)
     assert result.count('软玉ᴺ')==len(words) if mode!='ruby' else result.count('<ruby>')==len(words)
    rows.append(dict(language=lang,edition=edition,mode=mode,source=forms_source,selected=choice if payload else [],output=rt.apply_ruby_html_header_and_footer(result,fmt)))
   # Normalization and literal HTML characters preserve their normal behavior.
   for boundary in ('ĉu  nefrito\r\n%<nefrito>&@%','cxu\tnefrito\rnefrito','@nefrito nefrito@','@nefrit@o'):
    picks=senses.find_occurrences(boundary)
    payload=senses.render_selections(boundary,[0],data,fmt,edition=edition,bundled=True)
    result=rt.orchestrate_comprehensive_esperanto_text_replacement(boundary,explicit_occurrences=payload,**kwargs)
    if boundary=='@nefrit@o':assert '@' not in result,(lang,edition,mode,result)
    rows.append(dict(language=lang,edition=edition,mode=mode,source=boundary,selected=[0] if payload else [],output=rt.apply_ruby_html_header_and_footer(result,fmt)))
   ed._load_lists_cached.clear()
 assert guards==3
 # UI lifecycle and exact download transport.
 import streamlit as st
 from streamlit.testing.v1 import AppTest
 at=AppTest.from_file(app/'main.py',default_timeout=120)
 captured=[]; original=st.download_button
 def download(label,data,*args,**kwargs):
  if kwargs.get('key')=='confirmed_result_download':captured.append((data,kwargs['file_name']))
  return original(label,data,*args,**kwargs)
 def rerun():
  captured.clear();at.run();assert not at.exception,[e.message for e in at.exception]
  assert not at.error,[e.value for e in at.error]
 ui=[]
 with patch.object(st,'download_button',side_effect=download):
  rerun()
  at.text_area(key='text0_value').set_value('nefrito @nefrito@ %nefrito%');rerun()
  assert len(at.multiselect(key='_nefrit_sense_widget').options)==2
  at.multiselect(key='_nefrit_sense_widget').set_value([1]);rerun()
  for mode,index in (('pure',2),('kanji',1),('ruby',0)):
   radio=at.radio(key='_conversion_mode_widget');radio.set_value(radio.options[index]);rerun()
   assert at.multiselect(key='_nefrit_sense_widget').value==[1]
   at.button(key='convert_text').click();rerun()
   result=at.session_state['result_html']
   assert result.count('软玉ᴺ')==1 if mode!='ruby' else senses.load_sense(data)['annotations'][lang] in result
   assert at.session_state['result_assignment_metadata']['render_options']['senses']==[1]
   at.button(key='confirm_download').click();rerun()
   assert len(captured)==1
   raw=captured[0][0];raw=raw if isinstance(raw,bytes) else raw.encode()
   expected=result if mode=='pure' else result.replace('</head>',f'<meta name="esperanto-ruby-mode" content="{"kanji" if mode=="kanji" else "annotation"}">\n</head>',1)
   assert raw.decode().endswith(expected),(mode,result,raw.decode())
   ui.append({'mode':mode,'download_sha256':hashlib.sha256(raw).hexdigest(),'filename':captured[0][1]})
   rerun()
  at.multiselect(key='_nefrit_sense_widget').set_value([]);rerun()
  assert not any(x.key=='confirm_download' for x in at.button),'stale result still saveable'
  at.multiselect(key='_nefrit_sense_widget').set_value([1]);rerun()
  at.selectbox(key='_assignment_edition_widget').set_value('legacy');rerun()
  assert not at.multiselect and at.text_area(key='text0_value').value=='nefrito @nefrito@ %nefrito%'
  at.button(key='convert_text').click();rerun()
  assert '软玉ᴺ' not in at.session_state['result_html']
  at.selectbox(key='_assignment_edition_widget').set_value('current');rerun()
  assert at.multiselect(key='_nefrit_sense_widget').value==[1]
  at.text_area(key='text0_value').set_value('nefrito nefrito');rerun()
  assert at.multiselect(key='_nefrit_sense_widget').value==[]
 report={'passed':True,'language':lang,'rows':rows,'ui':ui,'stale_source_guards':guards,'old_and_custom_unchanged':True}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
 print(lang,'PASS',len(rows),'direct batches +',len(ui),'UI downloads',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--lang',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.root,a.lang,a.out)
