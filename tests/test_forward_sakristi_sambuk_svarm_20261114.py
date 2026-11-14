"""Three adopted room, plant, and swarm assignments; unchanged other owners and legacy."""
from pathlib import Path
import csv,gc,hashlib,io,json,re,unittest
ROOT=Path(__file__).resolve().parents[1]
CSV='世界语词根-汉字对应列表_参照2新割当_7791.csv'
CURRENT={'sakristi': '圣器室', 'sambuk': '接骨木', 'svarm': '群ˢ'}
KEEPS={'triumf': '凯', 'ar': '群', 'greg': '群ᴳ', 'gajn': '获ᴳ', 'sor': '升ˢ'}
PRESERVED_HASHES={'assignment_editions/legacy/manifest.json': 'b0534aa1ad3de51164d8ebd79201899f7e3c926c1aac45ea876afa06e32b464a', 'assignment_editions/legacy/README.md': '75af06988e6b1e38a10d17a79eaf87bb3d9b49444c84c47028e46e55c25436a6', 'assignment_editions/legacy/test_legacy_assets.py': 'd65b9b91bbdf7481e90c51b3a356ecd25a0cf37b8f29e25004671f5b8994ae45', 'assignment_editions/legacy/_identifier_sidecar.tsv': '8ee9e27651413f87f1404eb5c328e7ad8ba4bda3be61a442ac9585911a4a9600', 'assignment_editions/legacy/_kanji_map_master.tsv': '8260593759caf4403e61e88ba54b15eb4486dd499467aff8db95cf8058ec50f8', 'assignment_editions/legacy/JA/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/JA/kanji.json.gz': '33c2f24076d2da1eec014646d1f800b254a63d760b506ccb3a679c1928a92778', 'assignment_editions/legacy/JA/pure.json.gz': '48e12063315fbe4f5e02d320680ee0b7c20f714da3c407f665e12cb45fbfd021', 'assignment_editions/legacy/KO/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/KO/kanji.json.gz': 'df2ac677d8451565976240532b393c93faaf6324a77a1186459730cd645edda3', 'assignment_editions/legacy/ZH/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/ZH/kanji.json.gz': 'e4ceff3fbef215ff1533b42476c3c67eba7e37d1efbcb664f61ac32e946b00fa'}
RUBY=re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',re.S)
BREAK=re.compile(r'<br\s*/?>',re.I)
def normalize(root):
 for a,b in zip(('c^','g^','h^','j^','s^','u^'),'ĉĝĥĵŝŭ'):root=root.replace(a,b)
 return root

def fragments(value):return [(BREAK.sub('',m[2]),m[1]) for m in RUBY.finditer(value)]
def strip(value):return re.sub('</?ruby>','',re.sub('<rt[^>]*>.*?</rt>','',value,flags=re.S))
class SakristiSambukSvarmAssignment20261114(unittest.TestCase):
 def test_current_manual_tables_and_preserved_assets(self):
  for lang in ('JA','ZH','KO'):
   data=ROOT/f'Esperanto-Kanji-Ruby-{lang}/app_data'
   table=dict(csv.reader(io.StringIO((data/CSV).read_text('utf-8-sig'))))
   for root,value in {**CURRENT,**KEEPS}.items():self.assertEqual(table[root],value,(lang,root))
  for rel,expected in PRESERVED_HASHES.items():
   self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),expected,rel)
 def test_all_global_and_local_root_labels(self):
  for lang in ('JA','ZH','KO'):
   data=ROOT/f'Esperanto-Kanji-Ruby-{lang}/app_data'
   payload=json.loads((data/'置換リスト_漢字.json').read_bytes())
   seen={root:0 for root in CURRENT}
   plant_pieces=0
   for group,rows in payload.items():
    for row in rows:
     for root,glyph in fragments(row[1]):
      if normalize(root.lower())=='sor' and glyph=='胞ˢ':
       plant_pieces+=1
       continue
      if normalize(root.lower()) in CURRENT:
       self.assertEqual(glyph,CURRENT[normalize(root.lower())],(lang,group,row[0],root))
       seen[normalize(root.lower())]+=1
   self.assertTrue(all(seen.values()))
   self.assertGreater(plant_pieces,0)
   local={r[0]:r[1] for r in payload[next(k for k in payload if k.startswith('局部'))]}
   for root,value in CURRENT.items():
    for variant in (root,root.title(),root.upper()):self.assertEqual(fragments(local[variant]),[(variant,value)])
   if lang=='JA':
    pure=json.loads((data/'置換リスト_漢字_純粋置換.json').read_bytes())
    self.assertEqual(list(payload),list(pure))
    for group,rows in payload.items():
     self.assertEqual(len(rows),len(pure[group]))
     for row,p in zip(rows,pure[group]):self.assertEqual(p,[row[0],strip(row[1]),*row[2:]])
    del pure
   del payload,local;gc.collect()
if __name__=='__main__':unittest.main()
