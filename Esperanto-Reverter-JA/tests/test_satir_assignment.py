"""Preserve pre-satir text explicitly; only the three satir sharing-group rows change."""
import csv,hashlib,io,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app
from build_reverter_dictionary_from_all_json import rows_from_all_json
PROFILE='pre-satir-20261017'
CHANGES={'satir':('讽刺','讽'),'karikatur':('讽','讽ᴷ'),'sarkasm':('讽ˢ','讽ˢᴿ')}
CONTROLS={'精液':'sperm','精液ᶜ̂':'ĉur','精ˢ':'silf','精ˢᴵ':'spermati','种ˢᴿ':'sperm','嫁接':'greft','嫁妆':'dot','没收':'konfisk','君主':'monark','怀ᴺ':'nostalgi','瘤ᴼ':'onk','堡ᶠᴿ':'fortres','巧合':'koincid'}
def index(source):return app.build_mapping_index(app.load_dictionary_source(source))
@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_current_senses_ids_aliases_and_unapproved_roots(source):
    mapping=index(source)
    targets={'讽':'satir','讽刺':'satir','讽ᴷ':'karikatur','讽ˢᴿ':'sarkasm','讽ˢ':'sarkasm',**CONTROLS}
    for body,root in targets.items():
        for suffix in ('','o','oj','on','ojn','a','aj','ajn','e','i','as','ita','igi'):
            for ending in (suffix,suffix.upper()):assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
def test_snapshot_is_complete_and_changes_only_reviewed_rows():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    oldrows=list(csv.DictReader(io.StringIO(app.PRE_SATIR_20261017_CSV.read_text(encoding='utf-8'))))
    newrows=list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding='utf-8'))))
    assert len(oldrows)==10668 and len(newrows)==10678
    scope=set(CHANGES)|{'spermat','spermati','silf','spermatocit','spermatofit','spermatogenez','spermatozo','dot','greft','tualet'}
    scope |= ({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|({'klarion'}|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'})))))))))))
    assert [r for r in oldrows if r['source_root'] not in scope]==[r for r in newrows if r['source_root'] not in scope]
    profile=source['pre_satir_profile'];assert profile['id']==PROFILE
    assert profile['csv_sha256']=='ec6d04c11d3bee9fc2063342b73b884c1fc02819a736dc033f5b6e99e320f6c8'
    assert profile['snippet_csv_sha256']=='803a60e0b5b7017601378681876b30f15d926d4b2028694f116c009e0f7ec416'
    for name in ('csv','snippet_csv'):assert hashlib.sha256((app.ROOT/profile[name]).read_bytes()).hexdigest()==profile[name+'_sha256']
    old=index(PROFILE);now=index('pejvo-piv-20260620')
    assert old==app.build_mapping_index(app.read_assignment_csv(app.PRE_SATIR_SNIPPET_20261017_CSV))
    for r in oldrows:assert app.convert_kanji_esperanto_to_alphabet(r['kanji'],old)==r['esperanto']
    changes=[r['kanji'] for r in oldrows if r['source_root'] not in ({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|({'klarion'}|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))) and app.convert_kanji_esperanto_to_alphabet(r['kanji'],now)!=r['esperanto']]
    assert set(changes)=={'讽','精ˢ','妆'}
    assert app.convert_kanji_esperanto_to_alphabet('讽o 讽刺o 讽ˢo 精液o 精液ᶜ̂o 精ˢo',old)=='karikaturo satiro sarkasmo spermo ĉuro spermato'
    assert app.convert_kanji_esperanto_to_alphabet('怀ᴺo 瘤ᴼo 堡ᶠᴿo',old)=='nostalgio onko fortreso'
def test_safe_aliases_cannot_overwrite_owners_and_bare_feng_has_one_owner():
    for root,old,new in [('satir','讽刺','讽'),('sarkasm','讽ˢ','讽ˢᴿ')]:
        with pytest.raises(ValueError,match='conflicts with another root'):rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes());source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    rows=rows_from_all_json(data);assert len(data['items'])==source['current_item_count']==10640 and len(rows)==source['current_csv_count']==10678
    assert [(r['kanji'],r['esperanto']) for r in rows if r['kanji']=='讽']==[('讽','satir')]
    assert '讽' not in source['reverse_only_aliases']
    assert [r['body'] for r in data['items'] if r['sourceRoot']=='spermatozo']==['精子ˢᶻ']
    assert hashlib.sha256((app.ROOT/'data/satir-assignment-20261017.json').read_bytes()).hexdigest()==source['satir_assignment_manifest_sha256']
def test_archived_profile_remains_available_but_is_not_a_visible_edition():
    assert 'pre-satir-20261017' in app.DICTIONARY_SOURCES
    assert 'pre-satir-20261017' not in app.dictionary_options()
    mapping=app.build_mapping_index(app.load_dictionary_source('pre-satir-20261017'))
    assert app.convert_kanji_esperanto_to_alphabet('讽o 讽刺o 讽ˢo',mapping)=='karikaturo satiro sarkasmo'
