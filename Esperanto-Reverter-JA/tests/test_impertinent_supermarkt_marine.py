"""Unmarked independent roots, sea cow co-owners, and the frozen legacy readings."""
import io
from functools import lru_cache

import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = "pejvo-piv-20260620"
LEGACY = "pre-las-20261017"
CHANGES = (
    ("impertinent", "无礼", "放肆"), ("supermarkt", "超市", "市ˢ"),
    ("manat", "海牛", "兽ᴹᴬ"), ("dugong", "海牛ᴰ", "兽ᴰᴳ"), ("rosmar", "海象", "海豹ᴿ"),
)
GUARDS = {"无礼ᴳ̂": "senĝentil", "超市ᴹ": "hipermerkat", "超市ˢ": "hipersupermarkt",
          "海豹": "fok", "海豹ᴸ": "marleopard", "市": "urb", "木ᴳᴷ": "gink"}
LEGACY_COMPOUNDS = {"无礼": "sendonac", "超市": "hiperurb", "海牛": "marbov", "海象": "marelefant"}


@lru_cache()
def index(edition):
    return app.build_mapping_index_cached(
        app.effective_mapping_records(edition, app.load_dictionary_source(edition)))


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_complete_owners_historical_writings_and_compounds(edition):
    mapping = index(edition)
    expected = GUARDS | {old: root for root, _, old in CHANGES}
    if edition == CURRENT:
        expected.update({new: root for root, new, _ in CHANGES})
    else:
        expected.update(LEGACY_COMPOUNDS)
    for body, root in expected.items():
        for suffix in ("", "o", "ojn", "a", "ajn", "i", "as", "is", "OS", "ita", "ulo", "igi"):
            assert app.convert_kanji_esperanto_to_alphabet(body + suffix, mapping) == root + suffix.lower()
    assert "dugong" not in app.convert_kanji_esperanto_to_alphabet("海牛ᴰᴿo", mapping)
    assert "rosmar" not in app.convert_kanji_esperanto_to_alphabet("海象ᴱo", mapping)


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_readings_survive_export_and_import(edition):
    full, snippet = app.edition_download_data(edition)
    effective = (app.current_effective_download_data if edition == CURRENT
                 else app.legacy_effective_download_data)(edition)
    text = "无礼a 超市o 海牛o 海牛ᴰo 海象o 放肆a 市ˢo 兽ᴹᴬo 兽ᴰᴳo 海豹ᴿo"
    expected = app.convert_kanji_esperanto_to_alphabet(text, index(edition))
    for payload in (full, snippet, effective):
        imported = app.build_mapping_index(app.read_assignment_csv(io.BytesIO(payload)))
        assert app.convert_kanji_esperanto_to_alphabet(text, imported) == expected


@pytest.mark.parametrize("root,body,old", CHANGES)
def test_previous_form_is_reserved_only_when_current_owner_matches(root, body, old):
    def rows(*pairs):
        return rows_from_all_json({"items": [{"sourceRoot": r, "body": k} for r, k in pairs]})

    assert {row["kanji"] for row in rows((root, body))} == {body, old}
    assert [row["kanji"] for row in rows((root, "custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts with another root"):
        rows((root, body), ("other", old))

