"""Reviewed fruit/priority mappings, old spellings, and neighbouring roots."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import esperanto_converter_zh as app
from build_reverter_dictionary_from_all_json import rows_from_all_json


@pytest.mark.parametrize("source_id", ["pejvo-piv-20260620", "legacy-minimal"])
def test_current_and_historical_fruit_forms_with_longest_match(source_id):
    index = app.build_mapping_index(app.load_dictionary_source(source_id))
    for root, bodies in {"ananas": ["菠", "菠萝"], "jakv": ["菠蜜", "菠萝蜜"], "prioritat": ["优先"]}.items():
        for body in bodies:
            for ending in ("", "o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "i", "igi", "igxis"):
                for suffix in (ending, ending.upper()):
                    assert app.convert_kanji_esperanto_to_alphabet(body + suffix, index) == root + ending
    controls = {
        "菠菜o": "spinaco", "胡萝卜o": "karoto", "萝卜o": "rafano", "萝卜ᴿᴾo": "rapo",
        "萝卜素o": "karoteno", "蜜o": "mielo", "蜜ᴺo": "nektaro", "糖蜜o": "melaso",
        "优a 先a": "avantaĝa apriora", "优a先a": "avantaĝaapriora", "优 先": "avantaĝ aprior",
        "优ᴱo 优ᴼo 优生o": "elito optimumo eŭgeniko", "院长ᴾo": "prioro",
        "先知o 先例o 先例ᴾᵀo": "profeto precedenco precedento",
        "放i 放ᴱo": "lasi emancipo", "菠蜜o 菠o 蜜o": "jakvo ananaso mielo",
    }
    for text, expected in controls.items():
        assert app.convert_kanji_esperanto_to_alphabet(text, index) == expected


def test_reverse_aliases_do_not_change_historical_or_custom_generation():
    assert [r["kanji"] for r in rows_from_all_json({"items": [{"sourceRoot": "ananas", "body": "菠萝"}]})] == ["菠萝"]
    assert [r["kanji"] for r in rows_from_all_json({"items": [{"sourceRoot": "other", "body": "菠"}]})] == ["菠"]
    with pytest.raises(ValueError, match="conflicts with another root"):
        rows_from_all_json({"items": [{"sourceRoot": "ananas", "body": "菠"}, {"sourceRoot": "other", "body": "菠萝"}]})


def test_all_dictionary_menu_choices_convert_with_the_selected_profile():
    at = AppTest.from_file(str(Path(app.__file__)), default_timeout=20).run()
    for source_id in ("pejvo-piv-20260620", "pre-las-20261017", "pejvo-piv-20260620"):
        at.sidebar.selectbox[0].set_value(source_id).run()
        at.text_area[0].set_value("菠萝O 菠萝蜜ON 菠O 菠蜜O 优先O 优A 先A 留IS 放IS 放ᴱIS")
        at.button[0].click().run()
        assert not at.exception
        if source_id == "pre-las-20261017":
            assert at.text_area[1].value == "ananaso jakvon 菠o 菠mielo avantaĝaprioro avantaĝa apriora lasis emancipis 放ᴱis"
        else:
            assert at.text_area[1].value == "ananaso jakvon ananaso jakvo prioritato avantaĝa apriora 留is lasis emancipis"
