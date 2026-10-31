"""Adopted sozi/fobi displays, regenerated identifiers and fixed legacy."""
import hashlib,io,json
import pandas as pd
import pytest
import esperanto_converter_zh as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'; OLD='pre-las-20261017'
CHANGES={'sozi':('替身','肖ˢ'),'fobi':('症','怕ᶠ'),'fob':('怕ᶠ','怕ᶠᴼ'),'simptom':('症ˢ','症'),'agorafobi':('场ᴬ症','场ᴬ怕ᶠ'),'hidrofobi':('水ᴴ症','水ᴴ怕ᶠ'),'ksenofobi':('外ᴷˢ症','外ᴷˢ怕ᶠ'),'hidrofob':('水ᴴ怕ᶠ','水ᴴ怕ᶠᴼ'),'ksenofob':('外ᴷˢ怕ᶠ','外ᴷˢ怕ᶠᴼ'),'simptomologi':('症ˢ学ᴸᴳ','症学ᴸᴳ')}
LEGACY_BODIES={'sozi': '替身', 'fobi': '症', 'fob': '怕ᶠ', 'simptom': '症ˢ', 'agorafobi': '场症', 'hidrofobi': '水症', 'ksenofobi': '外症', 'hidrofob': '水怕', 'ksenofob': '外怕', 'simptomologi': '症学'}
CONTROLS={'脂':'gras','蜂':'abel','棍':'klab','船左':'babord','程ᴾᶜ':'proces','程ᴾᶻ':'procez','肖':'portret','怕':'tim'}
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
 assert flat['怕ᶠ']==('fobi' if source==CURRENT else 'fob')
 assert flat['症']==('simptom' if source==CURRENT else 'fobi')
 assert app.convert_kanji_esperanto_to_alphabet('怕ᶠᴼo',mapping)==('fobo' if source==CURRENT else '怕ᶠᴼo')
 assert app.convert_kanji_esperanto_to_alphabet('怕ᶠᴼᴬo',mapping) not in ('fobo','fobio')
 assert flat['水ᴴ怕ᶠ' if source==CURRENT else '水怕']==('hidrofobi' if source==CURRENT else 'hidrofob')
 assert flat['外ᴷˢ怕ᶠ' if source==CURRENT else '外怕']==('ksenofobi' if source==CURRENT else 'ksenofob')



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
 path=app.ROOT/source['sozi_fobi_manifest'];manifest=json.loads(path.read_bytes())
 assert source['revision']=='2026-11-01-adopted'
 assert manifest['revision']=='2026-10-26-sozi-fobi'
 assert manifest['changes']=={root:list(pair) for root,pair in CHANGES.items()}
 assert manifest['safe_reverse_aliases']=={}
 assert manifest['ownership_transfers']=={'怕ᶠ':{'before':'fob','after':'fobi'},'症':{'before':'fobi','after':'simptom'},'水ᴴ怕ᶠ':{'before':'hidrofob','after':'hidrofobi'},'外ᴷˢ怕ᶠ':{'before':'ksenofob','after':'ksenofobi'}}
 assert manifest['user_adopted_roots']==['sozi','fobi']
 assert set(manifest['identifier_propagated_roots'])==set(CHANGES)-{'sozi','fobi'}
 assert manifest['assignment_unchanged_item_count']==10630
 assert manifest['current_item_count']==manifest['baseline_item_count']==10640
 assert hashlib.sha256(path.read_bytes()).hexdigest()==source['sozi_fobi_manifest_sha256']
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
 content='  '+ruby('sozi','血縁関係のないそっくりな人')+'o '+ruby('fobi','病的な恐れ')+'o<br>\n\t&lt;保護&gt; &amp;  '
 html=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-10-25T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
 result=recover_standard_html(html,mode)
 assert result['text']=='  sozio fobio\n\t<保護> &  ' and result['assignment_edition']==edition

def test_custom_dictionary_stays_custom():
 frame=pd.DataFrame([('custom','怕ᶠ','0')],columns=['esperanto','kanji','priority'])
 records=app.effective_mapping_records('custom',frame)
 assert records==app.dataframe_to_mapping_records(frame)
 assert app.convert_kanji_esperanto_to_alphabet('怕ᶠo',app.build_mapping_index_cached(records))=='customo'
