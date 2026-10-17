"""Portable whole-table and runtime regression for reviewed 13-root display changes.

Copy this file to public tests/. No private generation module is imported.
--baseline-ref enables full row/order/placeholder and annotation-byte comparison.
"""
import argparse
from collections import Counter
import csv
import hashlib
import html
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT=Path(__file__).resolve().parent.parent
BASELINE=None
REPORT={'tables':[],'runtime':[],'manual':[]}
GLOBAL='全域替换用のリスト(列表)型配列(replacements_final_list)'
LOCAL='局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'
TWO='二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)'
CSV_NAME='世界语词根-汉字对应列表_参照2新割当_7791.csv'
MODES={'ruby':('置換リスト_ルビ.json','HTML格式_Ruby文字_大小调整'),
       'kanji':('置換リスト_漢字.json','HTML格式_Ruby文字_大小调整_汉字替换'),
       'pure':('置換リスト_漢字_純粋置換.json','替换后文字列のみ(仅)保留(简单替换)')}
VALUES={'strut':('鸵鸟','鸵'),'sinergi':('协同作用','协同'),'oliv':('橄榄','榄'),
        'limak':('蜗牛','螺ᴸ'),'orkidit':('兰炎','丸炎'),'orkidektomi':('兰除','丸除'),
        'orkidoterapi':('兰疗','丸疗'),'testikit':('丸炎','丸炎ᵀ'),'paniklit':('圆锥炎','脂炎'),
        'kuriterapi':('廷疗','kuri疗'),'litografi':('石志','石ᴸᵀ志ᴳ'),
        'fotolitografi':('拍石志','拍石ᴸᵀ志ᴳ'),'kromolitografi':('色石志','色ᴷᴹ石ᴸᵀ志ᴳ')}
RUBY=re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',re.S)

def plain(value):
    return html.unescape(re.sub(r'<[^>]*>','',value)).replace('\xa0',' ')

def strip_ruby(value):
    return re.sub(r'<rt[^>]*>.*?</rt>','',value,flags=re.S).replace('<ruby>','').replace('</ruby>','')

def visible(value):return plain(strip_ruby(value))

def original(value,mode):
    return plain(RUBY.sub(lambda m:m[2] if mode=='kanji' else m[1],value))

def neutral(value,after):
    def visit(m):
        root=plain(m[2]).lower()
        if root not in VALUES:return m[0]
        allowed=(VALUES[root][1],) if after else VALUES[root]
        if m[1] not in allowed:raise AssertionError((root,m[1],allowed))
        return '<reviewed>'+plain(m[2])+'</reviewed>'
    return RUBY.sub(visit,value)

def baseline_bytes(path):
    repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True,encoding='utf-8').strip())
    return subprocess.check_output(['git','show',f'{BASELINE}:{path.relative_to(repo).as_posix()}'],cwd=repo)

def load_module(app,name,key):
    spec=importlib.util.spec_from_file_location(key,app/name);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def render(module,data,payload,words,fmt):
    value=module.orchestrate_comprehensive_esperanto_text_replacement(' ◆ '.join(words),
        module.import_placeholders(str(data/'placeholders_skip.txt')),payload[LOCAL],
        module.import_placeholders(str(data/'placeholders_localcapture.txt')),payload[GLOBAL],payload[TWO],fmt)
    parts=[part.strip() for part in value.split('◆')]
    if len(parts)!=len(words):raise AssertionError('Batch alignment changed')
    return dict(zip(words,parts))

class ReviewedLocalTests(unittest.TestCase):
    def test_entire_deployed_delta(self):
        for lang in ('JA','ZH','KO'):
            data=ROOT/f'Esperanto-Kanji-Ruby-{lang}'/'app_data'
            path=data/MODES['kanji'][0];current=json.loads(path.read_bytes())
            old=json.loads(baseline_bytes(path)) if BASELINE else None
            groups={}
            for group,rows in current.items():
                pieces=Counter();changed=0
                if old:self.assertEqual(len(rows),len(old[group]))
                for i,row in enumerate(rows):
                    value=neutral(row[1],True)
                    if old:
                        before=old[group][i]
                        self.assertEqual(before[:1]+before[2:],row[:1]+row[2:])
                        self.assertEqual(neutral(before[1],False),value)
                        self.assertEqual(original(before[1],'kanji'),original(row[1],'kanji'))
                        changed+=before!=row
                    for m in RUBY.finditer(row[1]):
                        if plain(m[2]).lower() in VALUES:pieces[plain(m[2]).lower()]+=1
                groups[group]={'rows':len(rows),'changed':changed,'target_pieces':dict(pieces)}
            locals_by={r[0]:r[1] for r in current[LOCAL]}
            for root,(_,expected) in VALUES.items():
                for word in (root,root.title(),root.upper()):self.assertEqual(visible(locals_by[word]),expected)
            if lang=='JA':
                pure=json.loads((data/MODES['pure'][0]).read_bytes())
                for group,rows in current.items():
                    self.assertEqual(pure[group],[[r[0],strip_ruby(r[1]),*r[2:]] for r in rows])
                del pure
            raw=(data/CSV_NAME).read_bytes();mapping=dict(csv.reader(io.StringIO(raw.decode('utf-8'))))
            for root,(_,expected) in VALUES.items():self.assertEqual(mapping[root],expected)
            self.assertEqual(mapping['oval'],'椭圆');self.assertEqual(mapping['elips'],'椭圆ᴱ')
            if BASELINE:
                before=baseline_bytes(data/CSV_NAME).decode('utf-8');expected=[]
                for line in before.splitlines(keepends=True):
                    root=line.split(',',1)[0]
                    if root in VALUES:
                        body=line.rstrip('\r\n');ending=line[len(body):]
                        self.assertIn(body.split(',',1)[1],VALUES[root]);line=root+','+VALUES[root][1]+ending
                    expected.append(line)
                self.assertEqual(raw,''.join(expected).encode('utf-8'))
                anno=data/MODES['ruby'][0];self.assertEqual(anno.read_bytes(),baseline_bytes(anno))
            REPORT['tables'].append({'language':lang,'groups':groups,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            del current,old

    def test_nine_app_paths_and_manual_corrections(self):
        base=[form for root in VALUES for form in (root+'o',root+'oj',root+'on',root+'ojn',root+'a',root+'e','@'+root+'@o','@'+root+'o@')]
        base+=['strutino','strutido','strutejo','olivujo','olivoleo','sinergia','sinergie',
               'milio','@mili@o','@piroz@o','pirozo','@riboz@o','ribozo','@met@o','meto','@di@o','dio','@iĝ@i','iĝi',
               'lasi','emancipi','ananaso','jakvo','prioritato','prioro','semajntagoj','@semajn@tagoj','ŝakisto',
               'ovale','elipse','%olivo%','@strut@o & %olivo%','@amiko & amiko@']
        words=list(dict.fromkeys(form for word in base for form in (word,word.title(),word.upper())))
        controls={'milio':'粟ᴹo','@mili@o':'毫o','@piroz@o':'梨富ᴼo','pirozo':'火ᴾ症ᴼo',
                  '@riboz@o':'醋栗富ᴼo','ribozo':'核ᴿ糖ᴼo','@met@o':'甲o','meto':'置o','@di@o':'二ᴰᴵo','dio':'神o',
                  '@iĝ@i':'成i','iĝi':'成i','lasi':'放i','emancipi':'放ᴱi','ananaso':'菠o','jakvo':'菠蜜o',
                  'prioritato':'优先o','prioro':'院长ᴾo','semajntagoj':'周日oj','@semajn@tagoj':'周日oj',
                  'ŝakisto':'棋家o','ovale':'椭圆e','elipse':'椭圆ᴱe','@amiko & amiko@':'友o & 友o',
                  'orkidito':'丸ᴼ炎ᵀo','orkidektomio':'丸ᴼ除ᴱᴷo','orkidoterapio':'丸ᴼo疗o',
                  'testikito':'丸ᵀ炎ᵀo','paniklito':'脂ᴾ炎ᵀo','kuriterapio':'kuri疗o',
                  'litografio':'石ᴸᵀo志ᴳo','fotolitografio':'拍o石ᴸᵀo志ᴳo','kromolitografio':'色ᴷᴹo石ᴸᵀo志ᴳo'}
        for lang in ('JA','ZH','KO'):
            app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
            runtime=load_module(app,'esp_text_replacement_module.py','sync_runtime_'+lang)
            overlay=load_module(app,'esp_overlay_module.py','sync_overlay_'+lang)
            corrections=[overlay.build_correction(root+'/o',str(data)) for root in VALUES]
            kanji=None
            for mode,(filename,fmt) in MODES.items():
                owner=ROOT/'Esperanto-Kanji-Ruby-JA/app_data' if mode=='pure' else data
                payload=json.loads((owner/filename).read_bytes());key='ruby' if mode=='ruby' else 'kanji'
                user=overlay.load_overlay_entries(str(data),key)
                if mode=='pure':user=[[a,strip_ruby(b),c] for a,b,c in user]
                payload[GLOBAL]=overlay.merge_overlay(payload[GLOBAL],user)
                first=render(runtime,data,payload,words,fmt)
                auto=overlay.auto_overlay_entries(' ◆ '.join(first.values()),str(data),key)
                if mode=='pure':auto=[[a,strip_ruby(b),c] for a,b,c in auto]
                if auto:
                    payload[GLOBAL]=overlay.merge_overlay(payload[GLOBAL],auto)
                    final=render(runtime,data,payload,words,fmt)
                else:final=first
                for word,output in final.items():
                    if mode!='pure':self.assertEqual(original(output,mode),word.replace('@','').replace('%',''))
                    if word.startswith('%'):self.assertEqual(visible(output),word.replace('%',''))
                    elif mode in ('kanji','pure'):
                        for root in ('strut','sinergi','oliv'):
                            unprotected=re.sub(r'%[^%]*%','',word)
                            if root in unprotected.lower():self.assertIn(VALUES[root][1],visible(output))
                        for root,(_,expected) in VALUES.items():
                            if word=='@'+root+'@o':self.assertEqual(visible(output),expected+'o')
                        if word in controls:self.assertEqual(visible(output),controls[word],word)
                    if mode=='pure':self.assertEqual(output,visible(kanji[word]))
                    REPORT['runtime'].append({'language':lang,'mode':mode,'input':word,'first':first[word],'final':output})
                if mode=='kanji':kanji=final
                pairs=[p for c in corrections for p in c[key]]
                expected={w:strip_ruby(v) if mode=='pure' else v for w,v in pairs}
                entries=[[w,v,f'${9200000+i}$'] for i,(w,v) in enumerate(expected.items())]
                payload[GLOBAL]=overlay.merge_overlay(payload[GLOBAL],entries)
                manual=render(runtime,data,payload,list(expected),fmt)
                self.assertEqual(manual,expected)
                for w,v in manual.items():
                    if mode!='ruby':
                        display=VALUES[w[:-1].lower()][1]
                        if w.isupper():display=display.upper()
                        elif w[0].isupper():display=display[:1].upper()+display[1:]
                        self.assertEqual(visible(v),display+w[-1])
                    REPORT['manual'].append({'language':lang,'mode':mode,'input':w,'output':v})
                del payload

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--app-root',type=Path)
    parser.add_argument('--baseline-ref');parser.add_argument('--report',type=Path);args=parser.parse_args()
    ROOT=args.app_root.resolve() if args.app_root else ROOT;BASELINE=args.baseline_ref
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReviewedLocalTests))
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps({'passed':result.wasSuccessful(),**REPORT},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
