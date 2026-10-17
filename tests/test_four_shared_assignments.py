"""Portable exhaustive rule/byte and actual app-path regression for four assignments.

No private generation code is imported. Use --baseline-zip for a file snapshot,
or --baseline-ref in a repository. Historical evidence files are never changed.
"""
import argparse,csv,gc,hashlib,importlib.util,io,json,re,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('four_shared_helpers',HERE/'test_reviewed_at_sync.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
VALUES={'psitak':('鹦鹉','鹦ᴾˢ'),'uv':('葡萄','葡ᵁ'),'limon':('柠檬','柠'),'limonad':('柠檬水','柠水')}
CONTROLS={'vit':'葡','uve':'葡萄膜','uveit':'葡萄膜炎ᵀ','papag':'鹦',
 'konkord':'和合','observatori':'天文台','majest':'庄严','subtil':'精细',
 'turment':'虐','tortur':'虐ᵀᵀ','testikit':'丸ᵀ炎ᵀ','orkidit':'丸ᴼ炎ᵀ',
 'ananas':'菠','jakv':'菠蜜','las':'放','emancip':'放ᴱ','prioritat':'优先',
 'strut':'鸵','sinergi':'协同','oliv':'榄','oval':'椭圆','elips':'椭圆ᴱ','stafilokok':'葡球菌'}
TARGET_WORDS=[form for root in VALUES for base in
 (root+'o',root+'oj',root+'on',root+'ojn',root+'a',root+'aj',root+'ajn',root+'e',
  '@'+root+'@o','@'+root+'o@','@'+root+'@ojn') for form in (base,base.title(),base.upper())]
EXTRA=['psitakedoj','psitakozo','uvujo','uvbero','uvsuko','uvvino','limonujo','limonsuko','limonŝelo',
 'limonadbotelo','limonado','uveo','uveito','vito','papago','konkordo','observatorio','majesto','subtila',
 'turmenti','torturi','testikito','orkidito','@testikit@o','@orkidit@o',
 'ananaso','jakvo','prioritato','prioro','lasi','emancipi','struto','sinergio','olivo','ovalo','elipso',
 'stafilokoko','@stafilokok@o','semajntagoj','@semajn@tagoj','semajn semajn','ŝakisto',
 'uvo uveo uveito vito','@uv@o @uve@o @uveit@o @vit@o','@psitak@o @papag@o',
 '@limon@o @limonad@o','%uvo%','%@uv@%','@uv@o & %uvo%','@psitak & uv & limon & limonad@',
 '@amiko & amiko@']
WORDS=list(dict.fromkeys(TARGET_WORDS+EXTRA))
MANUAL=['psitak/o','uv/o','limon/o','limonad/o','uve/o','uveit/o','vit/o','papag/o','konkord/o','observatori/o']

def neutral(value,after):
    def visit(match):
        spelling=h.plain(match[2]);root=spelling.lower()
        if root not in VALUES:return match[0]
        expected=VALUES[root][int(after)]
        assert match[1]==expected,(root,match[1],expected)
        return '<reviewed>'+spelling+'</reviewed>'
    return h.RUBY.sub(visit,value)

def baseline_reader(root,baseline_zip,baseline_ref):
    if baseline_zip:
        archive=zipfile.ZipFile(baseline_zip)
        return lambda p:archive.read(p.relative_to(root).as_posix())
    if baseline_ref:
        h.ROOT=root;h.BASELINE=baseline_ref
        return h.baseline_bytes
    return None

def tables(root,old_bytes):
    report=[]
    for lang in ('JA','ZH','KO'):
        data=root/f'Esperanto-Kanji-Ruby-{lang}/app_data'
        path=data/h.MODES['kanji'][0];current=json.loads(path.read_bytes())
        before=json.loads(old_bytes(path)) if old_bytes else None
        if before is not None:assert list(current)==list(before)
        counts={}
        for group,rows in current.items():
            changed=0;target_pieces={r:0 for r in VALUES}
            if before is not None:assert len(rows)==len(before[group])
            for i,row in enumerate(rows):
                actual=neutral(row[1],True)
                for m in h.RUBY.finditer(row[1]):
                    rootname=h.plain(m[2]).lower()
                    if rootname in target_pieces:target_pieces[rootname]+=1
                if before is not None:
                    previous=before[group][i]
                    assert previous[:1]+previous[2:]==row[:1]+row[2:]
                    assert neutral(previous[1],False)==actual,(lang,group,row[0])
                    assert h.original(previous[1],'kanji')==h.original(row[1],'kanji')
                    changed+=previous!=row
            counts[group]={'rows':len(rows),'changed':changed if before is not None else None,'target_pieces':target_pieces}
        local={r[0]:r[1] for r in current[h.LOCAL]}
        for rootname,(_,expected) in VALUES.items():
            for spelling in (rootname,rootname.title(),rootname.upper()):
                assert h.visible(local[spelling])==expected,(spelling,local[spelling])
        csvpath=data/h.CSV_NAME;raw=csvpath.read_bytes();mapping=dict(csv.reader(io.StringIO(raw.decode('utf-8'))))
        for name,(_,expected) in VALUES.items():assert mapping[name]==expected
        for name,expected in CONTROLS.items():assert mapping[name]==expected,(name,mapping.get(name),expected)
        unchanged=[]
        if old_bytes:
            previous=old_bytes(csvpath);expected=previous
            for name,(old,new) in VALUES.items():
                a=(name+','+old+'\n').encode();b=(name+','+new+'\n').encode()
                assert expected.count(a)==1,(name,expected.count(a))
                expected=expected.replace(a,b)
            assert expected==raw
            for other in data.iterdir():
                if not other.is_file() or other.name in {h.CSV_NAME,h.MODES['kanji'][0],h.MODES['pure'][0]}:continue
                assert other.read_bytes()==old_bytes(other),other.name
                unchanged.append(other.name)
        if lang=='JA':
            pure=json.loads((data/h.MODES['pure'][0]).read_bytes())
            for group,rows in current.items():assert pure[group]==[[r[0],h.strip_ruby(r[1]),*r[2:]] for r in rows]
            del pure
        report.append({'language':lang,'groups':counts,'unchanged_data_files':unchanged})
        print('tables',lang,'PASS',flush=True);del current,before;gc.collect()
    return report

def runtime(root,after):
    results=[];manual_results=[]
    for lang in ('JA','ZH','KO'):
        app=root/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
        engine=h.load_module(app,'esp_text_replacement_module.py','four_shared_engine_'+lang)
        overlay=h.load_module(app,'esp_overlay_module.py','four_shared_overlay_'+lang)
        corrections=[(entry,overlay.build_correction(entry,str(data))) for entry in MANUAL]
        kanji=None;kanji_manual=None
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
                if mode!='ruby':
                    for rt,values in VALUES.items():
                        expected=values[int(after)]
                        for sourcebase,ending in ((rt+'o','o'),('@'+rt+'@o','o'),('@'+rt+'o@','o'),(rt+'ojn','ojn')):
                            for form in (sourcebase,sourcebase.title(),sourcebase.upper()):
                                if word==form:
                                    suffix=word.replace('@','')[-len(ending):]
                                    assert h.visible(value)==expected+suffix,(mode,word,value,expected+suffix)
                if mode=='pure':assert value==h.visible(kanji[word]),(lang,word,value,kanji[word])
                results.append({'language':lang,'mode':mode,'input':word,'first':first[word],'final':value,
                                'visible':h.visible(value),'restored':h.original(value,mode) if mode!='pure' else None})
            if mode=='kanji':kanji=final
            expected_pairs={w:h.strip_ruby(v) if mode=='pure' else v for _,c in corrections for w,v in c[key]}
            payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],[[w,v,f'${97000000+i}$'] for i,(w,v) in enumerate(expected_pairs.items())])
            actual=h.render(engine,data,payload,list(expected_pairs),fmt)
            assert actual==expected_pairs
            if mode=='pure':assert actual=={w:h.visible(v) for w,v in kanji_manual.items()}
            if mode=='kanji':kanji_manual=actual
            for word,value in actual.items():
                if mode!='ruby':
                    rt=word[:-1].lower()
                    expected=VALUES[rt][int(after)] if rt in VALUES else CONTROLS[rt]
                    assert h.visible(value)==expected+word[-1],(word,value,expected)
                manual_results.append({'language':lang,'mode':mode,'input':word,'output':value})
            print('runtime',lang,mode,len(final),'manual',len(actual),'PASS',flush=True)
            del payload;gc.collect()
    return results,manual_results

def compare(before,after):
    for section,fields in (('runtime',('first','final')),('manual',('output',))):
        assert len(before[section])==len(after[section])
        for a,b in zip(before[section],after[section]):
            assert (a['language'],a['mode'],a['input'])==(b['language'],b['mode'],b['input'])
            for phase in fields:
                if a['mode']=='ruby':assert a[phase]==b[phase],(section,a['input'])
                elif a['mode']=='kanji':assert neutral(a[phase],False)==neutral(b[phase],True),(section,a['input'])
                # Pure is checked against visible kanji output in both captures.

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app-root',type=Path)
    b=p.add_mutually_exclusive_group();b.add_argument('--baseline-ref');b.add_argument('--baseline-zip',type=Path)
    p.add_argument('--capture-before',action='store_true');p.add_argument('--compare-capture',type=Path)
    p.add_argument('--tables-only',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    root=a.app_root.resolve() if a.app_root else HERE.parent
    report={'passed':False,'baseline_ref':a.baseline_ref,'baseline_snapshot':a.baseline_zip.name if a.baseline_zip else None,
            'phase':'before' if a.capture_before else 'after','assignments':VALUES,
            'limitations':['Preserves existing annotation and segmentation; passing does not establish semantic correctness of every annotation.']}
    if not a.capture_before:report['tables']=tables(root,baseline_reader(root,a.baseline_zip,a.baseline_ref))
    if not a.tables_only:
        report['runtime'],report['manual']=runtime(root,not a.capture_before)
        if a.compare_capture:compare(json.loads(a.compare_capture.read_text(encoding='utf-8')),report)
    report['passed']=True
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('four shared assignment regression PASS',flush=True)
if __name__=='__main__':main()
