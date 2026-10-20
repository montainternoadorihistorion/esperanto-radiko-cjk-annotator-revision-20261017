"""Portable checks for the six 2026-10-20 user-adopted assignments."""
from pathlib import Path
import csv,gc,gzip,hashlib,html,io,json,re,unittest
ROOT=Path(__file__).resolve().parent.parent
VALUES={'bedaŭr':'惜ᴮ','raŭk':'哑ᴿ','buf':'蟆','lofi':'蟆鱼','aŭtomat':'自动','aŭtomaci':'自动ᴬᶜ'}
OLD={'bedaŭr':'憾','raŭk':'沙哑','buf':'蛤蟆','lofi':'蛤蟆鱼','aŭtomat':'动ᴬ','aŭtomaci':'动ᴬᶜ'}
CONTROLS={'domaĝ':'惜','mut':'哑','gelaten':'明胶','ŝakal':'胡狼','mikrob':'微生物','diafragm':'隔膜',
          'mov':'动','motor':'动ᴹᵀ','kanajl':'恶棍','prism':'棱镜','greft':'移植','dot':'妆'}
CSV='世界语词根-汉字对应列表_参照2新割当_7791.csv'
def visible(text):
 text=re.sub('<rt[^>]*>.*?</rt>','',text,flags=re.S)
 return html.unescape(re.sub('<[^>]*>','',text))
class SixAssignments(unittest.TestCase):
 def test_current_csv_and_preserved_other_choices(self):
  for lang in ('JA','ZH','KO'):
   mapping=dict(csv.reader(io.StringIO((ROOT/f'Esperanto-Kanji-Ruby-{lang}/app_data'/CSV).read_text('utf-8'))))
   for root,value in {**VALUES,**CONTROLS}.items():self.assertEqual(mapping[root],value,(lang,root))
 def test_all_case_local_displays_both_editions(self):
  for lang in ('JA','ZH','KO'):
   for edition in ('current','legacy'):
    if edition=='current':raw=(ROOT/f'Esperanto-Kanji-Ruby-{lang}/app_data/置換リスト_漢字.json').read_bytes()
    else:raw=gzip.decompress((ROOT/f'assignment_editions/legacy/{lang}/kanji.json.gz').read_bytes())
    payload=json.loads(raw);key=next(k for k in payload if k.startswith('局部'));local={r[0]:r[1] for r in payload[key]}
    for root,value in (VALUES if edition=='current' else OLD).items():
     for spelling in (root,root.title(),root.upper()):self.assertEqual(visible(local[spelling]),value,(lang,edition,spelling))
    del raw,payload,local;gc.collect()
 def test_reviewed_pure_is_derived_from_current_kanji(self):
  data=ROOT/'Esperanto-Kanji-Ruby-JA/app_data'
  kanji=json.loads((data/'置換リスト_漢字.json').read_bytes());pure=json.loads((data/'置換リスト_漢字_純粋置換.json').read_bytes())
  self.assertEqual(list(kanji),list(pure))
  for group,rows in kanji.items():
   self.assertEqual(len(rows),len(pure[group]))
   for a,b in zip(rows,pure[group]):
    stripped=re.sub('<rt[^>]*>.*?</rt>','',a[1]).replace('<ruby>','').replace('</ruby>','')
    self.assertEqual([a[0],stripped,*a[2:]],b)
if __name__=='__main__':unittest.main()
