"""Approved 2026-11-01 labels with preserved segmentation and fixed legacy."""
from pathlib import Path
import csv,gc,gzip,hashlib,io,json,re,unittest
ROOT=Path(__file__).resolve().parent.parent
CSV='世界语词根-汉字对应列表_参照2新割当_7791.csv'
CURRENT={"karot":"参ᴷ","panak":"参ᴾ","ginseng":"参ᴳ","karoten":"参ᴷ素","instig":"促ᴵ","elegi":"哀歌","delic":"悦ᴰ","delekt":"悦ᴰᴷ","pense":"草ᴾᴺ","psilofit":"草ᴾˢ","pasiflor":"草ᴾᶠ"}
LEGACY={"karot":"胡萝卜","panak":"草ᴾᴺ","ginseng":"草ᴳᴳ","karoten":"萝卜素","instig":"唆","elegi":"挽歌","delic":"珍","delekt":"悦ᴰ","pense":"草ᴾˢ","psilofit":"草ᴾᶠ","pasiflor":"草ᴾᴬˢ"}
KEEPS={"ligatur":"结ᴸᵀ","lig":"结","nod":"结ᴺ","bant":"结ᴮ","konklud":"结ᴷ","vrak":"残船","ekzempler":"册ᴱ","fuz":"燃ᶠᶻ","fuel":"燃ᶠ","brul":"燃","fuzi":"聚变","semajn":"周","stab":"参","referenc":"参ᴿ","koni":"毒参","holoturi":"海参"}
LEGACY_SHA={'JA':'215f0c297bf73efe29f4b323a982adb63a181d42e202dbed63f52c954baeb0fe','ZH':'f05e779677489ebcf5d00b00389e841eb89cc8bf7af87bbf1d1e65309c0fd594','KO':'8005ecf215185aa8fe9b8f482305f9fb1ec17aaf0d1c9c4fbbbb7928ef97508c'}
RUBY=re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>',re.S)
BREAK=re.compile(r'<br\s*/?>',re.I)
def fragments(value):return [(BREAK.sub('',m[2]),m[1]) for m in RUBY.finditer(value)]
def strip(value):return re.sub('</?ruby>','',re.sub('<rt[^>]*>.*?</rt>','',value,flags=re.S))
class AdoptedAssignments20261101(unittest.TestCase):
 def test_current_manual_tables_and_legacy_snapshot(self):
  for lang in ('JA','ZH','KO'):
   data=ROOT/f'Esperanto-Kanji-Ruby-{lang}/app_data'
   table=dict(csv.reader(io.StringIO((data/CSV).read_text('utf-8-sig'))))
   for root,value in {**CURRENT,**KEEPS}.items():self.assertEqual(table[root],value,(lang,root))
   raw=(ROOT/f'assignment_editions/legacy/{lang}/kanji.json.gz').read_bytes()
   self.assertEqual(hashlib.sha256(raw).hexdigest(),LEGACY_SHA[lang])
 def test_current_all_global_and_local_root_labels(self):
  for lang in ('JA','ZH','KO'):
   data=ROOT/f'Esperanto-Kanji-Ruby-{lang}/app_data';payload=json.loads((data/'置換リスト_漢字.json').read_bytes())
   for group,rows in payload.items():
    for row in rows:
     for root,glyph in fragments(row[1]):
      if root.lower() in CURRENT:self.assertEqual(glyph,CURRENT[root.lower()],(lang,group,row[0],root))
   local=dict((r[0],r[1]) for r in payload[next(k for k in payload if k.startswith('局部'))])
   for root,value in CURRENT.items():
    for variant in (root,root.title(),root.upper()):self.assertEqual(fragments(local[variant]),[(variant,value)])
   # karoten's independent @ root changes; the ordinary learned karot/en
   # segmentation retains en as Latin, rather than assigning the suffix 素.
   global_rows=payload[next(k for k in payload if k.startswith('全域'))]
   carotene=[r for r in global_rows if r[0].strip().lower()=='karoten']
   self.assertTrue(carotene)
   for row in carotene:
    self.assertIn(('karot','参ᴷ'),[(r.lower(),v) for r,v in fragments(row[1])])
    self.assertTrue(strip(row[1]).lower().endswith('en'))
    self.assertNotIn('素',row[1])
   if lang=='JA':
    pure=json.loads((data/'置換リスト_漢字_純粋置換.json').read_bytes())
    self.assertEqual(list(payload),list(pure))
    for group,rows in payload.items():
     self.assertEqual(len(rows),len(pure[group]))
     for row,p in zip(rows,pure[group]):self.assertEqual(p,[row[0],strip(row[1]),*row[2:]])
    del pure
   del payload,local,global_rows;gc.collect()
 def test_elegi_chinese_learning_gloss(self):
  data=ROOT/'Esperanto-Kanji-Ruby-ZH/app_data'
  self.assertEqual(json.loads((data/'word_anno.json').read_bytes())['elegi'],[['elegi','哀歌']])
  self.assertEqual(dict(r for r in csv.reader(io.StringIO((data/'世界语词根-中文注释对应列表.csv').read_text('utf-8-sig'))) if len(r)==2)['elegi'],'哀歌')
  payload=json.loads((data/'置換リスト_ルビ.json').read_bytes());seen={}
  for group,rows in payload.items():
   count=0
   for row in rows:
    for m in RUBY.finditer(row[1]):
     if BREAK.sub('',m[1]).lower()=='elegi':self.assertEqual(BREAK.sub('',m[2]),'哀歌');count+=1
   seen[group]=count
  self.assertEqual(sum(v for k,v in seen.items() if k.startswith('全域')),27)
  self.assertEqual(sum(v for k,v in seen.items() if k.startswith('局部')),3)
if __name__=='__main__':unittest.main()
