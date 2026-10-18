"""Approved stafilokok shortening and non-ambiguous historical compatibility."""
import csv
import hashlib
import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter as app
from build_reverter_dictionary_from_all_json import rows_from_all_json

SOURCE=json.loads((app.ROOT/'data/current_dictionary_source.json').read_text(encoding='utf-8'))
REVIEW=json.loads((app.ROOT/'data/stafilokok-assignment-20261017.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('source',['pejvo-piv-20260620','legacy-minimal'])
def test_current_and_historical_spelling_are_the_same_root(source):
    index=app.build_mapping_index(app.load_dictionary_source(source))
    for body in ('葡球菌','葡萄球菌'):
        for ending in ('','o','oj','on','ojn','a','aj','an','ajn','e','i','igi','igxis'):
            for suffix in (ending,ending.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index)=='stafilokok'+ending
    assert app.convert_kanji_esperanto_to_alphabet('葡球菌o 葡萄球菌o',index)=='stafilokoko stafilokoko'

@pytest.mark.parametrize('source',['pre-las-20261017','pre-mirror-20261017'])
def test_explicit_historical_profiles_still_read_old_spelling(source):
    index=app.build_mapping_index(app.load_dictionary_source(source))
    assert app.convert_kanji_esperanto_to_alphabet('葡萄球菌OJ',index)=='stafilokokoj'

def test_one_new_reverse_alias_and_no_extra_forward_item():
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_text(encoding='utf-8'))
    items=[r for r in data['items'] if r['sourceRoot']=='stafilokok']
    assert len(items)==1 and items[0]['body']=='葡球菌'
    assert not [r for r in data['items'] if r['body']=='葡萄球菌']
    rows=rows_from_all_json(data)
    assert len(rows)==SOURCE['current_csv_count']==10678
    assert {(r['esperanto'],r['kanji']) for r in rows if r['kanji'] in ('葡球菌','葡萄球菌')}=={('stafilokok','葡球菌'),('stafilokok','葡萄球菌')}
    assert SOURCE['assignment_changes']['stafilokok']=={'old':'葡萄球菌','current':'葡球菌'}
    assert SOURCE['reverse_only_aliases']['葡萄球菌']=='stafilokok'
    assert hashlib.sha256((app.ROOT/'data/stafilokok-assignment-20261017.json').read_bytes()).hexdigest()==SOURCE['stafilokok_assignment_manifest_sha256']

def test_ambiguous_alias_is_rejected_and_old_custom_source_untouched():
    with pytest.raises(ValueError,match='conflicts with another root'):
        rows_from_all_json({'items':[{'sourceRoot':'stafilokok','body':'葡球菌'},{'sourceRoot':'other','body':'葡萄球菌'}]})
    old=rows_from_all_json({'items':[{'sourceRoot':'stafilokok','body':'葡萄球菌'}]})
    assert len(old)==1 and old[0]['kanji']=='葡萄球菌'

def test_ui_converts_new_and_old_forms_with_current_profile():
    at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run()
    assert not at.exception
    at.text_area[0].set_value('葡球菌o 葡萄球菌o');at.button[0].click().run()
    assert not at.exception and at.text_area[1].value=='stafilokoko stafilokoko'
