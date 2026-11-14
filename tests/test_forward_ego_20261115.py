"""Ego and egoist share 我 with consistent internal identifier; preserve legacy and other roots."""
from pathlib import Path
import csv,gc,hashlib,io,json,re,unittest
ROOT=Path(__file__).resolve().parents[1]
CSV='世界语词根-汉字对应列表_参照2新割当_7791.csv'
CURRENT={'ego': '我ᴱ', 'egoist': '我ᴱ家'}
KEEPS={'klorofil': '叶绿', 'mi': '我', 'atm': '我ᴬ', 'ni': '我们', 'si': '己', 'propr': '己ᴾ', 'propriet': '己ᴾᵀ'}
PRESERVED_HASHES={'assignment_editions/legacy/manifest.json': '64aea654ea7f0ff2e0c1e2808754637a583cb7b2e1b201d11fc42fc926dfc86b', 'assignment_editions/legacy/README.md': '071c61a94faa66558d1424f976fc69537afd3f2cbb739576263e8fc92e3d1bc0', 'assignment_editions/legacy/test_legacy_assets.py': '038d12c39da393af8f72a25d0fec8ad98e46f9d298e2b269fe0e39360e31bb60', 'assignment_editions/legacy/_identifier_sidecar.tsv': '8ee9e27651413f87f1404eb5c328e7ad8ba4bda3be61a442ac9585911a4a9600', 'assignment_editions/legacy/_kanji_map_master.tsv': '8260593759caf4403e61e88ba54b15eb4486dd499467aff8db95cf8058ec50f8', 'assignment_editions/legacy/JA/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/JA/kanji.json.gz': '6eb499e70b3b9d4de661665043f2bc0b5dfd7c61969ff5de907592500f3414be', 'assignment_editions/legacy/JA/pure.json.gz': '92b807083dde178214c3a0deb277ca75515dae62a8b9ce4fbb08b1d541b3ba1c', 'assignment_editions/legacy/KO/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/KO/kanji.json.gz': '04f7120578bef8d14862306a768527e0807e277e094bf4fbf7e8d32b6d697b22', 'assignment_editions/legacy/ZH/kanji.csv': '40b265f39934fcf40b660bfa6bc5fac85a3a070f5b2545918702a8000b1971f1', 'assignment_editions/legacy/ZH/kanji.json.gz': '9f5fc98b84d696bab738c80bba4a25499e5b140be01a9cb91b11bf6422868ed1'}
RUBY=re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',re.S)
BREAK=re.compile(r'<br\s*/?>',re.I)
def normalize(root):
 for a,b in zip(('c^','g^','h^','j^','s^','u^'),'ĉĝĥĵŝŭ'):root=root.replace(a,b)
 return root

def fragments(value):return [(BREAK.sub('',m[2]),m[1]) for m in RUBY.finditer(value)]
def strip(value):return re.sub('</?ruby>','',re.sub('<rt[^>]*>.*?</rt>','',value,flags=re.S))
class EgoAssignment20261115(unittest.TestCase):
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
    for variant in (root,root.title(),root.upper()):
     if root=='ego':
      self.assertEqual(fragments(local[variant]),[(variant[:-1],'巨')])
      self.assertTrue(local[variant].endswith('O' if variant.isupper() else 'o'))
     else:self.assertEqual(fragments(local[variant]),[(variant,value)])
   if lang=='JA':
    pure=json.loads((data/'置換リスト_漢字_純粋置換.json').read_bytes())
    self.assertEqual(list(payload),list(pure))
    for group,rows in payload.items():
     self.assertEqual(len(rows),len(pure[group]))
     for row,p in zip(rows,pure[group]):self.assertEqual(p,[row[0],strip(row[1]),*row[2:]])
    del pure
   del payload,local;gc.collect()
 def test_exact_ego_boundary_keeps_eg_and_literal_text(self):
  import importlib.util,logging,sys
  logging.disable(logging.WARNING)
  app=ROOT/'Esperanto-Kanji-Ruby-JA';data=app/'app_data';sys.path.insert(0,str(app))
  def load(name):
   spec=importlib.util.spec_from_file_location('ego_guard_'+name,app/(name+'.py'));module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module
  rt=load('esp_text_replacement_module');ed=load('esp_assignment_edition');ov=load('esp_overlay_module')
  skip=rt.import_placeholders(str(data/'placeholders_skip.txt'));local=rt.import_placeholders(str(data/'placeholders_localcapture.txt'))
  source='ego @ego@ @eg@o @ego@@ist@o @egoist@o %ego% @grandego@ @bonego@ @belego@ @librego@'
  for edition,root,whole in [('current','我ᴱ','我ᴱ家'),('legacy','吾','己ᴱ')]:
   gg,ll,tw=ed.load_lists(data,'pure',edition)
   value=rt.orchestrate_comprehensive_esperanto_text_replacement(source,skip,ll,local,gg,tw,'替换后文字列のみ(仅)保留(简单替换)',reviewed_local_decompositions=True)
   self.assertEqual(value,f'巨o {root} 巨o {root}家o {whole}o ego 大巨o 良巨o 美巨o 书巨o')
   custom=rt.orchestrate_comprehensive_esperanto_text_replacement('@ego@ %a@ego@b%',skip,ll,local,gg,tw,'替换后文字列のみ(仅)保留(简单替换)',reviewed_local_decompositions=False)
   self.assertEqual(custom,'巨o a@ego@b')
   override=ov.merge_overlay(gg,[['ego','CUSTOM','$9000123$']])
   self.assertTrue(any(r[0]==' ego ' and r[1]==' CUSTOM ' for r in override))
   manual=rt.orchestrate_comprehensive_esperanto_text_replacement('@ego@ @grandego@',skip,ll,local,override,tw,'替换后文字列のみ(仅)保留(简单替换)',reviewed_local_decompositions=True)
   self.assertEqual(manual,'CUSTOM 大巨o')
   for corrected in ('CUSTOM','CUSTOMo'):
    other=ov.merge_overlay(gg,[['egoo',corrected,'$9000124$']])
    self.assertEqual(rt._reviewed_exact_ego_renderings(['ego'],ll,other,True),{'ego':root})
    value=rt.orchestrate_comprehensive_esperanto_text_replacement('@ego@ egoo',skip,ll,local,other,tw,'替换后文字列のみ(仅)保留(简单替换)',reviewed_local_decompositions=True)
    self.assertEqual(value,root+' '+corrected)
   all_anchors=ov.merge_overlay(gg,[[word,'CUSTOM'+str(i),'$'+str(9000130+i)+'$'] for i,word in enumerate(('egoo','egoon','egooj','egoojn'))])
   self.assertEqual(rt._reviewed_exact_ego_renderings(['ego'],ll,all_anchors,True),{})
   value=rt.orchestrate_comprehensive_esperanto_text_replacement('@ego@ @grandego@',skip,ll,local,all_anchors,tw,'替换后文字列のみ(仅)保留(简单替换)',reviewed_local_decompositions=True)
   self.assertEqual(value,'巨o 大巨o')
   combined=ov.merge_overlay(all_anchors,[['ego','ROOT','$9000139$']])
   self.assertEqual(rt._reviewed_exact_ego_renderings(['ego'],ll,combined,True),{'ego':'ROOT'})
   ed._load_lists_cached.clear();del gg,ll,tw;gc.collect()
  sys.path.pop(0)
if __name__=='__main__':unittest.main()
