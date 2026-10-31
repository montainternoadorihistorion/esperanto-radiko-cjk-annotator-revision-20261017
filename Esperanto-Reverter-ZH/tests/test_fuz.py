"""Adopted fuz display, unchanged identifiers and fixed legacy."""
import hashlib,io,json
import pandas as pd
import pytest
import esperanto_converter_zh as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'; OLD='pre-las-20261017'
CHANGES={'fuz':('信管','燃ᶠᶻ')}
LEGACY_BODIES={'fuz':'信管'}
CONTROLS={'面团':'knedlik','柴油':'dizel','柴油ᴰˢ':'disel','钢':'ŝtal','肖':'portret','怕':'tim'}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')
def index(source):
 return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_endings_and_control_owners(source):
 mapping=index(source)
 for root,pair in CHANGES.items():
  body=pair[1] if source==CURRENT else LEGACY_BODIES[root]
  for suffix in SUFFIXES:
   for ending in (suffix,suffix.upper()):assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
   for keep,owner in CONTROLS.items():assert app.convert_kanji_esperanto_to_alphabet(keep+suffix,mapping)==owner+suffix
  assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  '+root+'o\n\t'+root+'as & <x>  '

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_longer_identifier_boundaries_and_owner_transfer(source):
 mapping=index(source);flat={key:owner for bucket in mapping.by_length.values() for key,owner in bucket.items()}
 for root,pair in CHANGES.items():
  body=pair[1] if source==CURRENT else LEGACY_BODIES[root]
  for continuation in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
   key=body+continuation; actual=app.convert_kanji_esperanto_to_alphabet(key+'o',mapping)
   if key in flat:assert actual==flat[key]+'o'
   else:assert not actual.startswith(root),(key,actual)
 assert flat['燃ᶠᶻ' if source==CURRENT else '信管']=='fuz'
 assert ('信管' if source==CURRENT else '燃ᶠᶻ') not in flat


def test_only_two_visible_editions_and_no_obsolete_aliases():
 assert app.dictionary_options()==[CURRENT,OLD] and len(app.DICTIONARY_SOURCES)==8
 records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
 old_bodies={x[0] for x in CHANGES.values()};new_bodies={x[1] for x in CHANGES.values()}
 for root,(old,new) in CHANGES.items():
  if old not in new_bodies:assert not [r for r in records if r[1]==old]
  assert {r[0] for r in records if r[1]==new}=={root}
  assert old not in app.CURRENT_INVERSE_ALIAS_PAIRS
 assert all(body not in app.CURRENT_INVERSE_ALIAS_PAIRS for body in old_bodies|new_bodies)

def test_manifest_and_downloads():
 source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
 path=app.ROOT/source['fuz_manifest'];manifest=json.loads(path.read_bytes())
 assert source['revision']=='2026-11-01-adopted'
 assert manifest['revision']=='2026-10-29-fuz'
 assert manifest['changes']=={root:list(pair) for root,pair in CHANGES.items()}
 assert manifest['safe_reverse_aliases']=={}
 assert manifest['ownership_transfers']=={}
 assert manifest['user_adopted_roots']==['fuz']
 assert manifest['identifier_propagated_roots']==[]
 assert manifest['metadata_only_changes']['fuel']['band']==['pejvo','basic']
 assert manifest['documentation_only_changes']['brul']['group_count']==[2,3]
 assert manifest['expected_target_items']['fuel']['body']=='燃ᶠ'
 assert manifest['expected_target_items']['brul']['body']=='燃'
 assert manifest['assignment_unchanged_item_count']==10639
 assert manifest['current_item_count']==manifest['baseline_item_count']==10640
 assert hashlib.sha256(path.read_bytes()).hexdigest()==source['fuz_manifest_sha256']
 for pair in CHANGES.values():
  for body in pair:assert body not in source['reverse_only_aliases']
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
 def ruby(root,annotation):
  body=CHANGES[root][1] if edition=='current' else LEGACY_BODIES[root]
  return f'<ruby>{body}<rt>{root}</rt></ruby>' if mode=='kanji' else f'<ruby>{root}<rt>{annotation}</rt></ruby>'
 content='  '+ruby('fuz','長く燃える')+'o '+ruby('fuz','長く燃える')+'a<br>\n\t&lt;保護&gt; &amp;  '
 html=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-10-25T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
 result=recover_standard_html(html,mode)
 assert result['text']=='  fuzo fuza\n\t<保護> &  ' and result['assignment_edition']==edition

def test_custom_dictionary_stays_custom():
 frame=pd.DataFrame([('custom','燃ᶠᶻ','0')],columns=['esperanto','kanji','priority'])
 records=app.effective_mapping_records('custom',frame)
 assert records==app.dataframe_to_mapping_records(frame)
 assert app.convert_kanji_esperanto_to_alphabet('燃ᶠᶻo',app.build_mapping_index_cached(records))=='customo'


@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_fuz_fuel_brul_longest_identifier_and_neighbor_roots(source):
 mapping=index(source)
 for suffix in ('','o','a','i','as','is','os','us','u','ojn','ado','antajn','ita'):
  for body,root in CONTROLS.items():assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+suffix
  current=app.convert_kanji_esperanto_to_alphabet('燃ᶠᶻ'+suffix,mapping)
  assert current==('fuz'+suffix if source==CURRENT else '燃ᶠᶻ'+suffix)
 for text in ('燃ᶠᶻᴬo','燃ᶠᵁo','燃ᶠᶻᶻo'):
  result=app.convert_kanji_esperanto_to_alphabet(text,mapping)
  assert not result.startswith(('fuel','fuz','brul')),(text,result)
