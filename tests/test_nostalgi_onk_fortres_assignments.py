"""Portable exhaustive rule/byte and actual app-path regression for nostalgi/onk/fortres assignments.

No private generation code is imported. Use --baseline-zip for a file snapshot,
or --baseline-ref in a repository. Historical evidence files are never changed.
"""
import argparse,csv,gc,hashlib,importlib.util,io,json,re,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nostalgi_onk_fortres_helpers',HERE/'test_reviewed_at_sync.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
VALUES={'nostalgi': ('怀旧', '怀ᴺ'), 'onk': ('肿瘤', '瘤ᴼ'), 'fortres': ('堡垒', '堡ᶠᴿ')}
MIRRORS={"onkogen":("肿瘤生ᴳ","瘤ᴼ生ᴳ"),"onkologi":("肿瘤学ᴸᴳ","瘤ᴼ学ᴸᴳ")}
ALL_VALUES={**VALUES,**MIRRORS}
CONTROLS={**{'krep': '皱布', 'difrakt': '绕射', 'mortez': '卯', 'meger': '恶女', 'sin': '怀', 'tumor': '瘤ᵀ', 'fuort': '堡', 'burg': '堡ᴮ', 'koincid': '巧合', 'kombinaci': '合ᴷᶜ', 'karikatur': '讽', 'sarkasm': '讽ˢ', 'spermat': '精ˢ', 'ĉur': '精液ᶜ̂', 'sperm': '精液', 'satir': '讽刺', 'spermati': '精ˢᴵ'},'buf':'蛤蟆','lofi':'蛤蟆鱼','sutur':'缝ˢᴿ','fraj':'卵ᶠ','prism':'棱镜','protez':'假体','ranc':'酸败','kanajl':'恶棍','boks':'拳击','impertinent':'放肆','galer':'桨船','risort':'簧','anĉ':'簧ᴬ','lantern':'灯ᴸᴺ','lubrik':'滑ᴸ','hangar':'棚库','kontest':'异议','cisticerk':'囊尾虫','kruc':'十字','observatori':'观台','pland':'足底','lamp':'灯','lucern':'灯ᴸᶜ','glit':'滑','sinoviit':'滑ˢᴺ炎ᵀ','vit':'葡','uv':'葡ᵁ','psitak':'鹦ᴾˢ','limon':'柠','limonad':'柠水','papag':'鹦',
 'konkord':'和合','uve':'葡膜','uveit':'葡膜炎ᵀ','observ':'观','astronom':'星ᴬ学ᴺᴼ','astrolog':'星ᴬ学家','meteorolog':'气ᴹᴿ学家','majest':'庄严','subtil':'精细',
 'turment':'虐','tortur':'虐ᵀᵀ','testikit':'丸ᵀ炎ᵀ','orkidit':'丸ᴼ炎ᵀ',
 'ananas':'菠','jakv':'菠蜜','las':'放','emancip':'放ᴱ','prioritat':'优先',
 'strut':'鸵','sinergi':'协同','oliv':'榄','oval':'椭圆','elips':'椭圆ᴱ','stafilokok':'葡球菌'}
TARGET_WORDS=[form for root in VALUES for base in
 (root+'o',root+'oj',root+'on',root+'ojn',root+'a',root+'aj',root+'ajn',root+'e',
  '@'+root+'@o','@'+root+'o@','@'+root+'@ojn') for form in (base,base.title(),base.upper())]
PREVIOUS_TARGETS=[form for root in ('psitak','uv','limon','limonad','uve','uveit','observatori') for base in
 (root+'o',root+'oj',root+'on',root+'ojn',root+'a',root+'aj',root+'ajn',root+'e','@'+root+'@o','@'+root+'o@','@'+root+'@ojn') for form in (base,base.title(),base.upper())]
EXTRA=['nostalgio', 'nostalgiaj', 'nostalgie', 'nostalgii', 'nostalgieco', 'nostalgiaj memoroj', 'nostalgio al la hejmo', 'nostalgio pri la pasinteco', 'onkogena', '@onkogen@a', 'onkologia', 'onkologio', '@onkologi@o', 'onkologo', 'onkologiaj', 'onkoj', 'onkojn', 'fortresoj', 'fortresoj', 'fortresa', 'fortresmuro', 'fortresurbo', 'fortresano', '@nostalgi@o', '@onk@o', '@fortres@o', 'koincidi', '@koincid@i', 'sino', 'tumoro', 'fuorto', 'burgo', 'kombinacio', 'karikaturo', 'sarkasmo', 'spermo', 'ĉuro', 'spermat', 'spermatio', 'satira', '@nostalgi & onk & fortres@', '%nostalgio%', '%@onk@%', 'nostalgio onko fortreso', 'nostalgi/o', 'onk/o/gen/a', 'onk/o/logi/o']+['bufo','lofio','suturo','frajo','prismo','@buf@o','@lofi@o','@sutur@o','@fraj@o','@prism@o','krep','krepa','krepaj','krepa papero','krepa kaŭĉuko','kotona krepo','ĉina krepo','krepŝtofo','difrakt','difrakti','difrakta krado','difraktaj franĝoj','difraktometro','difraktoj','mortez','mortezi','mortezilo','mortezomaŝino','meger','megera','megeri','megereco','kanajlo','protokanajlo','boksi','impertinenta','galero','@krep@o @difrakt@o @mortez@o @meger@o','%krepo%','%@meger@%','@krep & difrakt & mortez & meger@','protez','protezado','protezi','protezisto','dentprotezo','dentprotezoj','brakprotezo','krurprotezo','ranc','ranca','ranci','ranceco','ranciĝi','ranciga','rancigitaj','protez/o','@protez@o @ranc@a','%protezo%','%@ranc@%','@protez & ranc@','hangaro','kontesti','cisticerko','kruco','risorta','risortaro','risorteco','risortiĝo','spiralrisorto','kluĉrisorto','anĉinstrumento','ancxo','anc^o','ANCXO','ANC^O','@ancx@o','@anc^@o','gaslanterno','lanternego','lanternisto','paperlanterno','stratlanterno','lubrika','lubriki','lubrikaĵo','lubrikilo','lubrikado','nelubrikita','lampoj','lucerno','gliti','sinoviito','plando','plandoj','@pland@o','@risort@o @anĉ@o @lantern@o @lubrik@i','%risorto%','%@anĉ@%','@lantern & lubrik@','observatoriejo','observatoriestro','observatoridomo','observatoripersonaro','observi','observo','observejo','astronomio','astrologio','meteorologio','majestaj','subtileco','@observatori@o @observ@i','%observatorio%','%@observatori@%','@observatori & observatori@','observatorio uveo uveito uvo vito','uveito','uvea','uveaj','uveajoj','uveektomio','uveinflamo','uveo uveito','@uve@o @uveit@o','%uveo%','%@uve@%','@uve@o & %uveo%','@uve & uveit@','psitakedoj','psitakozo','uvujo','uvbero','uvsuko','uvvino','limonujo','limonsuko','limonŝelo',
 'limonadbotelo','limonado','uveo','uveito','vito','papago','konkordo','observatorio','majesto','subtila',
 'turmenti','torturi','testikito','orkidito','@testikit@o','@orkidit@o',
 'ananaso','jakvo','prioritato','prioro','lasi','emancipi','struto','sinergio','olivo','ovalo','elipso',
 'stafilokoko','@stafilokok@o','semajntagoj','@semajn@tagoj','semajn semajn','ŝakisto',
 'uvo uveo uveito vito','@uv@o @uve@o @uveit@o @vit@o','@psitak@o @papag@o',
 '@limon@o @limonad@o','%uvo%','%@uv@%','@uv@o & %uvo%','@psitak & uv & limon & limonad@',
 '@amiko & amiko@']
WORDS=list(dict.fromkeys(TARGET_WORDS+PREVIOUS_TARGETS+EXTRA))
MANUAL=['nostalgi/o','onk/o','fortres/o','sin/o','tumor/o','fuort/o','burg/o','koincid/o','kombinaci/o','karikatur/o','sarkasm/o','spermat/o','ĉur/o','sperm/o','satir/o','buf/o','lofi/o','sutur/o','fraj/o','prism/o','krep/o','difrakt/o','mortez/o','meger/o','protez/o','ranc/a','risort/o','anĉ/o','lantern/o','lubrik/o','pland/o','lamp/o','lucern/o','glit/o','sinoviit/o','uve/o','uveit/o','psitak/o','uv/o','limon/o','limonad/o','vit/o','papag/o','konkord/o','observatori/o','majest/o','subtil/o','observ/o','astronom/o']


ANNO_RE=re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',re.S)
NEW_GLOSSES={
 'JA':{'nostalgi':'郷愁・懐かしさや憧れに伴う悲しさ','onk':'腫瘍（特に悪性）','fortres':'大規模で堅固な要塞'},
 'ZH':{'nostalgi':'思乡、怀旧或渴望引起的悲伤','onk':'肿瘤（尤指恶性）','fortres':'大型坚固要塞'},
 'KO':{'nostalgi':'향수·그리움·갈망의 슬픔','onk':'종양（특히 악성）','fortres':'크고 견고한 요새'}}
OLD_GLOSSES={
 'JA':{'nostalgi':{'郷愁'},'onk':{'腫瘍'},'fortres':{'要塞'}},
 'ZH':{'nostalgi':{'乡愁','怀旧'},'onk':{'肿瘤'},'fortres':{'堡垒'}},
 'KO':{'nostalgi':{'향수','향수(鄕愁)'},'onk':{'종양'},'fortres':{'요새'}}}
ANNO_CSV={'エスペラント語根-日本語訳ルビ対応リスト.csv':'JA','世界语词根-中文注释对应列表.csv':'ZH','에스페란토 어근-한국어 번역 루비 대응 목록.csv':'KO'}

def annotation_neutral(value):
    return ANNO_RE.sub(lambda m:'<reviewed_anno>'+h.plain(m[1])+'</reviewed_anno>' if h.plain(m[1]).lower() in VALUES else m[0],value)

def assert_gloss(language,piece,value,after=True):
    root=piece.lower()
    if root in VALUES:
        assert value in ({NEW_GLOSSES[language][root]} if after else OLD_GLOSSES[language][root]),(language,piece,value,after)

def annotation_tables(root,old_bytes):
    report=[]
    for lang in ('JA','ZH','KO'):
        data=root/f'Esperanto-Kanji-Ruby-{lang}/app_data';path=data/h.MODES['ruby'][0]
        now=json.loads(path.read_bytes());old=json.loads(old_bytes(path)) if old_bytes else None;counts={}
        if old is not None:assert list(now)==list(old)
        for group,rows in now.items():
            changed=0;targets={r:0 for r in VALUES}
            if old is not None:assert len(rows)==len(old[group])
            for i,row in enumerate(rows):
                for m in ANNO_RE.finditer(row[1]):
                    piece=h.plain(m[1]);assert_gloss(lang,piece,h.plain(m[2]))
                    if piece.lower() in targets:targets[piece.lower()]+=1
                if old is not None:
                    previous=old[group][i]
                    for m in ANNO_RE.finditer(previous[1]):assert_gloss(lang,h.plain(m[1]),h.plain(m[2]),False)
                    assert previous[:1]+previous[2:]==row[:1]+row[2:]
                    assert annotation_neutral(previous[1])==annotation_neutral(row[1]),(lang,group,row[0])
                    assert h.original(previous[1],'ruby')==h.original(row[1],'ruby')
                    changed+=previous!=row
            counts[group]={'rows':len(rows),'changed':changed if old is not None else None,'target_pieces':targets}
        csvs=[]
        for name,language in ANNO_CSV.items():
            path=data/name
            if not path.exists():continue
            raw=path.read_bytes();rows=list(csv.reader(io.StringIO(raw.decode('utf-8'))))
            matches=[r for r in rows if r and r[0] in VALUES]
            assert matches
            for r in matches:assert r==[r[0],NEW_GLOSSES[language][r[0]]]
            if old_bytes:
                lines=[];seen=[]
                for line in old_bytes(path).decode('utf-8').splitlines(keepends=True):
                    body=line.rstrip('\r\n');ending=line[len(body):];r=next(csv.reader([body]),[])
                    if r and r[0] in VALUES:
                        assert_gloss(language,r[0],r[1],False);assert body==','.join(r)
                        line=r[0]+','+NEW_GLOSSES[language][r[0]]+ending;seen.append(r[0])
                    lines.append(line)
                assert len(seen)==len(set(seen)) and ''.join(lines).encode('utf-8')==raw
            csvs.append({'file':name,'target_roots':[r[0] for r in matches]})
        path=data/'word_anno.json';words=json.loads(path.read_bytes());before=json.loads(old_bytes(path)) if old_bytes else None;wordchanges=[]
        if before is not None:assert list(words)==list(before)
        for key,pairs in words.items():
            for piece,meaning in pairs:assert_gloss(lang,piece,meaning)
            if before is not None:
                assert [p for p,v in pairs]==[p for p,v in before[key]]
                for a,b in zip(before[key],pairs):
                    assert_gloss(lang,a[0],a[1],False)
                    if b[0].lower() not in VALUES:assert a==b
                if before[key]!=pairs:wordchanges.append(key)
        report.append({'language':lang,'groups':counts,'changed_word_keys':wordchanges,'csvs':csvs})
        print('annotation tables',lang,'PASS',flush=True);del now,old;gc.collect()
    return report

def assert_runtime_glosses(report):
    checked={lang:{r:0 for r in VALUES} for lang in NEW_GLOSSES}
    for section,field in (('runtime','final'),('manual','output')):
        for row in report[section]:
            if row['mode']!='ruby':continue
            for m in ANNO_RE.finditer(row[field]):
                piece=h.plain(m[1]);assert_gloss(row['language'],piece,h.plain(m[2]))
                if piece.lower() in VALUES:checked[row['language']][piece.lower()]+=1
    assert all(n>0 for x in checked.values() for n in x.values());return checked

def assert_mirror_segmentation(report,after=True):
    head='瘤ᴼ' if after else '肿瘤'
    expected={'onkogena':head+'o生ᴳa','@onkogen@a':head+'生ᴳa','onkologio':head+'o学ᴸᴳo','@onkologi@o':head+'学ᴸᴳo'}
    checked=0
    for row in report['runtime']:
        if row['input'] in expected and row['mode'] in ('kanji','pure'):
            assert row['visible']==expected[row['input']],(row,expected);checked+=1
    assert checked==24;return checked


def neutral(value,after):
    def visit(match):
        spelling=h.plain(match[2]);root=spelling.lower()
        if root not in ALL_VALUES:return match[0]
        expected=ALL_VALUES[root][int(after)]
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
            changed=0;target_pieces={r:0 for r in ALL_VALUES}
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
        for rootname,(_,expected) in ALL_VALUES.items():
            for spelling in (rootname,rootname.title(),rootname.upper()):
                assert h.visible(local[spelling])==expected,(spelling,local[spelling])
        csvpath=data/h.CSV_NAME;raw=csvpath.read_bytes();mapping=dict(csv.reader(io.StringIO(raw.decode('utf-8'))))
        for name,(_,expected) in ALL_VALUES.items():assert mapping[name]==expected
        for name,expected in CONTROLS.items():assert mapping[name]==expected,(name,mapping.get(name),expected)
        unchanged=[]
        if old_bytes:
            previous=old_bytes(csvpath);expected=previous
            for name,(old,new) in ALL_VALUES.items():
                a=(name+','+old+'\n').encode();b=(name+','+new+'\n').encode()
                assert expected.count(a)==1,(name,expected.count(a))
                expected=expected.replace(a,b)
            assert expected==raw
            for other in data.iterdir():
                if not other.is_file() or other.name in {h.CSV_NAME,h.MODES['kanji'][0],h.MODES['pure'][0],h.MODES['ruby'][0],'word_anno.json',*ANNO_CSV}:continue
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
        engine=h.load_module(app,'esp_text_replacement_module.py','nostalgi_onk_fortres_engine_'+lang)
        overlay=h.load_module(app,'esp_overlay_module.py','nostalgi_onk_fortres_overlay_'+lang)
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
                    source=engine.convert_to_circumflex(source)
                    assert h.original(value,mode)==source,(mode,word,value)
                if mode!='ruby':
                    for rt,values in VALUES.items():
                        expected=values[int(after)]
                        # Ordinary forms retain baseline segmentation, including existing di+frakt forms.
                        # Explicit local-root input and manual overlays must follow the reviewed root.
                        for sourcebase,ending in ((rt+'o','o'),('@'+rt+'@o','o'),('@'+rt+'o@','o'),('@'+rt+'@ojn','ojn')):
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
    # Verify ordinary singulars are whole roots both before and after, independently of @.
    for snapshot,is_after in ((before,False),(after,True)):
        for root,values in VALUES.items():
            rows=[row for row in snapshot['runtime'] if row['input']==root+'o' and row['mode'] in ('kanji','pure')]
            assert len(rows)==6,(root,len(rows))
            assert all(row['visible']==values[int(is_after)]+'o' for row in rows),(root,is_after,rows)
    for section,fields in (('runtime',('first','final')),('manual',('output',))):
        assert len(before[section])==len(after[section])
        for a,b in zip(before[section],after[section]):
            assert (a['language'],a['mode'],a['input'])==(b['language'],b['mode'],b['input'])
            for phase in fields:
                if a['mode']=='ruby':assert annotation_neutral(a[phase])==annotation_neutral(b[phase]),(section,a['input'])
                elif a['mode']=='kanji':assert neutral(a[phase],False)==neutral(b[phase],True),(section,a['input'])
                # Pure is checked against visible kanji output in both captures.

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app-root',type=Path)
    b=p.add_mutually_exclusive_group();b.add_argument('--baseline-ref');b.add_argument('--baseline-zip',type=Path)
    p.add_argument('--capture-before',action='store_true');p.add_argument('--compare-capture',type=Path)
    p.add_argument('--tables-only',action='store_true');p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    root=a.app_root.resolve() if a.app_root else HERE.parent
    report={'passed':False,'baseline_ref':a.baseline_ref,'baseline_snapshot':a.baseline_zip.name if a.baseline_zip else None,
            'phase':'before' if a.capture_before else 'after','assignments':ALL_VALUES,
            'limitations':['Preserves all non-target annotation pieces and segmentation; target meanings have independent literal expectations. Other annotations are not semantically re-audited.']}
    if not a.capture_before:
        reader=baseline_reader(root,a.baseline_zip,a.baseline_ref)
        report['tables']=tables(root,reader)
        report['annotation_tables']=annotation_tables(root,reader)
    if not a.tables_only:
        report['runtime'],report['manual']=runtime(root,not a.capture_before)
        if a.compare_capture:compare(json.loads(a.compare_capture.read_text(encoding='utf-8')),report)
        report['mirror_segmentation_checks']=assert_mirror_segmentation(report,not a.capture_before)
        if not a.capture_before:report['runtime_semantics']=assert_runtime_glosses(report)
    report['passed']=True
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('nostalgi/onk/fortres assignments regression PASS',flush=True)
if __name__=='__main__':main()
