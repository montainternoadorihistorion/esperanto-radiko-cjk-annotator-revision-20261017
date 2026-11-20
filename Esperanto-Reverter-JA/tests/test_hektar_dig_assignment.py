from functools import lru_cache
import io

import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json

CURRENT = "pejvo-piv-20260620"
LEGACY = "pre-las-20261017"
OLD_KEYS = {"拦": "dig", "公顷": "hektar", "兽ᴵ": "izatis", "木ᴹᵁ": "mug", "木ᴷᴸᴱ": "klementin"}
NEW_KEYS = {"堤": "dig", "堤ᴳ̂": "ĝet", "百亩ᴴ": "hektar", "松ᴹ": "mug", "狐ᴵ": "izatis", "橘ᴷ": "klementin"}
NEIGHBORS = {
    "堤ᴹ": "mole", "松": "pin", "狐": "vulp", "橘": "mandarin",
    "木ᴷᴸᴱᴿ": "klerodendr", "木ᴷᴬᴸ": "kalitris", "木ᴷᴬᴸᴬ": "kalam",
    "百亩": "centar", "百ᴴ亩": "hektoar", "蛋奶": "flan", "果o蛋奶": "fruktoflan",
}

@lru_cache(maxsize=None)
def index(edition):
    source = app.load_dictionary_source(edition)
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, source))

@pytest.mark.parametrize("ending", ["", "o", "on", "oj", "ojn", "a", "an", "aj", "ajn", "e", "i", "as", "is", "os", "u", "us", "anta", "ita"])
@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_roots_endings_and_historical_readings(edition, ending):
    pairs = {**OLD_KEYS, **NEIGHBORS}
    if edition == CURRENT:
        pairs.update(NEW_KEYS)
        pairs["果o饼ᶠ"] = "fruktoflan"
    else:
        pairs["堤"] = "ĝet"
    for key, owner in pairs.items():
        assert app.convert_kanji_esperanto_to_alphabet(key + ending, index(edition)) == owner + ending

@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_longer_identifiers_are_not_consumed(edition):
    for text in ("堤ᴳ̂ᴷo", "狐ᴵᴷo", "松ᴹᴷo", "橘ᴷᴷo"):
        assert app.convert_kanji_esperanto_to_alphabet(text, index(edition)) == text
    value = app.convert_kanji_esperanto_to_alphabet("百亩ᴴᴷo", index(edition))
    assert value.endswith("亩ᴴᴷo")

@pytest.mark.parametrize("root,current,old", [
    ("dig","堤","拦"), ("mug","松ᴹ","木ᴹᵁ"), ("hektar","百亩ᴴ","公顷"),
    ("izatis","狐ᴵ","兽ᴵ"), ("klementin","橘ᴷ","木ᴷᴸᴱ"),
])
def test_previous_key_only_with_matching_assignment(root,current,old):
    def rows(*pairs):
        return rows_from_all_json({"items":[{"sourceRoot":r, "body":k} for r,k in pairs]})
    assert {row["kanji"] for row in rows((root,current))} == {current,old}
    assert [row["kanji"] for row in rows((root,"custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts"):
        rows((root,current),("another",old))

def test_download_and_custom_dictionary():
    for edition in (CURRENT,LEGACY):
        exported = app.edition_download_data(edition)[0]
        imported = app.read_assignment_csv(io.BytesIO(exported))
        mapping = app.build_mapping_index_cached(app.effective_mapping_records("custom",imported))
        expected = "digo" if edition == CURRENT else "ĝeto"
        assert app.convert_kanji_esperanto_to_alphabet("堤o",mapping) == expected
        assert app.convert_kanji_esperanto_to_alphabet("公顷o 蛋奶o",mapping) == "hektaro flano"

