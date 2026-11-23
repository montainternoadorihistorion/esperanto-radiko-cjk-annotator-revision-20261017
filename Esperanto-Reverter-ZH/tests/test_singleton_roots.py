"""A single independent root owns the unmarked display, including nested component IDs."""
from functools import lru_cache
import io

import pytest
import esperanto_converter_zh as app

CURRENT = "pejvo-piv-20260620"
LEGACY = "pre-las-20261017"
CHANGES = (
    ("otari", "海狮", "海狮ᴼ"), ("pakiderm", "厚皮", "厚皮ᴾᴷ"), ("polen", "花粉", "花粉ᴾᴸ"),
    ("hektar", "百亩", "百亩ᴴ"), ("tripanosom", "原兽", "原兽ᵀ"),
    ("deism", "神主义", "神主义ᴰ"), ("deist", "神家", "神家ᴰ"),
    ("dodekaedr", "十二面ᴱ", "十二面ᴱᴰ"), ("kseroftalmi", "干ᴷ目ᴼᶠ", "干ᴷ目ᴼᶠᴷ"),
    ("metapsiki", "超ᴹ心ᴾˢ", "超ᴹ心ᴾˢᴹ"), ("pedofili", "童ᴾ爱ᶠ", "童ᴾ爱ᶠᴾ"),
    ("polifoni", "多ᴾ声ᶠᴼ", "多ᴾ声ᶠᴼᴾ"), ("polipodi", "多ᴾ足ᴾᴼ", "多ᴾ足ᴾᴼᴾ"),
    ("polenolog", "花粉学家", "花粉ᴾᴸ学家"), ("polenologi", "花粉学ᴸᴳ", "花粉ᴾᴸ学ᴸᴳ"),
    ("polenoz", "花粉症ᴼ", "花粉ᴾᴸ症ᴼ"),
)


@lru_cache()
def index(edition):
    records = app.effective_mapping_records(edition, app.load_dictionary_source(edition))
    return app.build_mapping_index_cached(records)


@pytest.mark.parametrize("root,body,old", CHANGES)
def test_whole_root_owner_and_previous_complete_identifier(root, body, old):
    mapping = index(CURRENT)
    for suffix in ("", "o", "ojn", "a", "ajn", "e", "as", "is", "os", "us", "igi", "itan"):
        for spelling in (body, old):
            assert app.convert_kanji_esperanto_to_alphabet(spelling + suffix, mapping) == root + suffix
    assert root not in app.convert_kanji_esperanto_to_alphabet(old + "ᴸo", mapping)
    assert app.convert_kanji_esperanto_to_alphabet(old + "i", mapping) == root + "i"


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_actual_normal_and_localised_outputs_and_downloads(edition):
    expected = [
        ("干ᴷ目ᴼᶠiojn", "kseroftalmiojn"), ("童ᴾ爱ᶠio", "pedofilio"),
        ("多ᴾ声ᶠᴼian", "polifonian"), ("超ᴹ心ᴾˢio", "metapsikio"),
        ("多ᴾ足ᴾᴼio", "polipodio"), ("超ᴹ心ᴾˢi", "metapsiki"),
        ("多ᴾ足ᴾᴼi", "polipodi"), ("百ᴴ亩o", "hektoaro"), ("花粉ᴾo", "florpulvoro"),
        ("厚皮ᴾo", "dikpelto"), ("蛋奶o", "flano")
    ]
    if edition == CURRENT:
        expected.extend([("超ᴹ心ᴾˢiO", "metapsikio"), ("多ᴾ足ᴾᴼis", "polipodiis"),
                         ("花粉o学家o", "polenologo"), ("花粉o学ᴸᴳo", "polenologio"),
                         ("超ᴹ心ᴾˢo", "metapsikio"), ("多ᴾ足ᴾᴼo", "polipodio")])
    else:
        expected.extend([("花粉o", "florfaruno"), ("海狮o", "marleono"),
                         ("厚皮o", "dikhaŭto"), ("百亩o", "centaro")])
    exports = (app.current_effective_download_data if edition == CURRENT
               else app.legacy_effective_download_data)(edition)
    for mapping in (index(edition), app.build_mapping_index(app.read_assignment_csv(io.BytesIO(exports)))):
        for text, word in expected:
            assert app.convert_kanji_esperanto_to_alphabet(text, mapping) == word


def test_unrelated_custom_linking_i_keys_remain_literal():
    rows = app.read_assignment_csv(io.BytesIO(
        "esperanto,kanji,priority\nx,超ᴹ心ᴾˢ,0\ncustom,超ᴹ心ᴾˢi,0\n".encode()))
    mapping = app.build_mapping_index(rows)
    assert app.convert_kanji_esperanto_to_alphabet("超ᴹ心ᴾˢis", mapping) == "customs"

