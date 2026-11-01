"""Adopted ligatur display, unchanged identifiers and fixed legacy."""
import hashlib,io,json
import pandas as pd
import pytest
import esperanto_converter as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'; OLD='pre-las-20261017'
CHANGES={"karot":["胡萝卜","参ᴷ"],"panak":["草ᴾᴺ","参ᴾ"],"ginseng":["草ᴳᴳ","参ᴳ"],"karoten":["萝卜素","参ᴷ素"],"instig":["唆","促ᴵ"],"elegi":["挽歌","哀歌"],"delic":["珍","悦ᴰ"],"delekt":["悦ᴰ","悦ᴰᴷ"],"pense":["草ᴾˢ","草ᴾᴺ"],"psilofit":["草ᴾᶠ","草ᴾˢ"],"pasiflor":["草ᴾᴬˢ","草ᴾᶠ"]}
LEGACY_BODIES={"karot":"胡萝卜","panak":"草ᴾᴺ","ginseng":"草ᴳᴳ","karoten":"萝卜素","instig":"唆","elegi":"挽歌","delic":"珍","delekt":"悦ᴰ","pense":"草ᴾˢ","psilofit":"草ᴾᶠ","pasiflor":"草ᴾᴬˢ"}
CONTROLS={'参':'stab','参ᴿ':'referenc','悦':'plaĉ','促':'akcel','促ᶠ':'forc','结':'lig','结ᴺ':'nod','残船':'vrak','册ᴱ':'ekzempler'}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')
def index(source):
 return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))


@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_all_adopted_and_propagated_endings(source):
 mapping=index(source)
 for root,pair in CHANGES.items():
  body=pair[1] if source==CURRENT else LEGACY_BODIES[root]
  for suffix in SUFFIXES:
   for ending in (suffix,suffix.upper()):assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
  assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  '+root+'o\n\t'+root+'as & <x>  '
 for body,root in CONTROLS.items():
  for suffix in SUFFIXES:assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+suffix

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_long_identifier_boundaries_and_moved_owners(source):
 mapping=index(source);flat={key:owner for bucket in mapping.by_length.values() for key,owner in bucket.items()}
 for root,pair in CHANGES.items():
  body=pair[1] if source==CURRENT else LEGACY_BODIES[root]
  for continuation in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
   key=body+continuation;actual=app.convert_kanji_esperanto_to_alphabet(key+'o',mapping)
   if key in flat:assert actual==flat[key]+'o'
   else:assert not actual.startswith(root),(key,actual)
 moves={'草ᴾᴺ':('panak','pense'),'草ᴾˢ':('pense','psilofit'),'草ᴾᶠ':('psilofit','pasiflor'),'悦ᴰ':('delekt','delic')}
 for body,(old,new) in moves.items():assert flat[body]==(new if source==CURRENT else old)
 if source==CURRENT:
  assert app.convert_kanji_esperanto_to_alphabet('参ᴷ素o 参ᴷo 参ᴷᴬo',mapping)=='karoteno karoto 参ᴷᴬo'
  assert app.convert_kanji_esperanto_to_alphabet('悦ᴰᴷo 悦ᴰo 悦ᴰᴷᴬo',mapping)=='delekto delico 悦ᴰᴷᴬo'

def test_no_intermediate_edition_or_obsolete_aliases():
 assert app.dictionary_options()==[CURRENT,OLD] and len(app.DICTIONARY_SOURCES)==8
 records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
 old_bodies={x[0] for x in CHANGES.values()};new_bodies={x[1] for x in CHANGES.values()}
 for root,(old,new) in CHANGES.items():
  if old not in new_bodies:assert not [r for r in records if r[1]==old]
  assert {r[0] for r in records if r[1]==new}=={root}
 assert all(body not in app.CURRENT_INVERSE_ALIAS_PAIRS for body in old_bodies|new_bodies)

def test_manifest_downloads_and_approved_scope():
 source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
 path=app.ROOT/source['adopted_20261101_manifest'];manifest=json.loads(path.read_bytes())
 assert source['revision']=='2026-11-02-hibisk'
 assert manifest['revision']=='2026-11-01-adopted'
 assert manifest['changes']=={root:list(pair) for root,pair in CHANGES.items()}
 assert manifest['safe_reverse_aliases']=={}
 assert set(manifest['user_adopted_roots'])=={'karot','panak','ginseng','karoten','instig','elegi','delic'}
 assert set(manifest['identifier_propagated_roots'])=={'delekt','pense','psilofit','pasiflor'}
 assert manifest['metadata_only_changes']=={}
 assert manifest['assignment_unchanged_item_count']==10629
 assert manifest['current_item_count']==manifest['baseline_item_count']==10640
 assert hashlib.sha256(path.read_bytes()).hexdigest()==source['adopted_20261101_manifest_sha256']
 full,two=app.edition_download_data(CURRENT)
 assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
 assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
 assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
 legacy,legacy_two=app.edition_download_data(OLD)
 assert hashlib.sha256(legacy).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
 assert hashlib.sha256(legacy_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_standard_html_and_protected_text(edition,mode):
 def ruby(root):
  body=CHANGES[root][1] if edition=='current' else LEGACY_BODIES[root]
  return f'<ruby>{body}<rt>{root}</rt></ruby>' if mode=='kanji' else f'<ruby>{root}<rt>注釈</rt></ruby>'
 content='  '+ruby('karot')+'o '+ruby('karoten')+'a<br>\n\t&lt;保護&gt; &amp;  '
 html=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-11-01T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
 result=recover_standard_html(html,mode)
 assert result['text']=='  karoto karotena\n\t<保護> &  ' and result['assignment_edition']==edition

def test_custom_dictionary_unchanged():
 frame=pd.DataFrame([('custom','参ᴷ素','0')],columns=['esperanto','kanji','priority'])
 records=app.effective_mapping_records('custom',frame)
 assert records==app.dataframe_to_mapping_records(frame)
 assert app.convert_kanji_esperanto_to_alphabet('参ᴷ素o',app.build_mapping_index_cached(records))=='customo'
