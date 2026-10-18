"""Four reviewed assignments and old-text aliases, including longer retained keys."""
import hashlib,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app
from build_reverter_dictionary_from_all_json import rows_from_all_json

CHANGES={'psitak':('鹦鹉','鹦ᴾˢ'),'uv':('葡萄','葡ᵁ'),'limon':('柠檬','柠'),'limonad':('柠檬水','柠水')}
CONTROLS={'uve':'葡膜','uveit':'葡膜炎ᵀ','vit':'葡','ampelops':'葡ᴬ','papag':'鹦',
 'konur':'鹦ᴷ','kakatu':'鹦ᴷᴷ','ara':'鹦ᴬ','testikit':'丸ᵀ炎ᵀ','orkidit':'丸ᴼ炎ᵀ',
 'turment':'虐','tortur':'虐ᵀᵀ','stafilokok':'葡球菌','ananas':'菠','jakv':'菠蜜',
 'prioritat':'优先','las':'放','emancip':'放ᴱ'}

def index(source):return app.build_mapping_index(app.load_dictionary_source(source))

@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_new_and_old_spellings_all_endings(source):
    mapping=index(source)
    for root,bodies in CHANGES.items():
        for body in bodies:
            for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','igi','igxis'):
                for suffix in (ending,ending.upper()):
                    assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+ending
    for root,body in CONTROLS.items():
        for suffix in ('','o','OJ'):
            assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+suffix.lower()

def test_longest_match_and_identifier_boundary_are_preserved():
    mapping=index('pejvo-piv-20260620')
    text='葡萄膜炎ᵀo 葡萄膜o 葡萄o 葡ᵁo 葡o 柠檬水o 柠水o 柠檬o 柠o 鹦ᴾˢo 鹦o'
    expected='uveito uveo uvo uvo vito limonado limonado limono limono psitako papago'
    assert app.convert_kanji_esperanto_to_alphabet(text,mapping)==expected
    # Adjacent keys must not lose a superscript or consume their neighbour.
    for root,(old,new) in CHANGES.items():
        assert app.convert_kanji_esperanto_to_alphabet(new+'o '+old+'o',mapping)==root+'o '+root+'o'
    assert app.convert_kanji_esperanto_to_alphabet('葡萄球菌o 葡球菌o',mapping)=='stafilokoko stafilokoko'

@pytest.mark.parametrize('source',['pre-las-20261017','pre-mirror-20261017'])
def test_explicit_historical_profiles_read_old_forms(source):
    mapping=index(source)
    for root,(old,new) in CHANGES.items():
        assert app.convert_kanji_esperanto_to_alphabet(old+'OJ',mapping)==root+'oj'

def test_reviewed_sources_and_exactly_four_reverse_aliases():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_text(encoding='utf-8'))
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_text(encoding='utf-8'))
    assert len(data['items'])==source['current_item_count']==10640
    rows=rows_from_all_json(data)
    assert len(rows)==source['current_csv_count']==10678
    for root,(old,new) in CHANGES.items():
        assert [r['body'] for r in data['items'] if r['sourceRoot']==root]==[new]
        assert not [r for r in data['items'] if r['body']==old]
        assert {(r['esperanto'],r['kanji']) for r in rows if r['kanji'] in (old,new)}=={(root,old),(root,new)}
        assert source['assignment_changes'][root]=={'old':old,'current':new}
        assert source['reverse_only_aliases'][old]==root
    for root,body in CONTROLS.items():
        assert [r['body'] for r in data['items'] if r['sourceRoot']==root]==[body]
    p=app.ROOT/'data/four-shared-assignments-20261017.json'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==source['four_shared_assignment_manifest_sha256']

@pytest.mark.parametrize('root',CHANGES)
def test_alias_collision_rejected_and_old_custom_source_kept(root):
    old,new=CHANGES[root]
    with pytest.raises(ValueError,match='conflicts with another root'):
        rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
    rows=rows_from_all_json({'items':[{'sourceRoot':root,'body':old}]})
    assert len(rows)==1 and rows[0]['kanji']==old

def test_ui_current_short_and_historical_long_forms():
    at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run()
    assert not at.exception
    at.text_area[0].set_value('鹦ᴾˢo 鹦鹉o 葡ᵁo 葡萄o 葡萄膜o 葡萄膜炎ᵀo 柠o 柠檬o 柠水o 柠檬水o')
    at.button[0].click().run()
    assert not at.exception
    assert at.text_area[1].value=='psitako psitako uvo uvo uveo uveito limono limono limonado limonado'
