"""Approved protez/ranc meanings, retained old spellings, profiles and actual UI."""
import hashlib,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter_zh as app
from build_reverter_dictionary_from_all_json import rows_from_all_json

CHANGES={'protez':('假肢','假体'),'ranc':('哈喇','酸败')}
CONTROLS={'hangar':'棚库','kontest':'异议','cisticerk':'囊尾虫','kruc':'十字',
 'testikit':'丸ᵀ炎ᵀ','orkidit':'丸ᴼ炎ᵀ','uve':'葡膜','uveit':'葡膜炎ᵀ',
 'las':'放','emancip':'放ᴱ','risort':'簧','anc^':'簧ᴬ'}
def index(source):return app.build_mapping_index(app.load_dictionary_source(source))

@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_new_old_spellings_endings_and_identifiers(source):
    mapping=index(source)
    for root,bodies in CHANGES.items():
        for body in bodies:
            for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','igi','igxis'):
                for suffix in (ending,ending.upper()):
                    assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+ending
    for root,body in CONTROLS.items():
        actualroot='anĉ' if root=='anc^' else root
        assert app.convert_kanji_esperanto_to_alphabet(body+'o',mapping)==actualroot+'o'

@pytest.mark.parametrize('root',CHANGES)
def test_old_alias_conflicts_rejected_and_old_custom_source_unmodified(root):
    old,new=CHANGES[root]
    with pytest.raises(ValueError,match='conflicts with another root'):
        rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
    rows=rows_from_all_json({'items':[{'sourceRoot':root,'body':old}]})
    assert len(rows)==1 and rows[0]['kanji']==old

def test_current_source_and_forward_candidates():
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_text(encoding='utf-8'))
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_text(encoding='utf-8'))
    assert len(data['items'])==source['current_item_count']==10640
    rows=rows_from_all_json(data);assert len(rows)==source['current_csv_count']==10678
    for root,(old,new) in CHANGES.items():
        assert [r['body'] for r in data['items'] if r['sourceRoot']==root]==[new]
        assert not [r for r in data['items'] if r['body']==old]
        assert {(r['esperanto'],r['kanji']) for r in rows if r['kanji'] in (old,new)}=={(root,old),(root,new)}
        assert source['assignment_changes'][root]=={'old':old,'current':new}
        assert source['reverse_only_aliases'][old]==root
    for root,body in CONTROLS.items():assert [r['body'] for r in data['items'] if r['sourceRoot']==root]==[body]
    assert hashlib.sha256((app.ROOT/'data/protez-ranc-assignments-20261017.json').read_bytes()).hexdigest()==source['protez_ranc_assignment_manifest_sha256']

def test_historical_profiles_keep_previous_targets():
    for source in ('pre-las-20261017','pre-mirror-20261017','pre-three-short-20261017'):
        mapping=index(source)
        assert app.convert_kanji_esperanto_to_alphabet('假肢o 哈喇a',mapping)=='protezo ranca'

def test_ui_new_old_spellings_and_retained_controls():
    at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run();assert not at.exception
    at.text_area[0].set_value('假体o 假肢o 酸败a 哈喇a 棚库o 异议i 囊尾虫o 十字o 丸ᵀ炎ᵀo 丸ᴼ炎ᵀo')
    at.button[0].click().run()
    assert not at.exception
    assert at.text_area[1].value=='protezo protezo ranca ranca hangaro kontesti cisticerko kruco testikito orkidito'
