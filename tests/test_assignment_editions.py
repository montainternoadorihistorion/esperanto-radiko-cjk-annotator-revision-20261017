"""Portable tests for the actual edition helper and page wrappers."""
from pathlib import Path
import argparse,ast,gzip,hashlib,importlib.util,json,logging,os,tempfile,unittest
from typing import List,Tuple
from unittest.mock import patch
logging.disable(logging.WARNING)
H=Path(__file__).resolve().parent
A=H.parent
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class EditionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=A/'Esperanto-Kanji-Ruby-JA';cls.data=cls.app/'app_data';cls.e=load(cls.app/'esp_assignment_edition.py','tested_editions')
 def test_two_choices_and_all_routes(self):
  e=self.e;self.assertEqual(e.EDITIONS,('current','legacy'))
  for lang in ('JA','ZH','KO'):
   data=A/f'Esperanto-Kanji-Ruby-{lang}'/'app_data'
   for mode in ('kanji','pure','kanji_csv','ruby','ruby_csv'):
    for version in e.EDITIONS:self.assertTrue(e.resolve_path(data,mode,version).is_file())
   self.assertEqual(e.resolve_path(data,'ruby','legacy'),e.resolve_path(data,'ruby','current'))
   self.assertEqual(e.resolve_path(data,'pure','legacy'),A/'assignment_editions/legacy/JA/pure.json.gz')
  with self.assertRaises(ValueError):e.resolve_path(self.data,'kanji','pre-dot')
 def test_file_stamp_and_bounded_shared_cache(self):
  e=self.e;e._load_lists_cached.clear()
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'data.json';q=Path(temp)/'other.json.gz'
   def content(glyph):return json.dumps({key:[['las',glyph,'$1$']] for key in (e.GLOBAL,e.LOCAL,e.TWO)},ensure_ascii=False).encode()
   old=content('留');new=content('放');self.assertEqual(len(old),len(new));p.write_bytes(old)
   original=json.load
   with patch.object(e.json,'load',wraps=original) as parser:
    self.assertEqual(e.load_lists_path(p)[0][0][1],'留');e.load_lists_path(p);self.assertEqual(parser.call_count,1)
    stamp=p.stat();p.write_bytes(new);os.utime(p,ns=(stamp.st_atime_ns,stamp.st_mtime_ns+2_000_000_000))
    self.assertEqual(e.load_lists_path(p)[0][0][1],'放');self.assertEqual(parser.call_count,2)
    q.write_bytes(gzip.compress(old,mtime=0));self.assertEqual(e.load_lists_path(q)[0][0][1],'留')
    e.load_lists_path(p);self.assertEqual(parser.call_count,4,'One-entry cache must evict the prior table')
   p.unlink()
   with self.assertRaises(FileNotFoundError):e.load_lists_path(p)
  e._load_lists_cached.clear()
 def test_metadata_all_stale_inputs_and_custom(self):
  e=self.e;options={'mode':'pure','format':'plain','letters':'circumflex'}
  with patch.object(e.st,'session_state',{}),patch.object(e,'edition_signature',return_value='asset-A'):
   current=e.result_metadata(self.data,'current',render_options=options)
   self.assertTrue(e.result_matches(current,self.data,'current',render_options=options))
   # A mocked asset signature is intentionally shared; source_id still blocks
   # accidental reuse from the other edition independently of file hashing.
   self.assertFalse(e.result_matches(current,self.data,'legacy',render_options=options))
   self.assertFalse(e.result_matches(current,self.data,'current',render_options={'mode':'ruby'}))
   e.st.session_state['user_corrections_session']=[{'word':'laso','decomp':'las/o'}]
   self.assertFalse(e.result_matches(current,self.data,'current',render_options=options))
   custom=e.result_metadata(self.data,'current','uploaded-hash',options)
   self.assertIsNone(custom['edition_id']);self.assertEqual(custom['source_id'],'custom_json')
   self.assertEqual(custom['automatic_correction'],'shared_current_annotations')
   self.assertFalse(e.result_matches(custom,self.data,'current','changed-hash',options))
   self.assertIn('custom_json',e.download_filename('result',custom,'txt'))
   self.assertIn(custom['signature'],e.html_download_metadata(custom))
  with patch.object(e.st,'session_state',{}),patch.object(e,'edition_signature',return_value='asset-B'):
   self.assertFalse(e.result_matches(current,self.data,'current',render_options=options))
 def test_edition_signature_automatically_tracks_assets(self):
  e=self.e
  with patch.object(e,'file_hash',return_value='same'):
   one=e.edition_signature(self.data,'current');two=e.edition_signature(self.data,'legacy')
   self.assertNotEqual(one,two)
  with patch.object(e,'file_hash',return_value='changed'):
   self.assertNotEqual(one,e.edition_signature(self.data,'current'))
 def test_pinned_links_require_exact_committed_public_bytes(self):
  e=self.e
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);p=root/'data.json';p.write_bytes(b'{}')
   commit='1'*40
   def git(args,**kwargs):
    if args[1:]==['remote','get-url','origin']:return 'https://github.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017.git\n'
    if args[1:]==['rev-parse','--show-toplevel']:return str(root)+'\n'
    if args[1]=='rev-parse':return 'a'*40+'\n'
    if args[1]=='hash-object':return 'a'*40+'\n'
    raise AssertionError(args)
   e._pinned_asset_url.clear()
   with patch.object(e.subprocess,'check_output',side_effect=git):
    url=e._pinned_asset_url(str(root),'data.json','hash-A',commit)
    self.assertIn('/'+commit+'/data.json',url);self.assertNotIn('/main/',url)
   def dirty(args,**kwargs):return 'b'*40 if args[1]=='hash-object' else git(args,**kwargs)
   with patch.object(e.subprocess,'check_output',side_effect=dirty):self.assertIsNone(e._pinned_asset_url(str(root),'data.json','hash-B',commit))
   with patch.object(e.subprocess,'check_output',side_effect=OSError('no git')):self.assertIsNone(e._pinned_asset_url(str(root),'data.json','hash-C',commit))
   e._pinned_asset_url.clear()
 def test_main_and_manual_delegate_to_same_actual_cache(self):
  e=self.e
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'fixture.json';p.write_text(json.dumps({e.GLOBAL:[['global']],e.LOCAL:[['local']],e.TWO:[['two']]}),encoding='utf-8')
   for lang in ('JA','ZH','KO'):
    app=A/f'Esperanto-Kanji-Ruby-{lang}'
    for path,name in ((app/'main.py','load_replacements_lists'),(next((app/'pages').glob('1_*.py')),'_load_lists')):
     tree=ast.parse(path.read_text(encoding='utf-8'));functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
     self.assertEqual(len(functions),1)
     ns={'editions':e,'Tuple':Tuple,'List':List};exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),ns)
     output=ns[name](str(p));expected=([['global']],[['local']],[['two']]) if name=='load_replacements_lists' else ([['local']],[['two']],[['global']])
     self.assertEqual(output,expected)
  e._load_lists_cached.clear()
 def test_readonly_current_data_and_shared_runtime(self):
  # Portable caller may provide the immutable manifest explicitly.
  if not BASELINE:self.skipTest('Baseline manifest not supplied')
  manifest=json.loads(BASELINE.read_bytes())
  for row in manifest['files']:
   if '/app_data/' in row['path'] or row['path'].endswith(('esp_text_replacement_module.py','esp_replacement_json_make_module.py','esp_generation_module.py')):
    self.assertEqual(hashlib.sha256((A/row['path']).read_bytes()).hexdigest(),row['sha256'],row['path'])
 def test_manual_dictionary_version_does_not_change_decomposition(self):
  for lang in ('JA','ZH','KO'):
   app=A/f'Esperanto-Kanji-Ruby-{lang}';data=str(app/'app_data');ov=load(app/'esp_overlay_module.py','edition_overlay_'+lang)
   for decomp in ('las/o','greft/i','dot/o','tualet/o','natur/dot/it/a'):
    old=ov.build_correction(decomp,data,'legacy');new=ov.build_correction(decomp,data,'current')
    self.assertEqual(old['decomp'],new['decomp']);self.assertEqual(old['word'],new['word']);self.assertEqual(old['ruby'],new['ruby'])
    self.assertNotEqual(old['kanji'],new['kanji'])

BASELINE=None
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--app-root',type=Path);p.add_argument('--baseline-manifest',type=Path);p.add_argument('--report',type=Path);args=p.parse_args()
 if args.app_root:A=args.app_root.resolve()
 BASELINE=args.baseline_manifest
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EditionTests))
 if args.report:args.report.write_text(json.dumps({'passed':result.wasSuccessful(),'tests':result.testsRun,'failures':[x[0].id() for x in result.failures],'errors':[x[0].id() for x in result.errors]},indent=2)+'\n',encoding='utf-8')
 raise SystemExit(0 if result.wasSuccessful() else 1)
