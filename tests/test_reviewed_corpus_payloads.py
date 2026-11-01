"""Exact reviewed @ payload repairs preserve ordinary rules and custom JSON."""
from pathlib import Path
import gc, hashlib, html, importlib.util, json, logging, os, re, sys, unittest
logging.disable(logging.CRITICAL)
ROOT=Path(__file__).resolve().parents[1]
BEFORE_ROOT=Path(os.environ['LEARNING_BEFORE_ROOT']) if os.environ.get('LEARNING_BEFORE_ROOT') else None
REPORT=[]
# Keep this independent acceptance list explicit; do not derive it from the code.
TARGETS=frozenset(['teamanojn','tradukteamanojn','aperdato','aristokratino','koleginoj','konilon','vortuzon','ekstermovadaj','Landaron','landaron','dekstremuloj','regularojn','skanaĵoj','malfidinda','Emociego','antaŭeko','videbleco','uzeblas','direktivoj','organiziĝi','sendependa','radio-programeroj','romanigoj','filozofion','aŭskultoviziton','civilizon','korelingvajn','kronologion','IJK-on','burokratio','dankegas','enestas','ricevindas','sumiĝas','trametas','datumas','as-tempo','programeroj','akvumi','ambaŭkaze','aso','asoj','ason','asojn','metroj','metron','metrojn'])
EXPECTED_RUBY_PARTS={
  "teamanojn": [
    "team",
    "an"
  ],
  "tradukteamanojn": [
    "traduk",
    "team",
    "an"
  ],
  "aperdato": [
    "aper",
    "dat"
  ],
  "aristokratino": [
    "aristokrat",
    "in"
  ],
  "koleginoj": [
    "koleg",
    "in"
  ],
  "konilon": [
    "kon",
    "il"
  ],
  "vortuzon": [
    "vort",
    "uz"
  ],
  "ekstermovadaj": [
    "ekster",
    "mov",
    "ad"
  ],
  "Landaron": [
    "Land",
    "ar"
  ],
  "landaron": [
    "land",
    "ar"
  ],
  "dekstremuloj": [
    "dekstr",
    "em",
    "ul"
  ],
  "regularojn": [
    "regul",
    "ar"
  ],
  "skanaĵoj": [
    "skan",
    "aĵ"
  ],
  "malfidinda": [
    "mal",
    "fid",
    "ind"
  ],
  "Emociego": [
    "Emoci",
    "eg"
  ],
  "antaŭeko": [
    "antaŭ",
    "ek"
  ],
  "videbleco": [
    "vid",
    "ebl",
    "ec"
  ],
  "uzeblas": [
    "uz",
    "ebl",
    "as"
  ],
  "direktivoj": [
    "direkt",
    "iv"
  ],
  "organiziĝi": [
    "organ",
    "iz",
    "iĝ"
  ],
  "sendependa": [
    "sen",
    "de",
    "pend"
  ],
  "radio-programeroj": [
    "radi",
    "program",
    "er"
  ],
  "romanigoj": [
    "roman",
    "ig"
  ],
  "filozofion": [
    "filozofi"
  ],
  "aŭskultoviziton": [
    "aŭskult",
    "vizit"
  ],
  "civilizon": [
    "civiliz"
  ],
  "korelingvajn": [
    "kore",
    "lingv"
  ],
  "kronologion": [
    "kronologi"
  ],
  "IJK-on": [
    "IJK"
  ],
  "burokratio": [
    "burokrat"
  ],
  "dankegas": [
    "dank",
    "eg",
    "as"
  ],
  "enestas": [
    "en",
    "est",
    "as"
  ],
  "ricevindas": [
    "ricev",
    "ind",
    "as"
  ],
  "sumiĝas": [
    "sum",
    "iĝ",
    "as"
  ],
  "trametas": [
    "tra",
    "met",
    "as"
  ],
  "datumas": [
    "dat",
    "um",
    "as"
  ],
  "as-tempo": [
    "as",
    "temp"
  ],
  "programeroj": [
    "program",
    "er"
  ],
  "akvumi": [
    "akv",
    "um"
  ],
  "ambaŭkaze": [
    "ambaŭ",
    "kaz"
  ],
  "aso": [
    "as"
  ],
  "asoj": [
    "as"
  ],
  "ason": [
    "as"
  ],
  "asojn": [
    "as"
  ],
  "metroj": [
    "metr"
  ],
  "metron": [
    "metr"
  ],
  "metrojn": [
    "metr"
  ]
}
FORMATS={'pure':'替换后文字列のみ(仅)保留(简单替换)', 'kanji':'HTML格式_Ruby文字_大小调整_汉字替换', 'ruby':'HTML格式_Ruby文字_大小调整'}
CONTROLS=['@as@','aso','@aso@','asoj','@asoj@','@on@','@ajn@','@io@','@roman@','@kore@','@filozofi@','@civiliz@','@an@','@ĉar@','ĉar','@ret@','@semajn@o','@greganta@','@preganta@','@kordonita@','@stalagmito@','@sendeteneco@','@biontologio@','@povas@','@ludas@','@feliĉas@']
RUBY=re.compile(r'<ruby\b[^>]*>(.*?)<rt\b[^>]*>(.*?)</rt\s*>\s*</ruby\s*>',re.I|re.S)
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def plain(value):return html.unescape(re.sub(r'<[^>]*>','',value)).replace('\xa0',' ')
def source(value,mode):return plain(RUBY.sub(lambda m:m[2] if mode=='kanji' else m[1],value))
def visible(value):return plain(RUBY.sub(lambda m:m[1],value))
def cases():
 out=[]
 for w in sorted(TARGETS):
  out.extend([('@'+w+'@','target'),(w,'normal'),('%'+w+'%','percent'),('%@'+w+'@%','protected_at'),('@ '+w+' @','not_exact'),('@'+w+'!@','not_exact'),('@'+w+' kaj test@','not_exact'),('@x'+w+'@','not_exact'),('@'+w+'x@','not_exact'),('x'+w+'y','normal_embedding')])
 return out+[(w,'target' if w.startswith('@') and w.endswith('@') and w[1:-1] in TARGETS else 'control') for w in CONTROLS]
class ReviewedCorpusPayloadTests(unittest.TestCase):
 def test_manual_preview_and_explicit_scope(self):
  for lang in ('JA','ZH','KO'):
   app=ROOT/f'Esperanto-Kanji-Ruby-{lang}'
   rt=load(app/'esp_text_replacement_module.py','manual_corpus_'+lang)
   self.assertEqual(rt._REVIEWED_CORPUS_FORMS,TARGETS)
   self.assertEqual(rt._reviewed_corpus_renderings(list(TARGETS),[],[],False),{})
   manual=[(w,'MANUAL'+str(i),'$'+str(9000000+i)+'$') for i,w in enumerate(sorted(TARGETS))]
   for fmt in FORMATS.values():
    for i,w in enumerate(sorted(TARGETS)):
     expected='MANUAL'+str(i)
     got=rt.orchestrate_comprehensive_esperanto_text_replacement('@'+w+'@',[],[],[],manual,[],fmt,reviewed_local_decompositions=True)
     self.assertEqual(got,expected,(lang,w,fmt))
     preview=rt.create_replacements_list_for_localized_replacement('@'+w+'@',['@100@'],[],manual,reviewed_local_decompositions=True)
     self.assertEqual(preview[0][2],expected,(lang,w,'preview'))
     protected=rt.orchestrate_comprehensive_esperanto_text_replacement('%@'+w+'@%',[],[],[],manual,[],fmt,reviewed_local_decompositions=True)
     self.assertEqual(protected,'@'+w+'@')
   for w in ('sendeteneco','biontologio'):
    self.assertEqual(rt._reviewed_corpus_renderings([w],[],[],True),{})

 def test_real_rules_editions_source_inverse_and_optout(self):
  inv=load(ROOT/'Esperanto-Reverter-JA/esperanto_converter.py','corpus_inverse')
  recovery=load(ROOT/'Esperanto-Reverter-JA/html_source_recovery.py','corpus_recovery')
  indexes={edition:inv.build_mapping_index_cached(inv.effective_mapping_records(key,inv.load_dictionary_source(key))) for edition,key in [('current','pejvo-piv-20260620'),('legacy','pre-las-20261017')]}
  inputs=cases(); joined=' ◆ '.join(w for w,_ in inputs)
  expected_count=len(inputs)
  for lang in ('JA','ZH','KO'):
   app=ROOT/f'Esperanto-Kanji-Ruby-{lang}';sys.path.insert(0,str(app))
   rt=load(app/'esp_text_replacement_module.py','real_corpus_'+lang)
   ed=load(app/'esp_assignment_edition.py','edition_corpus_'+lang)
   old=load(BEFORE_ROOT/f'Esperanto-Kanji-Ruby-{lang}/esp_text_replacement_module.py','old_corpus_'+lang) if BEFORE_ROOT else None
   self.assertEqual(rt._REVIEWED_CORPUS_FORMS,TARGETS)
   code_hash=hashlib.sha256((app/'esp_text_replacement_module.py').read_bytes()).hexdigest()
   for edition in ('current','legacy'):
    for mode,fmt in FORMATS.items():
     gg,gl,g2=ed.load_lists(app/'app_data',mode,edition)
     def batch(engine,enabled):
      text=engine.orchestrate_comprehensive_esperanto_text_replacement(joined,[],gl,[],gg,g2,fmt,reviewed_local_decompositions=enabled)
      values=[v.strip() for v in text.split('◆')]
      self.assertEqual(len(values),expected_count)
      return values
     current=batch(rt,True)
     previous=batch(old,True) if old else None
     if old:self.assertEqual(batch(rt,False),batch(old,False),(lang,edition,mode,'custom-optout'))
     failures=[]; roundtrips=0; target_count=0
     for i,((inp,kind),out) in enumerate(zip(inputs,current)):
      before=previous[i] if previous else None
      if kind!='target':
       if previous:self.assertEqual(out,before,(lang,edition,mode,inp,'out-of-scope'))
       continue
      word=inp[1:-1];target_count+=1
      self.assertNotIn('@',out,(lang,edition,mode,word))
      if mode=='ruby':
       pairs=[(plain(m[1]),plain(m[2])) for m in RUBY.finditer(out)]
       self.assertEqual([rb for rb,rt in pairs],EXPECTED_RUBY_PARTS[word],(lang,edition,word,'reviewed segmentation'))
       if word in ('aso','asoj','ason','asojn'):
        self.assertEqual(pairs[0][1],{'JA':'エース','ZH':'A牌','KO':'에이스'}[lang])
       if word in ('dankegas','enestas','ricevindas','sumiĝas','trametas','datumas','as-tempo','uzeblas'):
        self.assertEqual([rt for rb,rt in pairs if rb=='as'],[{'JA':'現在形','ZH':'现在时','KO':'현재'}[lang]])
       if word=='romanigoj':
        self.assertEqual(pairs[0][1],{'JA':'ローマ字・小説','ZH':'罗马字;小说','KO':'로마자;소설'}[lang])
      if mode!='pure':
       self.assertEqual(source(out,mode),word,(lang,edition,mode,word))
       document=rt.apply_ruby_html_header_and_footer(out,fmt)
       recovered=recovery.recover_standard_html(document,'kanji' if mode=='kanji' else 'annotation')['text']
       self.assertEqual(recovered,word,(lang,edition,mode,word,'HTML source'))
      if mode in ('pure','kanji'):
       pure=out if mode=='pure' else visible(out)
       restored=inv.convert_kanji_esperanto_to_alphabet(pure,indexes[edition])
       old_text=None if before is None else before if mode=='pure' else visible(before)
       old_back=None if old_text is None else inv.convert_kanji_esperanto_to_alphabet(old_text,indexes[edition])
       if old_back is not None and old_back.lower()==word.lower():self.assertEqual(restored.lower(),word.lower(),(lang,edition,mode,word,'inverse regression',pure,restored))
       if restored.lower()!=word.lower():failures.append({'word':word,'rendered':pure,'restored':restored,'before_restored':old_back})
       else:roundtrips+=1
     self.assertFalse(failures,(lang,edition,mode,'reviewed target inverse mismatch',failures))
     REPORT.append({'language':lang,'edition':edition,'mode':mode,'inputs':expected_count,'target_count':target_count,'source_recovered':target_count if mode!='pure' else None,'inverse_exact':roundtrips if mode!='ruby' else None,'inverse_mismatches':failures,'before_compared':bool(old),'runtime_sha256':code_hash})
     print('corpus guard',lang,edition,mode,'targets',target_count,'inverse mismatches',len(failures),flush=True)
     ed._load_lists_cached.clear();del gg,gl,g2;gc.collect()
   self.assertEqual(hashlib.sha256((app/'esp_text_replacement_module.py').read_bytes()).hexdigest(),code_hash,(lang,'runtime changed during validation'))
   sys.path.pop(0)
if __name__=='__main__':unittest.main()
