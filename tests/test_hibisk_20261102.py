"""One approved display, unchanged other owners and frozen legacy assets."""
from pathlib import Path
import csv,gc,hashlib,io,json,re,unittest
ROOT=Path(__file__).resolve().parents[1]
CSV='世界语词根-汉字对应列表_参照2新割当_7791.csv'
CURRENT={'hibisk':'芙'}
KEEPS={'eŭfori':'快ᴱ','sofism':'伪辩','agrabl':'快','alegr':'快ᴬᴸ','fals':'伪','pseŭdo':'伪ᴾ'}
PRESERVED_HASHES={'assignment_editions/legacy/manifest.json': '4e210ed686da8040f017416d0cad10a5df3f9686c57cc3b58c040ddcd191cdda', 'assignment_editions/legacy/README.md': '071c61a94faa66558d1424f976fc69537afd3f2cbb739576263e8fc92e3d1bc0', 'assignment_editions/legacy/test_legacy_assets.py': 'fe7f87b2f0e641dc1d147fa01c30291088c4553386c7ee369eb1eabff8b50206', 'assignment_editions/legacy/_identifier_sidecar.tsv': '8ee9e27651413f87f1404eb5c328e7ad8ba4bda3be61a442ac9585911a4a9600', 'assignment_editions/legacy/_kanji_map_master.tsv': '8260593759caf4403e61e88ba54b15eb4486dd499467aff8db95cf8058ec50f8', 'assignment_editions/legacy/JA/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/JA/kanji.json.gz': '215f0c297bf73efe29f4b323a982adb63a181d42e202dbed63f52c954baeb0fe', 'assignment_editions/legacy/JA/pure.json.gz': '3ef2efd50fbb13a834f7421c3e85bd406d2926dd304028b19e1de3264ec3fb40', 'assignment_editions/legacy/KO/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/KO/kanji.json.gz': '8005ecf215185aa8fe9b8f482305f9fb1ec17aaf0d1c9c4fbbbb7928ef97508c', 'assignment_editions/legacy/ZH/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/ZH/kanji.json.gz': 'f05e779677489ebcf5d00b00389e841eb89cc8bf7af87bbf1d1e65309c0fd594'}
RUBY=re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',re.S)
BREAK=re.compile(r'<br\s*/?>',re.I)
def fragments(value):return [(BREAK.sub('',m[2]),m[1]) for m in RUBY.finditer(value)]
def strip(value):return re.sub('</?ruby>','',re.sub('<rt[^>]*>.*?</rt>','',value,flags=re.S))
class Hibisk20261102(unittest.TestCase):
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
   for group,rows in payload.items():
    for row in rows:
     for root,glyph in fragments(row[1]):
      if root.lower() in CURRENT:
       self.assertEqual(glyph,CURRENT[root.lower()],(lang,group,row[0],root))
       seen[root.lower()]+=1
   self.assertTrue(all(seen.values()))
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
