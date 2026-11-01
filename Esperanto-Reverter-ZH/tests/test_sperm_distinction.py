"""Approved sperm distinction and explicit old-text version."""
import csv,hashlib,io,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter_zh as app
from build_reverter_dictionary_from_all_json import rows_from_all_json
PROFILE='pre-sperm-distinction-20261018'
CHANGES={'spermat':('精ˢ','精子'),'spermati':('精ˢᴵ','精子ˢᴵ'),'silf':('精ˢᴸ','精ˢ'),'spermatocit':('精ˢ胞ᶜᴵ','精子胞ᶜᴵ'),'spermatofit':('精ˢ植ᶠ','精子植ᶠ'),'spermatogenez':('精ˢ源ᴳ','精子源ᴳ'),'spermatozo':(None,'精子ˢᶻ')}
CONTROLS={'精液':'sperm','精液ᶜ̂':'ĉur','种ˢᴿ':'sperm','讽':'satir','讽ᴷ':'karikatur','讽ˢᴿ':'sarkasm','嫁接':'greft','嫁妆':'dot','没收':'konfisk','君主':'monark','怀ᴺ':'nostalgi','瘤ᴼ':'onk','堡ᶠᴿ':'fortres','巧合':'koincid'}
def index(source):return app.build_mapping_index(app.load_dictionary_source(source))
@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_current_ids_safe_old_aliases_and_preserved_roots(source):
 mapping=index(source)
 targets={body:root for root,(old,body) in CHANGES.items()}
 targets.update({old:root for root,(old,new) in CHANGES.items() if old and root!='spermat'})
 targets.update(CONTROLS)
 for body,root in targets.items():
  for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','as','ita','igi'):
   for suffix in (ending,ending.upper()):assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+ending
def test_complete_snapshot_and_approved_scope():
 source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
 oldrows=list(csv.DictReader(io.StringIO(app.PRE_SPERM_DISTINCTION_20261018_CSV.read_text(encoding='utf-8'))))
 newrows=list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding='utf-8'))))
 assert len(oldrows)==10670 and len(newrows)==10678
 assert [r for r in oldrows if r['source_root'] not in (set(CHANGES)|{'dot','greft','tualet'}|({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|(({'klarion','stal','fuz','ligatur','eu^fori','sofism','hibisk'}|{'instig', 'karoten', 'psilofit', 'panak', 'pense', 'karot', 'pasiflor', 'ginseng', 'delic', 'delekt', 'elegi'})|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))))]==[r for r in newrows if r['source_root'] not in (set(CHANGES)|{'dot','greft','tualet'}|({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|(({'klarion','stal','fuz','ligatur','eu^fori','sofism','hibisk'}|{'instig', 'karoten', 'psilofit', 'panak', 'pense', 'karot', 'pasiflor', 'ginseng', 'delic', 'delekt', 'elegi'})|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))))]
 profile=source['pre_sperm_distinction_profile'];assert profile['id']==PROFILE
 assert profile['csv_sha256']=='87e9317a0fc35ef1ae50462002ec8143b129c3e64112f4eda360336796fe50fb'
 assert profile['snippet_csv_sha256']=='d9aa07044691264d371b2e526b7167264e3cc41790e8e6bb948ed829997d7ff7'
 for name in ('csv','snippet_csv'):assert hashlib.sha256((app.ROOT/profile[name]).read_bytes()).hexdigest()==profile[name+'_sha256']
 old=index(PROFILE);now=index('pejvo-piv-20260620')
 assert old==app.build_mapping_index(app.read_assignment_csv(app.PRE_SPERM_DISTINCTION_SNIPPET_20261018_CSV))
 for r in oldrows:assert app.convert_kanji_esperanto_to_alphabet(r['kanji'],old)==r['esperanto']
 for r in newrows:assert app.convert_kanji_esperanto_to_alphabet(r['kanji'],now)==r['esperanto']
 assert [r['kanji'] for r in oldrows if r['source_root'] not in ({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|(({'klarion','stal','fuz','ligatur','eu^fori','sofism','hibisk'}|{'instig', 'karoten', 'psilofit', 'panak', 'pense', 'karot', 'pasiflor', 'ginseng', 'delic', 'delekt', 'elegi'})|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))) and app.convert_kanji_esperanto_to_alphabet(r['kanji'],now)!=r['esperanto']]==['精ˢ','妆']
 assert app.convert_kanji_esperanto_to_alphabet('精ˢo 精ˢᴸo 精ˢᴵo 精液o 精液ᶜ̂o 讽o',old)=='spermato silfo spermatio spermo ĉuro satiro'
def test_aliases_reject_conflicts_and_current_source_is_pinned():
 for root,(old,new) in CHANGES.items():
  if not old or root=='spermat':continue
  with pytest.raises(ValueError,match='conflicts with another root'):rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
 data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
 source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
 rows=rows_from_all_json(data)
 assert len(data['items'])==source['current_item_count']==10640
 assert len(rows)==source['current_csv_count']==10678
 assert [(r['kanji'],r['esperanto']) for r in rows if r['kanji']=='精ˢ']==[('精ˢ','silf')]
 assert '精ˢ' not in source['reverse_only_aliases']
 assert [r['body'] for r in data['items'] if r['sourceRoot']=='spermatozo']==['精子ˢᶻ']
 assert hashlib.sha256((app.ROOT/'data/sperm-distinction-20261018.json').read_bytes()).hexdigest()==source['sperm_distinction_manifest_sha256']
def test_archived_profile_remains_available_but_is_not_a_visible_edition():
    assert 'pre-sperm-distinction-20261018' in app.DICTIONARY_SOURCES
    assert 'pre-sperm-distinction-20261018' not in app.dictionary_options()
    mapping=app.build_mapping_index(app.load_dictionary_source('pre-sperm-distinction-20261018'))
    assert app.convert_kanji_esperanto_to_alphabet('精ˢo 精ˢᴸo 精液o',mapping)=='spermato silfo spermo'
