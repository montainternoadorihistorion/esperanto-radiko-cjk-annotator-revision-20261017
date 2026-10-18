"""Reviewed observatori display and exact historical reading compatibility."""
import hashlib,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app
from build_reverter_dictionary_from_all_json import rows_from_all_json

CHANGES={'observatori':('天文台','观台')}
CONTROLS={'uve':'葡膜','uveit':'葡膜炎ᵀ','majest':'庄严','subtil':'精细','observ':'观','spekt':'观ˢ','uv':'葡ᵁ','vit':'葡','ampelops':'葡ᴬ','psitak':'鹦ᴾˢ','papag':'鹦','limon':'柠','limonad':'柠水',
 'testikit':'丸ᵀ炎ᵀ','orkidit':'丸ᴼ炎ᵀ','turment':'虐','tortur':'虐ᵀᵀ','stafilokok':'葡球菌',
 'ananas':'菠','jakv':'菠蜜','prioritat':'优先','las':'放','emancip':'放ᴱ'}
def index(source):return app.build_mapping_index(app.load_dictionary_source(source))

@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_new_old_forms_endings_and_retained_roots(source):
    mapping=index(source)
    for root,bodies in CHANGES.items():
        for body in bodies:
            for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','igi','igxis'):
                for suffix in (ending,ending.upper()):
                    assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+ending
    for root,body in CONTROLS.items():
        for suffix in ('','o','OJ'):
            assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+suffix.lower()

def test_longest_match_and_internal_identifier():
    mapping=index('pejvo-piv-20260620')
    text='观台o 天文台o 观i 观ˢi 葡膜炎ᵀo 丸ᵀ炎ᵀo'
    assert app.convert_kanji_esperanto_to_alphabet(text,mapping)=='observatorio observatorio observi spekti uveito testikito'

@pytest.mark.parametrize('root',CHANGES)
def test_alias_conflicts_rejected_and_historical_custom_source_unchanged(root):
    old,new=CHANGES[root]
    with pytest.raises(ValueError,match='conflicts with another root'):
        rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
    rows=rows_from_all_json({'items':[{'sourceRoot':root,'body':old}]})
    assert len(rows)==1 and rows[0]['kanji']==old

def test_current_manifest_and_only_current_forward_candidates():
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
    assert hashlib.sha256((app.ROOT/'data/observatori-assignment-20261017.json').read_bytes()).hexdigest()==source['observatori_assignment_manifest_sha256']

def test_old_explicit_profile_remains_byte_defined_and_readable():
    pre=index('pre-mirror-20261017')
    assert app.convert_kanji_esperanto_to_alphabet('天文台o',pre)=='observatorio'
    now=index('pejvo-piv-20260620')
    assert app.convert_kanji_esperanto_to_alphabet('观台o 天文台o',now)=='observatorio observatorio'

def test_ui_old_and_current_words():
    at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run();assert not at.exception
    at.text_area[0].set_value('观台o 天文台o 葡膜o 葡膜炎ᵀo 庄严a 精细a')
    at.button[0].click().run()
    assert not at.exception and at.text_area[1].value=='observatorio observatorio uveo uveito majesta subtila'
