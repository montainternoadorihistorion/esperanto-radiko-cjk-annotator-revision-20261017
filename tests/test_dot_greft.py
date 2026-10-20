"""Portable exact-row and real app-path tests for approved dot/greft changes."""
from pathlib import Path
import argparse,csv,gc,hashlib,importlib.util,io,json,re,zipfile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dot_greft_helpers',HERE/'test_reviewed_at_sync.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
VALUES={'greft':('嫁接','移植'),'dot':('嫁妆','妆'),'tualet':('妆','妆ᵀ')}
OLD={'JA':{'dot':'持参金','greft':'移植'},'ZH':{'dot':'嫁妆','greft':'嫁接'},'KO':{'dot':'지참금','greft':'이식'}}
NEW={'JA':{'dot':'持参金・婚姻財産／（転義）資質などを与える','greft':'接ぎ木／組織・器官の移植','endow':'資質などを与える','medical':'組織・器官の移植','plant':'接ぎ木'},'ZH':{'dot':'嫁妆、婚姻财产／（转义）赋予资质等','greft':'嫁接／组织、器官移植','endow':'赋予资质等','medical':'组织、器官移植','plant':'嫁接'},'KO':{'dot':'지참금·혼인 재산／（비유）자질 등을 부여하다','greft':'접목／조직·기관 이식','endow':'자질 등을 부여하다','medical':'조직·기관 이식','plant':'접목'}}
CSV_LANG={'エスペラント語根-日本語訳ルビ対応リスト.csv':'JA','世界语词根-中文注释对应列表.csv':'ZH','에스페란토 어근-한국어 번역 루비 대응 목록.csv':'KO'}
WORDS=[];MANUAL=[];CONTROLS={};BASELINE_PURE_MISMATCHES=[]
_original_render=h.render
def bounded_render(engine,data,payload,words,fmt):
 result={}
 for i in range(0,len(words),40):result.update(_original_render(engine,data,payload,words[i:i+40],fmt))
 return result
h.render=bounded_render

def expected_annotation(root,lang,context):
 key=context.replace('/','').lower().strip()
 if root=='dot':return NEW[lang]['endow'] if 'naturdot' in key else NEW[lang]['dot']
 if 'korgreft' in key:return NEW[lang]['medical']
 if 'burĝongreft' in key or 'greftobaz' in key:return NEW[lang]['plant']
 return NEW[lang]['greft']

def neutral(value,after):
 def visit(m):
  spelling=h.plain(m[2]);root=spelling.lower()
  if root not in VALUES:return m[0]
  assert m[1]==VALUES[root][int(after)],(root,m[1],after)
  return '<reviewed>'+spelling+'</reviewed>'
 return h.RUBY.sub(visit,value)

def annotation_neutral(value,after,lang,context,strict=True):
 def visit(m):
  spelling=h.plain(m[1]);root=spelling.lower()
  if root not in OLD[lang]:return m[0]
  meaning=h.plain(m[2])
  if not after:assert meaning==OLD[lang][root],(root,meaning,context)
  elif strict:assert meaning==expected_annotation(root,lang,context),(root,meaning,context)
  else:assert meaning in ({NEW[lang]['dot'],NEW[lang]['endow']} if root=='dot' else {NEW[lang]['greft'],NEW[lang]['medical'],NEW[lang]['plant']}),(root,meaning,context)
  return '<annotation>'+spelling+'</annotation>'
 return h.RUBY.sub(visit,value)

def expected_csv(old,lang):
 lines=[]
 for line in old.decode('utf-8').splitlines(keepends=True):
  body=line.rstrip('\r\n');ending=line[len(body):];row=next(csv.reader([body]),[])
  if row and row[0] in OLD[lang]:
   assert row[1]==OLD[lang][row[0]]
   line=row[0]+','+NEW[lang][row[0]]+ending
  lines.append(line)
 return ''.join(lines).encode('utf-8')

def check_words(before,after,lang):
 assert list(before)==list(after)
 changed=[]
 for key,pairs in before.items():
  actual=after[key];assert len(pairs)==len(actual)
  for (r,v),(rr,vv) in zip(pairs,actual):
   assert r==rr
   if r.lower() in OLD[lang]:assert v==OLD[lang][r.lower()] and vv==expected_annotation(r.lower(),lang,key)
   else:assert v==vv
  if pairs!=actual:changed.append(key)
 return changed

def tables(root,old_bytes=None):
 report=[]
 for lang in ('JA','ZH','KO'):
  data=root/f'Esperanto-Kanji-Ruby-{lang}/app_data';counts={}
  for mode in ('kanji','ruby'):
   p=data/h.MODES[mode][0];after=json.loads(p.read_bytes());before=json.loads(old_bytes(p)) if old_bytes else None
   if before is not None:assert list(before)==list(after)
   for group,rows in after.items():
    changed=0
    if before is not None:assert len(before[group])==len(rows)
    for i,row in enumerate(rows):
     current=neutral(row[1],True) if mode=='kanji' else annotation_neutral(row[1],True,lang,row[0])
     if before is not None:
      prev=before[group][i];assert prev[:1]+prev[2:]==row[:1]+row[2:]
      prior=neutral(prev[1],False) if mode=='kanji' else annotation_neutral(prev[1],False,lang,prev[0])
      assert prior==current,(lang,mode,group,row[0]);assert h.original(prev[1],mode)==h.original(row[1],mode)
      changed+=prev!=row
    counts[mode+'/'+group]={'rows':len(rows),'changed':changed if before is not None else None}
   if mode=='kanji':
    local={r[0]:r[1] for r in after[h.LOCAL]}
    for rt,(_,value) in VALUES.items():
     for spelling in (rt,rt.upper(),rt.title()):assert h.visible(local[spelling])==value
    if lang=='JA':
     pure=json.loads((data/h.MODES['pure'][0]).read_bytes())
     for group,rows in after.items():assert pure[group]==[[r[0],h.strip_ruby(r[1]),*r[2:]] for r in rows]
     del pure
   del after,before;gc.collect()
  mapping=dict(csv.reader(io.StringIO((data/h.CSV_NAME).read_text(encoding='utf-8'))))
  for rt,(_,value) in VALUES.items():assert mapping[rt]==value
  for rt,value in CONTROLS.items():assert mapping[rt]==value,(rt,mapping[rt],value)
  unchanged=[];source_changes=[]
  if old_bytes:
   for p in data.iterdir():
    if not p.is_file() or p.name in (h.MODES['kanji'][0],h.MODES['ruby'][0],h.MODES['pure'][0]):continue
    before=old_bytes(p);after=p.read_bytes()
    if p.name==h.CSV_NAME:
     for rt,(old,new) in VALUES.items():
      oldline=(rt+','+old+'\n').encode();assert before.count(oldline)==1;before=before.replace(oldline,(rt+','+new+'\n').encode())
     assert before==after
    elif p.name in CSV_LANG:assert after==expected_csv(before,CSV_LANG[p.name])
    elif p.name=='word_anno.json':source_changes=check_words(json.loads(before),json.loads(after),lang)
    else:assert before==after,p.name;unchanged.append(p.name)
  report.append({'language':lang,'groups':counts,'word_annotation_contexts_changed':source_changes,'unchanged_data_files':unchanged});print('tables',lang,'PASS',flush=True)
 return report

def runtime(root,after):
    results=[];manual_results=[]
    for lang in ('JA','ZH','KO'):
        app=root/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
        engine=h.load_module(app,'esp_text_replacement_module.py','sperm_engine_'+lang)
        overlay=h.load_module(app,'esp_overlay_module.py','sperm_overlay_'+lang)
        corrections=[(entry,overlay.build_correction(entry,str(data))) for entry in MANUAL]
        kanji=None;kanji_manual=None
        for mode,(filename,fmt) in h.MODES.items():
            owner=root/'Esperanto-Kanji-Ruby-JA/app_data' if mode=='pure' else data
            payload=json.loads((owner/filename).read_bytes());key='ruby' if mode=='ruby' else 'kanji'
            user=overlay.load_overlay_entries(str(data),key)
            if mode=='pure':user=[[a,h.strip_ruby(b),c] for a,b,c in user]
            payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],user)
            first=h.render(engine,data,payload,WORDS,fmt)
            final=dict(first);auto_groups={}
            # Each test input is a separate document. Never let correction of
            # an artificial neighbouring case override a different document.
            for word,value in first.items():
                auto=overlay.auto_overlay_entries(value,str(data),key)
                if mode=='pure':auto=[[a,h.strip_ruby(b),c] for a,b,c in auto]
                if auto:auto_groups.setdefault(json.dumps(auto,ensure_ascii=False),[]).append(word)
            for raw,words in auto_groups.items():
                candidate=dict(payload);candidate[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],json.loads(raw))
                final.update(h.render(engine,data,candidate,words,fmt))
            for word,value in final.items():
                if mode!='pure':
                    source=word[1:-1] if word.startswith('%') and word.endswith('%') else word.replace('@','').replace('%','')
                    source=engine.convert_to_circumflex(source)
                    assert h.original(value,mode)==source,(mode,word,value)
                if mode=='pure' and value!=h.visible(kanji[word]):
                    if after:raise AssertionError((lang,word,value,kanji[word]))
                    BASELINE_PURE_MISMATCHES.append({'language':lang,'input':word,'pure':value,'kanji_visible':h.visible(kanji[word])})
                results.append({'language':lang,'mode':mode,'input':word,'first':first[word],'final':value,'visible':h.visible(value),'restored':h.original(value,mode) if mode!='pure' else None})
            if mode=='kanji':kanji=final
            expected_pairs={w:h.strip_ruby(v) if mode=='pure' else v for _,c in corrections for w,v in c[key]}
            payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],[[w,v,f'${97000000+i}$'] for i,(w,v) in enumerate(expected_pairs.items())])
            actual=h.render(engine,data,payload,list(expected_pairs),fmt);assert actual==expected_pairs
            if mode=='pure':assert actual=={w:h.visible(v) for w,v in kanji_manual.items()}
            if mode=='kanji':kanji_manual=actual
            for word,value in actual.items():
                if mode!='ruby':
                    rt=word[:-1].lower();expected=VALUES[rt][int(after)] if rt in VALUES else CONTROLS.get(rt)
                    assert expected is not None,rt
                    assert h.visible(value)==expected+word[-1],(word,value,expected)
                manual_results.append({'language':lang,'mode':mode,'input':word,'output':value})
            print('runtime',lang,mode,len(final),'manual',len(actual),'PASS',flush=True)
            del payload;gc.collect()
    results.sort(key=lambda r:(r['language'],r['mode'],r['input']));manual_results.sort(key=lambda r:(r['language'],r['mode'],r['input']))
    return results,manual_results


def semantic_checks(report):
 rows={(r['language'],r['mode'],r['input']):r for r in report['runtime']}
 for lang in ('JA','ZH','KO'):
  for rt,(_,expected) in VALUES.items():
   for word in (rt+'o','@'+rt+'@o'):
    for mode in ('kanji','pure'):assert rows[(lang,mode,word)]['visible']==expected+'o'
  for rt in ('dot','greft'):
   for word in (rt+'o','@'+rt+'@o'):
    assert NEW[lang][rt] in h.plain(rows[(lang,'ruby',word)]['final'])
  for word,meaning in [('naturdoto',NEW[lang]['endow']),('naturdotita',NEW[lang]['endow']),('korgrefto',NEW[lang]['medical']),('burĝongrefti',NEW[lang]['plant']),('greftobazo',NEW[lang]['plant'])]:
   html=rows[(lang,'ruby',word)]['final'];assert meaning in h.plain(html),(lang,word,html,meaning)
 manual={(r['language'],r['mode'],r['input']):r['output'] for r in report['manual']}
 for lang in ('JA','ZH','KO'):
  assert NEW[lang]['dot'] in h.plain(manual[(lang,'ruby','doto')]);assert NEW[lang]['greft'] in h.plain(manual[(lang,'ruby','grefti')])
 return {'root_meanings_and_identifier_expectations':True,'marriage_property_and_endowment':True,'plant_and_medical_grafting':True,'context_specific_meanings':True}

def compare(before,after):
 for section,fields in (('runtime',('first','final')),('manual',('output',))):
  assert len(before[section])==len(after[section])
  for a,b in zip(before[section],after[section]):
   assert (a['language'],a['mode'],a['input'])==(b['language'],b['mode'],b['input'])
   for key in fields:
    if a['mode']=='kanji':assert neutral(a[key],False)==neutral(b[key],True),(section,a,b)
    elif a['mode']=='ruby':assert annotation_neutral(a[key],False,a['language'],a['input'],False)==annotation_neutral(b[key],True,a['language'],a['input'],False),(section,a,b)
 return {'all_existing_boundaries_and_non_target_renderings_unchanged':True,'approved_complete_root_display_and_annotation_changes_only':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--app-root',type=Path);p.add_argument('--baseline-zip',type=Path);p.add_argument('--inputs',type=Path);p.add_argument('--capture-before',action='store_true');p.add_argument('--compare-capture',type=Path);p.add_argument('--tables-only',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 root=a.app_root or HERE.parent;config=json.loads((a.inputs or HERE/'dot_greft_inputs.json').read_bytes())
 global WORDS,MANUAL,CONTROLS
 WORDS=config['WORDS'];MANUAL=config['MANUAL'];CONTROLS=config['CONTROLS'];CONTROLS.update({'buf':'蟆','lofi':'蟆鱼'});old=None
 if a.baseline_zip:
  z=zipfile.ZipFile(a.baseline_zip);old=lambda path:z.read(path.relative_to(root).as_posix())
 report={'passed':False,'assignments':VALUES,'tables':tables(root,old) if not a.capture_before else [],'method':'Actual app engine and per-input automatic overlays; bounded initial render batches of 40; explicit manual correction path.'}
 if not a.tables_only:
  report['runtime'],report['manual']=runtime(root,not a.capture_before)
  a.report.with_name(a.report.stem+'_captured.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  if not a.capture_before:report['semantics']=semantic_checks(report)
  if a.compare_capture:report['comparison']=compare(json.loads(a.compare_capture.read_bytes()),report)
 report['passed']=True;a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Dot/greft PASS',flush=True)
if __name__=='__main__':main()
