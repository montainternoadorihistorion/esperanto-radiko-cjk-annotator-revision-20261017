"""Reviewed component identifiers, preserved old profiles, and boundary collisions."""
import csv
import hashlib
import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter_zh as app
from build_reverter_dictionary_from_all_json import to_unicode_esperanto_root

MANIFEST=json.loads((app.ROOT/'data/mirror-identifiers-20261017.json').read_text(encoding='utf-8'))
# Later reviewed body; retain the original mirror ledger and its internal LG identifier.
LATER_CURRENT_BODIES = {'mikrobologi': '微生物学ᴸᴳ'}


def index(source):
    return app.build_mapping_index(app.load_dictionary_source(source))


def rows(path):
    with path.open(encoding='utf-8',newline='') as handle:return list(csv.DictReader(handle))


def test_legacy_bytes_and_exact_reviewed_scope():
    assert hashlib.sha256(app.PRE_MIRROR_20261017_CSV.read_bytes()).hexdigest()==MANIFEST['previous_csv_sha256']
    old=rows(app.PRE_MIRROR_20261017_CSV);new=rows(app.PEJVO_PIV_20260620_CSV)
    targets={r['root'] for r in MANIFEST['changes']}
    targets.update({'stafilokok','psitak','uv','limon','limonad','uve','uveit','observatori','risort','anc^','lantern','lubrik','protez','ranc','krep','difrakt','mortez','meger','sutur','fraj','nostalgi','onk','fortres','onkogen','onkologi','satir','karikatur','sarkasm','spermat','spermati','silf','spermatocit','spermatofit','spermatogenez','spermatozo','dot','greft','tualet'})  # later approved changes have separate tests
    targets.update(({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|{'armatur','arund','donak','androzac','armoraci','diktamn'})))))))  # six-assignment behavior has a separate exhaustive test
    assert len(old)==10642 and len(new)==MANIFEST['current_csv_count']+34
    assert [r for r in old if r['source_root'] not in targets]==[r for r in new if r['source_root'] not in targets]
    assert index('legacy-minimal')==index('pejvo-piv-20260620')
    byroot={}
    for r in new:byroot.setdefault(r['source_root'],set()).add(r['kanji'])
    for change in MANIFEST['changes']:
        assert LATER_CURRENT_BODIES.get(change['root'], change['current']) in byroot[change['root']]
        # Old mirror aliases are not silently added to the current profile.
        if change['old']!=change['current']:
            assert change['old'] not in byroot[change['root']]


@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_every_reviewed_whole_root_reverts(source):
    mapping=index(source)
    for change in MANIFEST['changes']:
        assert app.convert_kanji_esperanto_to_alphabet(LATER_CURRENT_BODIES.get(change['root'], change['current']),mapping)==to_unicode_esperanto_root(change['root'])


def test_all_previous_rows_are_readable_in_the_explicit_legacy_profile():
    mapping=index('pre-mirror-20261017')
    for r in rows(app.PRE_MIRROR_20261017_CSV):
        assert app.convert_kanji_esperanto_to_alphabet(r['kanji'],mapping)==r['esperanto']


@pytest.mark.parametrize('ending',['','o','oj','on','ojn','a','aj','an','ajn','e','i','as','ita'])
def test_internal_and_whole_identifiers_are_not_consumed_as_other_roots(ending):
    current=index('pejvo-piv-20260620');legacy=index('pre-mirror-20261017')
    changes={r['root']:r for r in MANIFEST['changes'] if r['type']!='sep'}
    for root in ('testikit','orkidit','metapsiki','pedofili','polifoni','kseroftalmi','polipodi','endoskop','endoskopi','mikroskop','mikroskopi','tensimetr','tensiometr','dodekaedr'):
        for suffix in (ending,ending.upper()):
            assert app.convert_kanji_esperanto_to_alphabet(changes[root]['current']+suffix,current)==root+ending
            if changes[root]['old_monaco_body'] is not None:
                assert app.convert_kanji_esperanto_to_alphabet(changes[root]['old']+suffix,legacy)==root+ending


def test_reserved_bare_sequences_keep_their_existing_component_spelling():
    mapping=index('pejvo-piv-20260620')
    pairs={'超ᴹ心ᴾˢa':'metapsika','超ᴹ心ᴾˢio':'metapsikio','童ᴾ爱ᶠio':'pedofilio',
           '多ᴾ声ᶠᴼia':'polifonia','多ᴾ声ᶠᴼio':'polifonio','干ᴷ目ᴼᶠio':'kseroftalmio',
           '多ᴾ足ᴾᴼio':'polipodio','内ᴱᴰ镜ˢᴷo':'endoskopo','微镜ˢᴷo':'mikroskopo'}
    for surface,expected in pairs.items():
        assert app.convert_kanji_esperanto_to_alphabet(surface,mapping)==expected
        assert app.convert_kanji_esperanto_to_alphabet(' '+surface+' '+surface+' ',mapping)==' '+expected+' '+expected+' '
    # Existing retained aliases and unrelated earlier decisions.
    assert app.convert_kanji_esperanto_to_alphabet('放i 放ᴱo 菠o 菠蜜o 优先o 鸵o 协同o 榄o 椭圆a 椭圆ᴱo',mapping)=='lasi emancipo ananaso jakvo prioritato struto sinergio olivo ovala elipso'


def test_secondary_whole_identifiers_are_preserved_to_avoid_new_homographs():
    for source in ('pejvo-piv-20260620','pre-mirror-20261017'):
        mapping=index(source)
        assert app.convert_kanji_esperanto_to_alphabet('原兽ᵀo 神主义ᴰo 神家ᴰo',mapping)=='tripanosomo deismo deisto'
    assert app.convert_kanji_esperanto_to_alphabet('十二面ᴱᴰo',index('pejvo-piv-20260620'))=='dodekaedro'


def test_archived_profile_remains_available_but_is_not_a_visible_edition():
    assert 'pre-mirror-20261017' in app.DICTIONARY_SOURCES
    assert 'pre-mirror-20261017' not in app.dictionary_options()
    mapping=app.build_mapping_index(app.load_dictionary_source('pre-mirror-20261017'))
    assert app.convert_kanji_esperanto_to_alphabet('丸炎ᵀo 丸炎o',mapping)=='testikito orkidito'
