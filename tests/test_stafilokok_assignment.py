"""Portable exhaustive rule comparison and real app-path regression for stafilokok."""
import argparse,csv,gc,hashlib,importlib.util,io,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stafilokok_helpers',HERE/'test_reviewed_at_sync.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
OLD='葡萄球菌';NEW='葡球菌'
CONTROLS={'turment':'虐','tortur':'虐ᵀᵀ','testikit':'丸ᵀ炎ᵀ','orkidit':'丸ᴼ炎ᵀ',
          'uv':'葡萄','uve':'葡萄膜','uveit':'葡萄膜炎ᵀ','vit':'葡','ananas':'菠','jakv':'菠蜜','las':'放',
          'prioritat':'优先','strut':'鸵','sinergi':'协同','oliv':'榄','oval':'椭圆','elips':'椭圆ᴱ'}
WORDS=['stafilokoko','stafilokokoj','stafilokokon','stafilokokojn','stafilokoka','stafilokokaj',
       'stafilokokajn','stafilokoke','stafilokokozo','Stafilokoko','STAFILOKOKO',
       '@stafilokok@o','@stafilokoko@','@stafilokok@oj','@Stafilokok@o','@STAFILOKOK@O',
       'antistafilokoka','%stafilokoko%','%@stafilokok@%','@stafilokok@o & %stafilokoko%',
       'turmenti','torturi','@turment@i','@tortur@i','testikito','orkidito','@testikit@o','@orkidit@o',
       'uvo','uveo','uveito','vito','ananaso','jakvo','prioritato','lasi','emancipi','struto','sinergio',
       'olivo','ovalo','elipso','semajntagoj','@semajn@tagoj','ŝakisto']

def neutral(value,display):
    def visit(match):
        spelling=h.plain(match[2])
        if spelling.lower()!='stafilokok':return match[0]
        assert match[1]==display,(spelling,match[1],display)
        return '<reviewed>'+spelling+'</reviewed>'
    return h.RUBY.sub(visit,value)

def tables(root,baseline):
    report=[]
    for lang in ('JA','ZH','KO'):
        data=root/f'Esperanto-Kanji-Ruby-{lang}/app_data'
        path=data/h.MODES['kanji'][0];current=json.loads(path.read_bytes())
        old=json.loads(h.baseline_bytes(path)) if baseline else None
        counts={}
        for group,rows in current.items():
            changed=0
            if old:assert len(rows)==len(old[group])
            for i,row in enumerate(rows):
                actual=neutral(row[1],NEW)
                if old:
                    previous=old[group][i]
                    assert previous[:1]+previous[2:]==row[:1]+row[2:]
                    assert neutral(previous[1],OLD)==actual,(lang,group,row[0])
                    assert h.original(previous[1],'kanji')==h.original(row[1],'kanji')
                    changed+=previous!=row
            counts[group]={'rows':len(rows),'changed':changed if old else None}
        local={r[0]:r[1] for r in current[h.LOCAL]}
        for spelling in ('stafilokok','Stafilokok','STAFILOKOK'):
            assert h.visible(local[spelling])==NEW
        csvpath=data/h.CSV_NAME;raw=csvpath.read_bytes();mapping=dict(csv.reader(io.StringIO(raw.decode('utf-8'))))
        assert mapping['stafilokok']==NEW
        for name,value in CONTROLS.items():assert mapping[name]==value,(name,mapping[name])
        if baseline:
            previous=h.baseline_bytes(csvpath)
            assert previous.count(b'stafilokok,')==1
            assert previous.replace(('stafilokok,'+OLD).encode(),('stafilokok,'+NEW).encode())==raw
            for other in data.iterdir():
                if not other.is_file() or other.name in {h.CSV_NAME,h.MODES['kanji'][0],h.MODES['pure'][0]}:continue
                assert other.read_bytes()==h.baseline_bytes(other),other.name
        if lang=='JA':
            pure=json.loads((data/h.MODES['pure'][0]).read_bytes())
            for group,rows in current.items():assert pure[group]==[[r[0],h.strip_ruby(r[1]),*r[2:]] for r in rows]
            del pure
        report.append({'language':lang,'groups':counts})
        print('tables',lang,'PASS',flush=True);del current,old;gc.collect()
    return report

def runtime(root,expected):
    result=[];manual=[]
    for lang in ('JA','ZH','KO'):
        app=root/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
        engine=h.load_module(app,'esp_text_replacement_module.py','stafilokok_engine_'+lang)
        overlay=h.load_module(app,'esp_overlay_module.py','stafilokok_overlay_'+lang)
        correction=overlay.build_correction('stafilokok/o',str(data))
        for mode,(filename,fmt) in h.MODES.items():
            owner=root/'Esperanto-Kanji-Ruby-JA/app_data' if mode=='pure' else data
            payload=json.loads((owner/filename).read_bytes());key='ruby' if mode=='ruby' else 'kanji'
            user=overlay.load_overlay_entries(str(data),key)
            if mode=='pure':user=[[a,h.strip_ruby(b),c] for a,b,c in user]
            payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],user)
            first=h.render(engine,data,payload,WORDS,fmt)
            auto=overlay.auto_overlay_entries(' ◆ '.join(first.values()),str(data),key)
            if mode=='pure':auto=[[a,h.strip_ruby(b),c] for a,b,c in auto]
            if auto:
                payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],auto)
                final=h.render(engine,data,payload,WORDS,fmt)
            else:final=first
            for word,value in final.items():
                if mode!='pure':
                    source=word[1:-1] if word.startswith('%') and word.endswith('%') else word.replace('@','').replace('%','')
                    assert h.original(value,mode)==source,(mode,word,value)
                if mode!='ruby' and word in ('stafilokoko','@stafilokok@o','@stafilokoko@'):
                    assert h.visible(value)==expected+'o',(mode,word,value)
                if mode!='ruby' and word in ('turmenti','torturi','testikito','orkidito'):
                    rt=word[:-1];assert h.visible(value)==CONTROLS[rt]+word[-1]
                result.append({'language':lang,'mode':mode,'input':word,'first':first[word],'final':value})
            pairs=correction[key]
            expected_pairs={w:h.strip_ruby(v) if mode=='pure' else v for w,v in pairs}
            if mode!='ruby':
                for word,value in expected_pairs.items():assert h.visible(value)==expected+word[-1]
            payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],[[w,v,f'${95000000+i}$'] for i,(w,v) in enumerate(expected_pairs.items())])
            actual=h.render(engine,data,payload,list(expected_pairs),fmt)
            assert actual==expected_pairs
            manual.append({'language':lang,'mode':mode,'forms':len(actual),'passed':True})
            print('runtime',lang,mode,len(final),'manual',len(actual),'PASS',flush=True)
            del payload;gc.collect()
    return result,manual

def compare(before,after):
    assert len(before)==len(after)
    for a,b in zip(before,after):
        assert (a['language'],a['mode'],a['input'])==(b['language'],b['mode'],b['input'])
        for phase in ('first','final'):
            if a['mode']=='ruby':assert a[phase]==b[phase]
            elif a['mode']=='kanji':assert neutral(a[phase],OLD)==neutral(b[phase],NEW)
            else:assert a[phase].replace(OLD,NEW)==b[phase]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app-root',type=Path)
    p.add_argument('--baseline-ref');p.add_argument('--capture-before',action='store_true')
    p.add_argument('--compare-capture',type=Path);p.add_argument('--tables-only',action='store_true')
    p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    root=a.app_root.resolve() if a.app_root else HERE.parent
    h.ROOT=root;h.BASELINE=a.baseline_ref
    report={'passed':False,'baseline_ref':a.baseline_ref,'phase':'before' if a.capture_before else 'after'}
    if not a.capture_before:report['tables']=tables(root,a.baseline_ref)
    if not a.tables_only:
        report['runtime'],report['manual']=runtime(root,OLD if a.capture_before else NEW)
        if a.compare_capture:compare(json.loads(a.compare_capture.read_text(encoding='utf-8'))['runtime'],report['runtime'])
    report['passed']=True
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('stafilokok regression PASS',flush=True)
if __name__=='__main__':main()
