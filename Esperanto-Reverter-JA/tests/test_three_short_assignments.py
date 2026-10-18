"""Three shortened assignments and an explicitly selected pre-change dictionary."""
import hashlib,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app
from build_reverter_dictionary_from_all_json import rows_from_all_json

CHANGES={'risort':('弹簧','簧'),'anc^':('簧','簧ᴬ'),'lantern':('灯笼','灯ᴸᴺ'),'lubrik':('润滑','滑ᴸ')}
CONTROLS={'pland':'足底','lamp':'灯','lucern':'灯ᴸᶜ','glit':'滑','glat':'滑ᴳᴬ','observatori':'观台',
 'majest':'庄严','subtil':'精细','uve':'葡膜','uveit':'葡膜炎ᵀ','testikit':'丸ᵀ炎ᵀ','orkidit':'丸ᴼ炎ᵀ',
 'turment':'虐','tortur':'虐ᵀᵀ','las':'放','emancip':'放ᴱ','uv':'葡ᵁ'}
PROFILE='pre-three-short-20261017'
def index(source):return app.build_mapping_index(app.load_dictionary_source(source))
def root_text(root):return 'anĉ' if root=='anc^' else root

@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_current_assignments_all_inflections_and_controls(source):
    mapping=index(source)
    for root,(old,new) in CHANGES.items():
        bodies=[new] if root=='anc^' else [old,new]
        for body in bodies:
            for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','as','ita','igi','igxis'):
                for suffix in (ending,ending.upper()):
                    assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root_text(root)+ending
    for root,body in CONTROLS.items():
        assert app.convert_kanji_esperanto_to_alphabet(body+'OJ',mapping)==root+'oj'

@pytest.mark.parametrize('root',['risort','lantern','lubrik'])
def test_safe_alias_collision_refused_and_old_custom_source_preserved(root):
    old,new=CHANGES[root]
    with pytest.raises(ValueError,match='conflicts with another root'):
        rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old}]})
    rows=rows_from_all_json({'items':[{'sourceRoot':root,'body':old}]})
    assert len(rows)==1 and rows[0]['kanji']==old

def test_bare_huang_is_not_a_current_alias_for_anc():
    data={'items':[{'sourceRoot':'risort','body':'簧'},{'sourceRoot':'anc^','body':'簧ᴬ'}]}
    rows=rows_from_all_json(data)
    assert {(r['kanji'],r['esperanto']) for r in rows}=={('簧','risort'),('簧ᴬ','anĉ'),('弹簧','risort')}
    now=index('pejvo-piv-20260620');old=index(PROFILE)
    assert app.convert_kanji_esperanto_to_alphabet('簧o 簧ᴬo 弹簧o',now)=='risorto anĉo risorto'
    assert app.convert_kanji_esperanto_to_alphabet('簧o 弹簧o 灯笼o 润滑i',old)=='anĉo risorto lanterno lubriki'

def test_manifest_snapshot_and_current_forward_candidates():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
    assert len(data['items'])==source['current_item_count']==10640
    rows=rows_from_all_json(data);assert len(rows)==source['current_csv_count']==10678
    for root,(old,new) in CHANGES.items():
        assert [r['body'] for r in data['items'] if r['sourceRoot']==root]==[new]
        assert source['assignment_changes'][root]=={'old':old,'current':new}
    assert '簧' not in source['reverse_only_aliases']
    assert hashlib.sha256((app.ROOT/'data/three-short-assignments-20261017.json').read_bytes()).hexdigest()==source['three_short_assignment_manifest_sha256']
    profile=source['pre_three_short_profile'];assert profile['id']==PROFILE
    for field in ('csv','snippet_csv'):
        assert hashlib.sha256((app.ROOT/profile[field]).read_bytes()).hexdigest()==profile[field+'_sha256']
    assert index(PROFILE)==app.build_mapping_index(app.read_assignment_csv(app.PRE_THREE_SHORT_SNIPPET_20261017_CSV))
    assert app.DICTIONARY_SOURCES[PROFILE]['path']==app.PRE_THREE_SHORT_20261017_CSV

def test_archived_profile_remains_available_but_is_not_a_visible_edition():
    assert 'pre-three-short-20261017' in app.DICTIONARY_SOURCES
    assert 'pre-three-short-20261017' not in app.dictionary_options()
    mapping=app.build_mapping_index(app.load_dictionary_source('pre-three-short-20261017'))
    assert app.convert_kanji_esperanto_to_alphabet('簧o 弹簧o',mapping)=='anĉo risorto'
