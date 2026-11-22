"""Protect independent names and the existing readings of composed text."""
from functools import lru_cache
import io

import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = "pejvo-piv-20260620"
LEGACY = "pre-las-20261017"
CHANGES = (("unci", "豹ᵁ", "兽ᵁᶜ"), ("fenikopter", "火烈鸟ᶠᴱ", "鸟ᶠᴾ"))
PROTECTED = {
    "火烈鸟": "flameng",
    "雪豹": "neĝpanter",
    "雪豹ᴸ": "neĝleopard",
    "火烈鸟ᶠᴺ": "fajrintensfenikur",
    "豹": "panter",
    "豹ᴸ": "leopard",
    "鸟ᶠᴺ": "fenikur",
}


@lru_cache()
def index(edition):
    source = app.load_dictionary_source(edition)
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, source))


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_historical_and_current_spellings(edition):
    pairs = {**PROTECTED, **{old: root for root, _, old in CHANGES}}
    if edition == CURRENT:
        pairs.update({new: root for root, new, _ in CHANGES})
    for body, root in pairs.items():
        for ending in ("", "o", "ojn", "a", "ajn", "e", "i", "as", "is", "os", "us", "u", "ante", "ito"):
            assert app.convert_kanji_esperanto_to_alphabet(body + ending, index(edition)) == root + ending


@pytest.mark.parametrize("root,new,old", CHANGES)
def test_aliases_require_the_new_source_assignment(root, new, old):
    def rows(*pairs):
        return rows_from_all_json({"items": [{"sourceRoot": r, "body": key} for r, key in pairs]})

    assert {r["kanji"] for r in rows((root, new))} == {old, new}
    assert [r["kanji"] for r in rows((root, "custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts"):
        rows((root, new), ("other", old))


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_downloaded_dictionaries_and_longer_identifiers(edition):
    keys = {"兽ᵁᶜo": "uncio", "鸟ᶠᴾo": "fenikoptero", "火烈鸟o": "flamengo",
            "雪豹o": "neĝpantero", "雪豹ᴸo": "neĝleopardo"}
    if edition == CURRENT:
        keys.update({"豹ᵁo": "uncio", "火烈鸟ᶠᴱo": "fenikoptero"})
    for payload in app.edition_download_data(edition):
        downloaded = app.build_mapping_index(app.read_assignment_csv(io.BytesIO(payload)))
        assert app.convert_kanji_esperanto_to_alphabet(" ".join(keys), downloaded) == " ".join(keys.values())
        for text in ("兽ᵁᶜᴷo", "鸟ᶠᴾᴷo", "豹ᵁᴷo", "火烈鸟ᶠᴱᴷo"):
            result = app.convert_kanji_esperanto_to_alphabet(text, downloaded)
            assert "unci" not in result and "fenikopter" not in result

