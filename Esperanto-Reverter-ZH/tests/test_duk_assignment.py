"""Ducal and baronial spellings, including the boundaries of their identifiers."""
from functools import lru_cache
import io

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
def test_peerage_spellings_and_neighbors(edition, ending):
    pairs = {
        "爵": "baron", "爵ᴰ": "duk", "公爵": "duk", "公": "publik", "公ᴶ": "just",
        "大爵ᴰ": "grandduk", "爵ᴰ国": "dukland", "爵士": "baronkavalir", "爵ᴰᴷ": "爵ᴰᴷ",
    }
    for key, root in pairs.items():
        assert app.convert_kanji_esperanto_to_alphabet(key + ending, mapping(edition)) == root + ending


@pytest.mark.parametrize("root,current,previous", [("duk", "爵ᴰ", "公爵")])
def test_alias_is_guarded(root, current, previous):
    def rows(*entries):
        return rows_from_all_json({"items": [{"sourceRoot": owner, "body": body} for owner, body in entries]})

    assert {r["kanji"] for r in rows((root, current))} == {current, previous}
    assert [r["kanji"] for r in rows((root, "custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts"):
        rows((root, current), ("another", previous))


def test_fixed_original_and_custom_dictionary_keep_their_own_entries():
    fixed_csv, _ = app.edition_download_data(LEGACY)
    effective_csv = app.legacy_effective_download_data(LEGACY)
    for content, expected in [(fixed_csv, "爵ᴰo"), (effective_csv, "duko")]:
        uploaded = app.read_assignment_csv(io.BytesIO(content))
        records = app.effective_mapping_records("custom", uploaded)
        index = app.build_mapping_index_cached(records)
        assert app.convert_kanji_esperanto_to_alphabet("爵ᴰo", index) == expected
        assert app.convert_kanji_esperanto_to_alphabet("爵o 公爵o", index) == "barono duko"
