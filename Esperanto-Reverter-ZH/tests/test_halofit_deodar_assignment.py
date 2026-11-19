"""Whole and historical plant spellings, including the boundaries of their identifiers."""
from functools import lru_cache

import pandas as pd
import pytest

import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json

CURRENT = "pejvo-piv-20260620"
LEGACY = "pre-las-20261017"


@lru_cache(maxsize=None)
def mapping(edition):
    source = app.load_dictionary_source(edition)
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, source))


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
@pytest.mark.parametrize("ending", ["", "o", "on", "oj", "ojn", "a", "an", "aj", "ajn", "as", "is", "os", "us", "u", "e", "i", "anta", "ita", "ulo"])
def test_plant_spellings_and_neighbors(edition, ending):
    pairs = {
        "盐ᴴ植ᶠ": "halofit", "雪松ᴰ": "deodar" if edition == CURRENT else "neĝ松ᴰ",
        "草ᴴᶠ": "halofit", "木ᴰᴰ": "deodar", "雪松": "cedr", "盐植": "salplant",
        "盐ᴴ": "halo", "植ᶠ": "fit", "公爵": "duk", "柴": "alumet", "自ᴬ主义": "aŭtism",
        "雪松ᴰᴷ": "neĝ松ᴰᴷ", "盐ᴴ植ᶠᴷ": "halo植ᶠᴷ",
        "木ᴰᴰᴷ": "木ᴰᴰᴷ", "草ᴴᶠᴷ": "草ᴴᶠᴷ",
    }
    for key, root in pairs.items():
        assert app.convert_kanji_esperanto_to_alphabet(key + ending, mapping(edition)) == root + ending


@pytest.mark.parametrize("root,current,previous", [("halofit", "盐ᴴ植ᶠ", "草ᴴᶠ"), ("deodar", "雪松ᴰ", "木ᴰᴰ")])
def test_alias_is_guarded(root, current, previous):
    def rows(*entries):
        return rows_from_all_json({"items": [{"sourceRoot": owner, "body": body} for owner, body in entries]})

    assert {r["kanji"] for r in rows((root, current))} == {current, previous}
    assert [r["kanji"] for r in rows((root, "custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts"):
        rows((root, current), ("another", previous))


def test_custom_csv_keeps_its_owners():
    df = pd.DataFrame([("custom", "盐ᴴ植ᶠ", "0"), ("other", "雪松ᴰ", "0")], columns=["esperanto", "kanji", "priority"])
    index = app.build_mapping_index_cached(app.effective_mapping_records("custom", df))
    assert app.convert_kanji_esperanto_to_alphabet("盐ᴴ植ᶠo 雪松ᴰo 木ᴰᴰ 草ᴴᶠ", index) == "customo othero 木ᴰᴰ 草ᴴᶠ"
