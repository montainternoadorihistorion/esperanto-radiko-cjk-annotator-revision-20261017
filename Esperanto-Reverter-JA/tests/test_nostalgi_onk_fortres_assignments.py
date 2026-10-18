"""Three approved roots and two faithful mirrors; retain legacy text and controls."""
import hashlib,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app
from build_reverter_dictionary_from_all_json import rows_from_all_json
CHANGES={'nostalgi':('怀旧','怀ᴺ'),'onk':('肿瘤','瘤ᴼ'),'fortres':('堡垒','堡ᶠᴿ'),'onkogen':('肿瘤生ᴳ','瘤ᴼ生ᴳ'),'onkologi':('肿瘤学ᴸᴳ','瘤ᴼ学ᴸᴳ')}
CONTROLS={'巧合':'koincid','讽刺':'satir','精液':'sperm','精液ᶜ̂':'ĉur','精ˢ':'silf','种ˢᴿ':'sperm','瘤ᵀ':'tumor','怀':'sin','灌':'klister','缝ˢᴿ':'sutur','卵ᶠ':'fraj','棱镜':'prism'}
def index(source):return app.build_mapping_index(app.load_dictionary_source(source))
@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_current_and_legacy_targets_with_endings(source):
    mapping=index(source)
    for root,bodies in CHANGES.items():
        for body in bodies:
            for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','as','igi','igxis'):
                for suffix in (ending,ending.upper()):assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+ending
    for body,root in CONTROLS.items():assert app.convert_kanji_esperanto_to_alphabet(body+'o',mapping)==root+'o'
@pytest.mark.parametrize('root',CHANGES)
def test_alias_cannot_steal_an_existing_owner(root):
    old,new=CHANGES[root]
    with pytest.raises(ValueError,match='conflicts with another root'):
        rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
    rows=rows_from_all_json({'items':[{'sourceRoot':root,'body':old}]})
    assert len(rows)==1 and rows[0]['kanji']==old
def test_current_manifest_and_all_five_source_items():
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_text(encoding='utf-8'))
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_text(encoding='utf-8'))
    assert len(data['items'])==source['current_item_count']==10640
    rows=rows_from_all_json(data);assert len(rows)==source['current_csv_count']==10678
    for root,(old,new) in CHANGES.items():
        matches=[r for r in data['items'] if r['sourceRoot']==root]
        assert len(matches)==1 and matches[0]['body']==new
        assert matches[0]['base'] is (root in {'onkogen','onkologi'})
        assert not [r for r in data['items'] if r['body']==old]
        assert {(r['esperanto'],r['kanji']) for r in rows if r['kanji'] in (old,new)}=={(root,old),(root,new)}
        assert source['assignment_changes'][root]=={'old':old,'current':new}
        assert source['reverse_only_aliases'][old]==root
    for body,root in CONTROLS.items():
        assert any(r['kanji']==body and r['esperanto']==root for r in rows)
    manifest=app.ROOT/'data/nostalgi-onk-fortres-assignments-20261017.json'
    assert hashlib.sha256(manifest.read_bytes()).hexdigest()==source['nostalgi_onk_fortres_assignment_manifest_sha256']
def test_legacy_profiles_keep_old_target_meanings():
    for source in ('pre-las-20261017','pre-mirror-20261017','pre-three-short-20261017'):
        assert app.convert_kanji_esperanto_to_alphabet('怀旧o 肿瘤o 堡垒o',index(source))=='nostalgio onko fortreso'
def test_actual_ui_internal_ids_and_old_spellings():
    at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run();assert not at.exception
    at.text_area[0].set_value('怀ᴺo 怀旧o 瘤ᴼo 肿瘤o 堡ᶠᴿo 堡垒o 瘤ᴼ生ᴳa 肿瘤生ᴳa 瘤ᴼ学ᴸᴳo 肿瘤学ᴸᴳo 巧合o 讽刺o 精液o 精液ᶜ̂o')
    at.button[0].click().run();assert not at.exception
    assert at.text_area[1].value=='nostalgio nostalgio onko onko fortreso fortreso onkogena onkogena onkologio onkologio koincido satiro spermo ĉuro'
