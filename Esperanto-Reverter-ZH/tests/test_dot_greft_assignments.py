"""Approved dot/greft assignments and explicit immediate old-text version."""
import csv,hashlib,io,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter_zh as app
from build_reverter_dictionary_from_all_json import rows_from_all_json
PROFILE='pre-dot-greft-20261018'
CHANGES={'greft':('嫁接','移植'),'dot':('嫁妆','妆'),'tualet':('妆','妆ᵀ')}
def index(source):return app.build_mapping_index(app.load_dictionary_source(source))
@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_current_and_safe_aliases(source):
 mapping=index(source)
 targets={'移植':'greft','嫁接':'greft','妆':'dot','嫁妆':'dot','妆ᵀ':'tualet','妆ˢ̂':'ŝmink','妆ᴷ':'kosmetik','精子':'spermat','精子ˢᶻ':'spermatozo','精液':'sperm','精液ᶜ̂':'ĉur','精ˢ':'silf','讽':'satir'}
 for body,root in targets.items():
  for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','as','ita','igi'):
   for suffix in (ending,ending.upper()):assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+ending
def test_full_snapshot_all_keys_and_only_approved_transfer():
 source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
 oldrows=list(csv.DictReader(io.StringIO(app.PRE_DOT_GREFT_20261018_CSV.read_text(encoding='utf-8'))))
 newrows=list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding='utf-8'))))
 assert len(oldrows)==10676 and len(newrows)==10678
 assert [r for r in oldrows if r['source_root'] not in (set(CHANGES)|({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|({'klarion'}|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))))]==[r for r in newrows if r['source_root'] not in (set(CHANGES)|({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|({'klarion'}|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))))]
 profile=source['pre_dot_greft_profile'];assert profile['id']==PROFILE
 assert profile['csv_sha256']=='3219d77284ddf21c90b6d33a580ead00a3c38b2628b09ed205883c9255f6bd65'
 assert profile['snippet_csv_sha256']=='22ef2de51e53bd19314b6c7f140aa8d82b0914bd71bfdd0b2c943cbc71591f07'
 for name in ('csv','snippet_csv'):assert hashlib.sha256((app.ROOT/profile[name]).read_bytes()).hexdigest()==profile[name+'_sha256']
 old=index(PROFILE);now=index('pejvo-piv-20260620')
 assert old==app.build_mapping_index(app.read_assignment_csv(app.PRE_DOT_GREFT_SNIPPET_20261018_CSV))
 for r in oldrows:assert app.convert_kanji_esperanto_to_alphabet(r['kanji'],old)==r['esperanto']
 for r in newrows:assert app.convert_kanji_esperanto_to_alphabet(r['kanji'],now)==r['esperanto']
 assert [r['kanji'] for r in oldrows if r['source_root'] not in ({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|({'klarion'}|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))) and app.convert_kanji_esperanto_to_alphabet(r['kanji'],now)!=r['esperanto']]==['妆']
def test_version_specific_boundary_and_suffix_examples():
 old=index(PROFILE);now=index('pejvo-piv-20260620')
 pairs={'妆o':('tualeto','doto'),'妆水o':('tualetakvo','dotakvo'),'移植o':('translaciplanto','grefto'),'移植ᶠo':('translacifito','translacifito'),'移o植o':('translacioplanto','translacioplanto'),'越植i':('transplanti','transplanti'),'嫁接物o':('greftaĵo','greftaĵo'),'嫁妆o':('doto','doto')}
 for text,(a,b) in pairs.items():assert (app.convert_kanji_esperanto_to_alphabet(text,old),app.convert_kanji_esperanto_to_alphabet(text,now))==(a,b)
 for text,want in {'妆ᵀ水o':'tualetakvo','心移植o':'korgrefto','移植物o':'greftaĵo','移植o基o':'greftobazo','然妆受a':'naturdotita','无妆a':'sendota'}.items():assert app.convert_kanji_esperanto_to_alphabet(text,now)==want
def test_aliases_reject_conflicts_and_current_source_is_pinned():
 for root in ('greft','dot'):
  old,new=CHANGES[root]
  with pytest.raises(ValueError,match='conflicts with another root'):rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
 data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
 source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
 rows=rows_from_all_json(data)
 assert len(data['items'])==source['current_item_count']==10640
 assert len(rows)==source['current_csv_count']==10678
 assert [(r['kanji'],r['esperanto']) for r in rows if r['kanji']=='妆']==[('妆','dot')]
 assert '妆' not in source['reverse_only_aliases']
 assert hashlib.sha256((app.ROOT/'data/dot-greft-20261018.json').read_bytes()).hexdigest()==source['dot_greft_manifest_sha256']
def test_archived_profile_remains_available_but_is_not_a_visible_edition():
    assert 'pre-dot-greft-20261018' in app.DICTIONARY_SOURCES
    assert 'pre-dot-greft-20261018' not in app.dictionary_options()
    mapping=app.build_mapping_index(app.load_dictionary_source('pre-dot-greft-20261018'))
    assert app.convert_kanji_esperanto_to_alphabet('妆o 移植o 精子o',mapping)=='tualeto translaciplanto spermato'
