from functools import lru_cache
import io

import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = "pejvo-piv-20260620"
LEGACY = "pre-las-20261017"
ASSIGNMENTS = (
    ("korsak", "狐ᴷ", "兽ᴷˢ"),
    ("hematit", "赤铁矿", "矿ᴴ"),
    ("kolokazi", "芋", "草ᴷᶻ"),
    ("kolokasi", "芋ᴷˢ", "草ᴷᴼᴸ"),
    ("orcin", "虎鲸ᴼᶜ", "兽ᴼᴿ"),
    ("grosulari", "醋栗ᴳᴸ", "木ᴳˢ"),
)
NEIGHBORS = {"兽ᴷᵀ": "kironekt", "兽ᴼᵀ": "orikterop", "草ᴷᶠ": "krozofor",
             "狐": "vulp", "赤": "ekvator", "铁": "fer", "矿": "min", "虎": "tigr", "醋": "acet"}


@lru_cache()
def index(edition):
    source = app.load_dictionary_source(edition)
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, source))


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
@pytest.mark.parametrize("ending", ["", "o", "on", "oj", "ojn", "a", "aj", "ajn", "e", "i", "as", "is", "os", "u", "us", "anta", "ita"])
def test_readings(edition, ending):
    pairs = {**NEIGHBORS, **{old: root for root, _, old in ASSIGNMENTS}}
    if edition == CURRENT:
        pairs.update({new: root for root, new, _ in ASSIGNMENTS})
        pairs.update({"狐ᴵ": "izatis", "虎鲸": "ork", "醋栗": "rib", "醋栗ᴳ": "gros"})
    for key, root in pairs.items():
        assert app.convert_kanji_esperanto_to_alphabet(key + ending, index(edition)) == root + ending


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_compound_and_identifier_boundaries(edition):
    read = lambda text: app.convert_kanji_esperanto_to_alphabet(text, index(edition))
    assert read("木ᴳˢ科ᴬoj") == "grosulariacoj"
    if edition == CURRENT:
        assert read("醋栗ᴳᴸ科ᴬoj") == "grosulariacoj"
        assert read("芋o芋ᴷˢo") == "kolokaziokolokasio"
    for text in ("芋ᴷo", "芋ᴷˢᴷo", "狐ᴷᴷo", "兽ᴷˢᴷo", "草ᴷᶻᴷo"):
        assert read(text) == text


@pytest.mark.parametrize("root,new,old", ASSIGNMENTS)
def test_source_conditional_historical_alias(root, new, old):
    def rows(*pairs):
        items = [{"sourceRoot": owner, "body": key} for owner, key in pairs]
        return rows_from_all_json({"items": items})

    assert {r["kanji"] for r in rows((root, new))} == {new, old}
    assert [r["kanji"] for r in rows((root, "custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts"):
        rows((root, new), ("another", old))


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_downloaded_dictionary_recovers_historical_compound(edition):
    full, snippet = app.edition_download_data(edition)
    for data in (full, snippet):
        uploaded = app.build_mapping_index(app.read_assignment_csv(io.BytesIO(data)))
        text = "木ᴳˢ科ᴬoj 草ᴷᶻo 草ᴷᴼᴸo 兽ᴼᴿo"
        assert app.convert_kanji_esperanto_to_alphabet(text, uploaded) == "grosulariacoj kolokazio kolokasio orcino"
        if edition == CURRENT:
            assert app.convert_kanji_esperanto_to_alphabet("芋o 芋ᴷˢo 醋栗ᴳᴸ科ᴬoj", uploaded) == "kolokazio kolokasio grosulariacoj"

