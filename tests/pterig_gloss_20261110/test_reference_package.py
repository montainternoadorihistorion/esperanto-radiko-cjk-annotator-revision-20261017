"""Keep the public reference package complete and aligned with current assignments."""
from pathlib import Path
from html.parser import HTMLParser
import ast,csv,json,types,unittest,zipfile
ROOT=Path(__file__).resolve().parents[2]
REFERENCES=ROOT/'references'
EXTRA_MANUAL_ROOTS={'esperant','german','latin','rus','Petr','Krist','angl','eŭrop','Oceani','ĉin','islam','kaf','um'}

def unicode_root(value):
    for old,new in zip('cghjsuCGHJSU','ĉĝĥĵŝŭĈĜĤĴŜŬ'):
        value=value.replace(old+'^',new)
    return value

def reference_rows():
    text=(REFERENCES/'kanji.html').read_text('utf-8-sig')
    rows,_=json.JSONDecoder().raw_decode(text.split('const D=',1)[1])
    return rows

class Links(HTMLParser):
    def __init__(self):super().__init__();self.values=[]
    def handle_starttag(self,tag,attrs):
        self.values.extend(v for k,v in attrs if k in ('href','src') and v)

class PterigReference(unittest.TestCase):
    def test_all_reference_assignments_and_identifiers_match_current_csv(self):
        rows=reference_rows()
        display={unicode_root(row['r']):row['k']+row['i'] for row in rows}
        self.assertEqual(len(display),len(rows),'Duplicate normalized reference roots')
        for lang in ('JA','ZH','KO'):
            path=ROOT/f'Esperanto-Kanji-Ruby-{lang}/app_data/世界语词根-汉字对应列表_参照2新割当_7791.csv'
            csv_rows=list(csv.reader(path.open(encoding='utf-8-sig',newline='')))
            current=dict(csv_rows)
            self.assertEqual(len(current),len(csv_rows),'Duplicate manual CSV roots')
            self.assertEqual(set(current)-set(display),EXTRA_MANUAL_ROOTS)
            self.assertEqual(display,{root:current[root] for root in display})
        byroot={unicode_root(row['r']):row for row in rows}
        self.assertEqual(byroot['pterig']['g'],'翼')
        self.assertEqual(display['pterig'],'翅ᴾᴳ')

    def test_archive_contains_exact_self_contained_html_pair(self):
        expected={'kanji.html','words.html'}
        with zipfile.ZipFile(REFERENCES/'kanji_reference_current.zip') as archive:
            self.assertEqual(set(archive.namelist()),expected)
            self.assertEqual(len(archive.infolist()),2)
            self.assertIsNone(archive.testzip())
            for name in expected:
                self.assertEqual(archive.read(name),(REFERENCES/name).read_bytes())
                links=Links();links.feed(archive.read(name).decode('utf-8-sig'))
                self.assertEqual(set(links.values),expected-{name})

    def test_source_compatibility_checks_reference_files_only_for_current(self):
        commit='a'*40
        prefix='https://raw.githubusercontent.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017/'
        for lang in ('JA','ZH','KO'):
            app=ROOT/f'Esperanto-Kanji-Ruby-{lang}'
            page=next((app/'pages').glob('2_*.py'))
            module=ast.parse(page.read_text('utf-8-sig'))
            function=next(node for node in module.body if isinstance(node,ast.FunctionDef) and node.name=='_matching_source_links')
            code=compile(ast.Module(body=[function],type_ignores=[]),str(page),'exec')
            for edition in ('current','legacy'):
                seen=[]
                def pin(_data,path):
                    seen.append(path)
                    return prefix+commit+'/'+path.relative_to(ROOT).as_posix()
                fake=types.SimpleNamespace(resolve_path=lambda data,role,choice:data/(role+'.json'),pinned_asset_url=pin)
                env={'APP_DIR':app,'DATA_DIR':app/'app_data','ROOT':ROOT,'edition':edition,'editions':fake}
                exec(code,env)
                self.assertEqual(env['_matching_source_links']()['commit'],commit)
                seen_references={p.name for p in seen if p.parent==REFERENCES}
                self.assertEqual(seen_references,{'kanji.html','words.html','kanji_reference_current.zip'} if edition=='current' else set())
                if edition=='current':
                    fake.pinned_asset_url=lambda _data,path:None if path==REFERENCES/'words.html' else prefix+commit+'/'+path.relative_to(ROOT).as_posix()
                    self.assertIsNone(env['_matching_source_links'](),'Uncommitted reference bytes must not receive a matching-source link')

if __name__=='__main__':unittest.main()
