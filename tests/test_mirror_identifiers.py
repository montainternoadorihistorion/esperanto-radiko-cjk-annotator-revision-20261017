"""Portable independent checks for component identifiers in whole-root displays."""
import argparse,csv,hashlib,importlib.util,io,json,re,unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;BASELINE=None
SCOPE_PATH=HERE/'reviewed_mirror_identifiers_20261017.json'
SCOPE_SHA256='d0b5dfc0c31fb35bbd27308b6841651c76987e0e6da222dd118771d92878f681'
scope_raw=SCOPE_PATH.read_bytes()
if hashlib.sha256(scope_raw).hexdigest()!=SCOPE_SHA256:raise ValueError('Test scope fingerprint changed')
SCOPE=json.loads(scope_raw)
spec=importlib.util.spec_from_file_location('mirror_test_helpers',HERE/'test_reviewed_at_sync.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
REPORT={'tables':[],'manual':[],'controls':[]}
def norm(root):
    root=root.lower()
    for a,b in zip(('c^','g^','h^','j^','s^','u^'),'ĉĝĥĵŝŭ'):root=root.replace(a,b)
    return root
VALUES={norm(r['root']):r for r in SCOPE['changes']}
# Current-value checks follow the later approved uve shortening. Keep the
# historical scope and its fingerprint unchanged, including the before value.
VALUES['uveit']={**VALUES['uveit'],'after':'葡膜炎ᵀ'}
ABSENT=set(SCOPE.get('currently_absent_csv_roots',[]))
PRESERVED={(norm(r['root']),r['display']) for r in SCOPE.get('preserved_senses',[])}

def neutral(value,phase,context):
    def visit(m):
        root=norm(h.plain(m[2]));display=m[1]
        if root not in VALUES:return m[0]
        if display==VALUES[root][phase]:return '<mirror>'+h.plain(m[2])+'</mirror>'
        for rule in SCOPE.get('word_scoped_changes',[]):
            if norm(rule['root'])==root and display==rule[phase] and any(re.fullmatch(p,norm(context.replace('/','').strip())) for p in rule['context_patterns']):
                return '<mirror>'+h.plain(m[2])+'</mirror>'
        if (root,display) in PRESERVED:return m[0]
        raise AssertionError((root,display,phase,context))
    return h.RUBY.sub(visit,value)

class MirrorTests(unittest.TestCase):
    def test_all_rows_and_csv(self):
        for lang in ('JA','ZH','KO'):
            data=ROOT/f'Esperanto-Kanji-Ruby-{lang}'/'app_data';path=data/h.MODES['kanji'][0]
            current=json.loads(path.read_bytes());old=json.loads(h.baseline_bytes(path)) if BASELINE else None
            groups={}
            for group,rows in current.items():
                changed=0
                if old:self.assertEqual(len(rows),len(old[group]))
                for i,row in enumerate(rows):
                    n=neutral(row[1],'after',row[0])
                    if old:
                        before=old[group][i]
                        self.assertEqual(before[:1]+before[2:],row[:1]+row[2:])
                        self.assertEqual(neutral(before[1],'before',before[0]),n)
                        self.assertEqual(h.original(before[1],'kanji'),h.original(row[1],'kanji'))
                        changed+=before!=row
                groups[group]={'rows':len(rows),'changed':changed}
            raw=(data/h.CSV_NAME).read_bytes();mapping=dict(csv.reader(io.StringIO(raw.decode('utf-8'))))
            for root,row in VALUES.items():
                if root in ABSENT:self.assertNotIn(root,mapping)
                else:self.assertEqual(mapping[root],row['after'])
            if BASELINE:
                oldraw=h.baseline_bytes(data/h.CSV_NAME).decode('utf-8');newlines=[]
                for line in oldraw.splitlines(keepends=True):
                    body=line.rstrip('\r\n');ending=line[len(body):];parts=next(csv.reader([body]),[])
                    if parts and norm(parts[0]) in VALUES:
                        expected=VALUES[norm(parts[0])];self.assertEqual(parts[1],expected['before'])
                        line=parts[0]+','+expected['after']+ending
                    newlines.append(line)
                self.assertEqual(raw,''.join(newlines).encode('utf-8'))
                anno=data/h.MODES['ruby'][0];self.assertEqual(anno.read_bytes(),h.baseline_bytes(anno))
            for rel,expected in SCOPE['unchanged_app_data_sha256'].items():
                if rel.startswith(f'Esperanto-Kanji-Ruby-{lang}/'):
                    self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),expected,rel)
            if lang=='JA':
                pure=json.loads((data/h.MODES['pure'][0]).read_bytes())
                for group,rows in current.items():self.assertEqual(pure[group],[[r[0],h.strip_ruby(r[1]),*r[2:]] for r in rows])
                del pure
            REPORT['tables'].append({'language':lang,'groups':groups,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            del current,old

    def test_all_manual_generation_and_nine_paths(self):
        roots=sorted(VALUES.keys()-ABSENT)
        controls=['testikito','@testikit@o','orkidito','@orkidit@o','@testikito@','@TESTIKIT@O',
                  'testikitoj','testikiton','testikitojn','Testikito','TESTIKITO','orkidektomio','orkidoterapio',
                  'paniklito','alkoholato','@alkoholat@o','salpingito','@salpingit@o','otosalpingito','@otosalpingit@o',
                  'fotografio','@fotografi@o','milio','@mili@o','@piroz@o','pirozo','@riboz@o','ribozo',
                  'lasi','emancipi','ananaso','jakvo','prioritato','struto','sinergio','olivo','ovalo','elipso',
                  'semajntagoj','@semajn@tagoj','ŝakisto','%testikito%','@testikit@o & %amiko%']
        expected={'testikito':'丸ᵀ炎ᵀo','@testikit@o':'丸ᵀ炎ᵀo','orkidito':'丸ᴼ炎ᵀo','@orkidit@o':'丸ᴼ炎ᵀo',
                  '@testikito@':'丸ᵀ炎ᵀo','@TESTIKIT@O':'丸ᵀ炎ᵀO','testikitoj':'丸ᵀ炎ᵀoj','testikiton':'丸ᵀ炎ᵀon',
                  'testikitojn':'丸ᵀ炎ᵀojn','Testikito':'丸ᵀ炎ᵀo','TESTIKITO':'丸ᵀ炎ᵀO',
                  'orkidektomio':'丸ᴼ除ᴱᴷo','orkidoterapio':'丸ᴼo疗o','paniklito':'脂ᴾ炎ᵀo',
                  'alkoholato':'醇盐ᴬo','@alkoholat@o':'醇盐ᴬo','salpingito':'卵管炎ᵀo','@salpingit@o':'卵管炎ᵀo',
                  'otosalpingito':'耳ᴼᵀo管ˢ炎ᵀo','@otosalpingit@o':'待o卵管炎ᵀo',
                  'milio':'粟ᴹo','@mili@o':'毫o','@piroz@o':'梨富ᴼo','pirozo':'火ᴾ症ᴼo','@riboz@o':'醋栗富ᴼo','ribozo':'核ᴿ糖ᴼo',
                  'lasi':'放i','emancipi':'放ᴱi','ananaso':'菠o','jakvo':'菠蜜o','prioritato':'优先o','struto':'鸵o',
                  'sinergio':'协同o','olivo':'榄o','ovalo':'椭圆o','elipso':'椭圆ᴱo','semajntagoj':'周日oj',
                  '@semajn@tagoj':'周日oj','ŝakisto':'棋家o','%testikito%':'testikito','@testikit@o & %amiko%':'丸ᵀ炎ᵀo & amiko'}
        for lang in ('JA','ZH','KO'):
            app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';data=app/'app_data'
            runtime=h.load_module(app,'esp_text_replacement_module.py','mirror_runtime_'+lang)
            overlay=h.load_module(app,'esp_overlay_module.py','mirror_overlay_'+lang)
            corrections=[overlay.build_correction(root+'/o',str(data)) for root in roots]
            for mode,(filename,fmt) in h.MODES.items():
                owner=ROOT/'Esperanto-Kanji-Ruby-JA/app_data' if mode=='pure' else data
                payload=json.loads((owner/filename).read_bytes());key='ruby' if mode=='ruby' else 'kanji'
                user=overlay.load_overlay_entries(str(data),key)
                if mode=='pure':user=[[a,h.strip_ruby(b),c] for a,b,c in user]
                payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],user)
                first=h.render(runtime,data,payload,controls,fmt)
                auto=overlay.auto_overlay_entries(' ◆ '.join(first.values()),str(data),key)
                if mode=='pure':auto=[[a,h.strip_ruby(b),c] for a,b,c in auto]
                if auto:
                    payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],auto);final=h.render(runtime,data,payload,controls,fmt)
                else:final=first
                for word,value in final.items():
                    if mode!='ruby' and word in expected:self.assertEqual(h.visible(value),expected[word],word)
                    if mode!='pure':self.assertEqual(h.original(value,mode),word.replace('@','').replace('%',''))
                    REPORT['controls'].append({'language':lang,'mode':mode,'input':word,'first':first[word],'final':value})
                pairs=[p for correction in corrections for p in correction[key]]
                desired={w:h.strip_ruby(v) if mode=='pure' else v for w,v in pairs}
                # Every generated correction is checked, including all case variants.
                for word,value in desired.items():
                    if mode!='ruby':self.assertEqual(h.visible(value),VALUES[norm(word[:-1])]['after']+word[-1])
                    if mode!='pure':self.assertEqual(h.original(value,mode),word)
                # Thousands of simultaneous session corrections exercise the
                # existing quadratic merge cost, unrelated to this data change.
                # Real full-runtime integration covers the competing whole roots,
                # alternate sense, missing-i variants and preserved split examples.
                representatives=set(roots[:3]+roots[-3:])|{'testikit','orkidit','alkoholat','salpingit',
                    'metapsiki','pedofili','polifoni','polipodi','kseroftalmi','fotografi','endoskop','mikroskop','dodekaedr','telefoni'}
                probes={w:v for w,v in desired.items() if norm(w[:-1]) in representatives}
                payload[h.GLOBAL]=overlay.merge_overlay(payload[h.GLOBAL],[[w,v,f'${93000000+i}$'] for i,(w,v) in enumerate(probes.items())])
                actual=h.render(runtime,data,payload,list(probes),fmt)
                self.assertEqual(actual,probes)
                REPORT['manual'].append({'language':lang,'mode':mode,'generated_roots':len(roots),'generated_forms':len(desired),'runtime_forms':len(actual),'passed':True})
                print('manual',lang,mode,len(desired),'generated,',len(actual),'runtime',flush=True)
                del payload

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--app-root',type=Path);parser.add_argument('--baseline-ref')
    parser.add_argument('--report',type=Path);selection=parser.add_mutually_exclusive_group()
    selection.add_argument('--runtime-only',action='store_true');selection.add_argument('--tables-only',action='store_true');args=parser.parse_args()
    ROOT=args.app_root.resolve() if args.app_root else ROOT;BASELINE=args.baseline_ref;h.ROOT=ROOT;h.BASELINE=BASELINE
    suite=(unittest.TestSuite([MirrorTests('test_all_manual_generation_and_nine_paths')]) if args.runtime_only else
           unittest.TestSuite([MirrorTests('test_all_rows_and_csv')]) if args.tables_only else unittest.defaultTestLoader.loadTestsFromTestCase(MirrorTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if args.report:args.report.write_text(json.dumps({'passed':result.wasSuccessful(),'scope_sha256':SCOPE_SHA256,**REPORT},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
