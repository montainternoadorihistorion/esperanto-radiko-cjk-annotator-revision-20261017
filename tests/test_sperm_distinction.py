"""Independent complete-table, semantic and live-path sperm distinction audit."""
import argparse,csv,gc,hashlib,importlib.util,io,json,re,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sperm_helpers',HERE/'test_reviewed_at_sync.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
VALUES={} # Runtime uses exact complete expectations below, not implementation code.
DISPLAYS={'spermat':('精ˢ','精子'),'spermati':('精ˢᴵ','精子ˢᴵ'),'spermatocit':('精ˢ胞ᶜᴵ','精子胞ᶜᴵ'),'spermatofit':('精ˢ植ᶠ','精子植ᶠ'),'spermatogenez':('精ˢ源ᴳ','精子源ᴳ'),'silf':('精ˢᴸ','精ˢ'),'spermatozo':(None,'精子ˢᶻ')}
NEW_GLOSSES={'JA':{'sperm':'精液','spermat':'精子／種子（複合語要素）','spermati':'植物の不動性生殖細胞'},'ZH':{'sperm':'精液','spermat':'精子／种子（复合词成分）','spermati':'植物的不动生殖细胞'},'KO':{'sperm':'정액','spermat':'정자／종자（복합어 요소）','spermati':'식물의 비운동성 생식세포'}}
OLD_GLOSSES={'JA':{'sperm':{'精子','精液','[生]精液','種子'},'spermat':{'精子'},'spermati':{'精子'}},'ZH':{'sperm':{'精子','精液','种子'},'spermat':{'精子'},'spermati':{'精胞'}},'KO':{'sperm':{'정자','정액','씨','종자'},'spermat':{'정자'},'spermati':{'정자'}}}
GENERAL={'sperm','spermo','sperma','spermon','spermoj','spermojn','sperman','spermaj','spermajn','spermuj','spermelĵet','spermodukt','spermosak','spermotubet'}
CSV_LANG={'エスペラント語根-日本語訳ルビ対応リスト.csv':'JA','世界语词根-中文注释对应列表.csv':'ZH','에스페란토 어근-한국어 번역 루비 대응 목록.csv':'KO'}
WHOLE={'JA':{'spermatocit':'精母細胞','spermatogenez':'精子形成'},'ZH':{'spermatocit':'精母细胞','spermatogenez':'精子形成'},'KO':{'spermatocit':'정모세포','spermatogenez':'정자 형성'}}
WORDS=[];MANUAL=[];CONTROLS={}
batch=h.render
def bounded_render(engine,data,payload,words,fmt):
 result={}
 for at in range(0,len(words),40):result.update(batch(engine,data,payload,words[at:at+40],fmt))
 return result
h.render=bounded_render
def checked_gloss(lang,root,value,context):
 if root not in NEW_GLOSSES[lang]:return value
 assert value in OLD_GLOSSES[lang][root]|{NEW_GLOSSES[lang][root]},(lang,root,value,context)
 word=context.lower().replace('/','').strip()
 if root=='sperm':
  if word in ('endosperm','perisperm'):return {'JA':'種子','ZH':'种子','KO':'씨'}[lang]
  if word=='spermicid':return value
  assert word in GENERAL,(word,root,value)
  return value if value in ('精液','[生]精液','정액') else NEW_GLOSSES[lang][root]
 if root=='spermat' and word in ('spermatocit','spermatogenez'):return value
 return NEW_GLOSSES[lang][root]
def kanji_neutral(value,after):
 def visit(m):
  spelling=h.plain(m[2]);rt=spelling.lower()
  if rt not in DISPLAYS:return m[0]
  assert m[1]==DISPLAYS[rt][int(after)],(rt,m[1],after)
  return '<reviewed>'+spelling+'</reviewed>'
 return h.RUBY.sub(visit,value)
def annotation_pair(before,after,lang,context):
 old=list(h.RUBY.finditer(before));new=list(h.RUBY.finditer(after));assert len(old)==len(new),(context,old,new)
 aa=before;bb=after
 for x,y in zip(old,new):
  spelling=h.plain(x[1]);assert h.plain(y[1])==spelling
  root=spelling.lower();gloss=h.plain(x[2]);expected=checked_gloss(lang,root,gloss,context)
  assert h.plain(y[2])==expected,(lang,context,root,gloss,h.plain(y[2]),expected)
  if expected!=gloss:
   aa=aa.replace(x[0],'<annotation>'+spelling+'</annotation>');bb=bb.replace(y[0],'<annotation>'+spelling+'</annotation>')
 assert aa==bb,(context,aa,bb)
def tables(root,old_bytes):
 report=[]
 for lang in ('JA','ZH','KO'):
  data=root/f'Esperanto-Kanji-Ruby-{lang}/app_data';stats={}
  for mode in ('kanji','ruby'):
   path=data/h.MODES[mode][0];current=json.loads(path.read_bytes());before=json.loads(old_bytes(path)) if old_bytes else None
   if before:assert list(current)==list(before)
   for group,rows in current.items():
    keys=[(r[0],r[2]) for r in rows];assert len(keys)==len(set(keys))
    counts={'rows':len(rows),'existing_changed':0,'added':[]}
    if before:
     previous=before[group];old_keys=[(r[0],r[2]) for r in previous];old_set=set(old_keys)
     assert [k for k in keys if k in old_set]==old_keys,(lang,mode,group,'order')
     added=[r for r in rows if (r[0],r[2]) not in old_set]
     expected_root='spermat' if group==h.GLOBAL else ('spermatozo' if group==h.LOCAL and mode=='kanji' else None)
     assert len(added)==(3 if expected_root else (6 if mode=='ruby' and group==h.LOCAL else 0)),(lang,mode,group,added)
     if mode=='ruby' and group==h.LOCAL:
      assert {r[0].lower() for r in added}==set(WHOLE[lang])
      for r in added:
       assert h.original(r[1],'ruby')==r[0]
       pieces=list(h.RUBY.finditer(r[1]));assert [h.plain(x[1]).lower() for x in pieces]==['spermat','cit' if r[0].lower().endswith('cit') else 'genez']
       assert h.plain(pieces[0][2])=={'JA':'精子','ZH':'精子','KO':'정자'}[lang]
       assert h.plain(pieces[1][2])==({'JA':'細胞','ZH':'细胞','KO':'세포'} if r[0].lower().endswith('cit') else {'JA':'発生','ZH':'发生','KO':'발생'})[lang]
     if expected_root:
      assert {r[0] for r in added}=={expected_root,expected_root.upper(),expected_root.title()}
      for r in added:
       assert h.original(r[1],mode)==r[0]
       if mode=='kanji':assert h.visible(r[1])==DISPLAYS[expected_root][1]
       else:assert h.plain(next(h.RUBY.finditer(r[1]))[2])==NEW_GLOSSES[lang][expected_root]
     counts['added']=[r[0] for r in added];bykey={(r[0],r[2]):r for r in rows}
     for a in previous:
      b=bykey[(a[0],a[2])];assert a[:1]+a[2:]==b[:1]+b[2:];assert h.original(a[1],mode)==h.original(b[1],mode)
      if mode=='kanji':
       if a[0].lower()=='spermatozo':assert a[1]==a[0] and h.visible(b[1])=='精子ˢᶻ'
       else:assert kanji_neutral(a[1],False)==kanji_neutral(b[1],True),(lang,group,a[0])
      else:annotation_pair(a[1],b[1],lang,a[0])
      counts['existing_changed']+=a!=b
    stats[mode+'/'+group]=counts
  mapping=dict(csv.reader((data/h.CSV_NAME).read_text(encoding='utf-8').splitlines()))
  for r,(_,v) in DISPLAYS.items():assert mapping[r]==v
  for r,v in CONTROLS.items():assert mapping[r]==v,(r,mapping.get(r),v)
  if old_bytes:
   old=dict(csv.reader(old_bytes(data/h.CSV_NAME).decode('utf-8').splitlines()));assert set(mapping)==set(old)|{'spermatozo'}
   assert all(mapping[r]==(DISPLAYS[r][1] if r in DISPLAYS else v) for r,v in old.items())
   for path in data.iterdir():
    if not path.is_file() or path.name in {h.CSV_NAME,h.MODES['kanji'][0],h.MODES['ruby'][0],h.MODES['pure'][0],'word_anno.json',*CSV_LANG}:continue
    assert path.read_bytes()==old_bytes(path),path.name
   for name,cl in CSV_LANG.items():
    path=data/name
    if not path.exists():continue
    old=old_bytes(path).decode('utf-8').splitlines(keepends=True);new=path.read_text(encoding='utf-8',newline='') if False else path.read_bytes().decode('utf-8').splitlines(keepends=True)
    has_full=any(x.startswith('spermat,') for x in old)
    assert len(new)==len(old)+(2 if has_full else 0)
    if has_full:assert [next(csv.reader([x])) for x in new[-2:]]==[[r,v] for r,v in WHOLE[cl].items()]
    for a,b in zip(old,new):
     x=next(csv.reader([a]));y=next(csv.reader([b]));assert x[:1]==y[:1]
     if x and x[0] in NEW_GLOSSES[cl]:assert len(x)==len(y)==2 and y[1]==checked_gloss(cl,x[0],x[1],x[0])
     else:assert a==b
   old=json.loads(old_bytes(data/'word_anno.json'));new=json.loads((data/'word_anno.json').read_bytes());assert list(new)==list(old)+(['spermat'] if 'spermat' not in old else [])
   for w,pairs in old.items():assert new[w]==[[rt,checked_gloss(lang,rt,v,w)] for rt,v in pairs]
   assert new['spermat']==[['spermat',NEW_GLOSSES[lang]['spermat']]]
  if lang=='JA':
   kanji=json.loads((data/h.MODES['kanji'][0]).read_bytes());pure=json.loads((data/h.MODES['pure'][0]).read_bytes())
   assert pure=={g:[[r[0],h.strip_ruby(r[1]),*r[2:]] for r in rr] for g,rr in kanji.items()}
   del kanji,pure
  report.append({'language':lang,'groups':stats});print('tables',lang,'PASS',flush=True);gc.collect()
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
                    rt=word[:-1].lower();expected=CONTROLS.get(rt)
                    if rt=='spermatozo' and not after:expected='spermatozo'
                    assert expected is not None,rt
                    assert h.visible(value)==(word if rt=='spermatozo' and not after else expected+word[-1]),(word,value,expected)
                manual_results.append({'language':lang,'mode':mode,'input':word,'output':value})
            print('runtime',lang,mode,len(final),'manual',len(actual),'PASS',flush=True)
            del payload;gc.collect()
    results.sort(key=lambda r:(r['language'],r['mode'],r['input']));manual_results.sort(key=lambda r:(r['language'],r['mode'],r['input']))
    return results,manual_results


def semantic_checks(report):
 rows={(r['language'],r['mode'],r['input']):r for r in report['runtime']}
 normal={'spermatozoo':'精子ˢᶻo','spermato':'精子o','spermatio':'精子ˢᴵo','spermatocito':'精子o胞ᶜᴵo','spermatofitoj':'精子o植ᶠoj','spermatogenezo':'精子o源ᴳo','silfo':'精ˢo','spermo':'精液o','ĉuro':'精液ᶜ̂o','spermatido':'spermatido','spermatogonio':'spermatogonio'}
 for lang in ('JA','ZH','KO'):
  for word,expected in normal.items():
   for mode in ('kanji','pure'):assert rows[(lang,mode,word)]['visible']==expected,(lang,mode,word,rows[(lang,mode,word)]['visible'],expected)
  for rt,(_,v) in DISPLAYS.items():
   for mode in ('kanji','pure'):assert rows[(lang,mode,'@'+rt+'@o')]['visible']==v+'o'
  for word in ('spermo','ĉuro','@sperm@o','@ĉur@o'):
   value=rows[(lang,'ruby',word)]['final'];glosses=' '.join(h.plain(m[2]) for m in h.RUBY.finditer(value))
   assert ('정액' if lang=='KO' else '精液') in glosses and ('정자' if lang=='KO' else '精子') not in glosses,(lang,word,value)
  for word in ('spermatofitoj','@spermatofit@oj','@spermatofitoj@'):
   assert {'JA':'種子植物','ZH':'种子植物','KO':'종자식물'}[lang] in h.plain(rows[(lang,'ruby',word)]['final'])
  for word in ('spermatio','@spermati@o'):
   assert NEW_GLOSSES[lang]['spermati'] in h.plain(rows[(lang,'ruby',word)]['final'])
  for word in ('spermatozoo','@spermatozo@o'):
   assert ('정자' if lang=='KO' else '精子') in h.plain(rows[(lang,'ruby',word)]['final'])
  assert {'JA':'種子','ZH':'种子','KO':'종자'}[lang] in h.plain(rows[(lang,'ruby','@spermat@ofitoj')]['final'])
 manual={(r['language'],r['mode'],r['input']):r['output'] for r in report['manual']}
 for lang in ('JA','ZH','KO'):
  for rt,meaning in WHOLE[lang].items():assert meaning in h.plain(manual[(lang,'ruby',rt+'o')])
  for word in ('spermatocito','@spermatocit@o'):
   cit=[h.plain(m[2]) for m in h.RUBY.finditer(rows[(lang,'ruby',word)]['final']) if h.plain(m[1]).lower()=='cit'];assert cit==[{'JA':'細胞','ZH':'细胞','KO':'세포'}[lang]]
 return {'normal_expectations':normal,'plant_meanings':True,'spermati_nonmotile_plant_cell':True,'semen_cell_distinction':True}
def compare(before,after):
 exceptions=[]
 for section,fields in (('runtime',('first','final')),('manual',('output',))):
  assert len(before[section])==len(after[section])
  for a,b in zip(before[section],after[section]):
   assert (a['language'],a['mode'],a['input'])==(b['language'],b['mode'],b['input'])
   for phase in fields:
    if a[phase]==b[phase] or a['mode']=='pure':continue
    if a['mode']=='kanji':
     equal=kanji_neutral(a[phase],False)==kanji_neutral(b[phase],True)
     if not equal:
      # Only the two explicitly authorized roots may change segmentation.
      assert re.search(r'spermat(?:o|a(?:j?n)?(?=[@% ]|$)|e(?=[@% ]|$)|i(?=[@% ]|$)|[aiou]s(?=[@% ]|$)|u(?=[@% ]|$)|@|/|$)',a['input'],re.I),(section,a,b)
      assert h.original(a[phase],'kanji')==h.original(b[phase],'kanji')
      exceptions.append({'section':section,'input':a['input'],'language':a['language'],'mode':a['mode'],'phase':phase,'before':a[phase],'after':b[phase]})
    else:
     try:annotation_pair(a[phase],b[phase],a['language'],a['input'].replace('@','').replace('%',''))
     except AssertionError:
      # Source tables proved every gloss and boundary. Runtime combinations use
      # word forms/endings; validate reviewed pieces without inferring glosses
      # from the entire synthetic multiword input.
      aa=a[phase];bb=b[phase]
      def neut(s):return h.RUBY.sub(lambda m: '<ann>'+h.plain(m[1])+'</ann>' if h.plain(m[1]).lower() in ('sperm','spermat','spermati') or (h.plain(m[1]).lower()=='cit' and 'spermatocit' in a['input'].lower()) else m[0],s)
      if neut(aa)!=neut(bb):
       assert re.search(r'spermat(?:o|a(?:j?n)?(?=[@% ]|$)|e(?=[@% ]|$)|i(?=[@% ]|$)|[aiou]s(?=[@% ]|$)|u(?=[@% ]|$)|@|/|$)',a['input'],re.I),(section,a,b)
       assert h.original(aa,'ruby')==h.original(bb,'ruby')
       exceptions.append({'section':section,'input':a['input'],'language':a['language'],'mode':'ruby','phase':phase,'before':aa,'after':bb})
 return {'authorized_boundary_changes':exceptions,'other_runtime_deltas_exact_reviewed_root_pieces':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('--app-root',type=Path);p.add_argument('--baseline-zip',type=Path);p.add_argument('--inputs',type=Path);p.add_argument('--compare-capture',type=Path);p.add_argument('--tables-only',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 root=a.app_root or HERE.parent
 config=json.loads((a.inputs or HERE/'sperm_distinction_inputs.json').read_bytes())
 global WORDS,MANUAL,CONTROLS
 WORDS=config['WORDS'];MANUAL=config['MANUAL'];CONTROLS=config['CONTROLS'];CONTROLS.update({r:v[1] for r,v in DISPLAYS.items()})
 old=None
 if a.baseline_zip:
  z=zipfile.ZipFile(a.baseline_zip);old=lambda path:z.read(path.relative_to(root).as_posix())
 report={'passed':False,'assignments':DISPLAYS,'tables':tables(root,old),'method':'Actual current application runtime with default and automatic overlays; 40 independent-input bounded batches, plus manual correction pathway.'}
 if not a.tables_only:
  report['runtime'],report['manual']=runtime(root,True)
  capture_path=a.report.with_name(a.report.stem+'_captured.json');capture_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  report['semantics']=semantic_checks(report)
  if a.compare_capture:report['comparison']=compare(json.loads(a.compare_capture.read_bytes()),report)
 report['passed']=True;a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Sperm distinction PASS',flush=True)
if __name__=='__main__':main()
