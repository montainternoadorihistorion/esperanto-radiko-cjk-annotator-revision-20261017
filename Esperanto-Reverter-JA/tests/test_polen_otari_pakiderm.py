"""Keep the independent pollen, sea lion and pachyderm readings distinct from compounds."""
from functools import lru_cache
import io

import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = "pejvo-piv-20260620"
LEGACY = "pre-las-20261017"
CHANGES = (
    ("polen", "花粉ᴾᴸ", "粉ᴾᴺ"),
    ("otari", "海狮ᴼ", "兽ᴼ"),
    ("pakiderm", "厚皮ᴾᴷ", "兽ᴾᴷ"),
    ("polenolog", "花粉ᴾᴸ学家", "粉ᴾᴺ学家"),
    ("polenologi", "花粉ᴾᴸ学ᴸᴳ", "粉ᴾᴺ学ᴸᴳ"),
    ("polenoz", "花粉ᴾᴸ症ᴼ", "粉ᴾᴺ症ᴼ"),
)
PROTECTED = {
    "花粉": "florfarun", "花粉ᴾ": "florpulvor", "花粉ᴾᴰ": "florpudr", "花粉ᴾᴺ": "florpolen",
    "海狮": "marleon", "厚皮": "dikhaŭt", "厚皮ᴾ": "dikpelt", "厚皮者": "dikhaŭtul",
    "粉ᴾᴺo学家": "polenolog", "粉ᴾᴺo学ᴸᴳ": "polenologi",
}
ENDINGS = ("", "o", "ojn", "a", "ajn", "e", "i", "as", "is", "os", "us", "u", "ante", "ito")


@lru_cache()
def index(edition):
    source = app.load_dictionary_source(edition)
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, source))


def historical(edition):
    pairs = {old: root for root, _, old in CHANGES}
    if edition == LEGACY:
        # Raw concatenation without the linking o has a different reading in the fixed dictionary.
        pairs.update({"粉ᴾᴺ学家": "polenlog", "粉ᴾᴺ学ᴸᴳ": "polenlogi"})
    return pairs


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_original_readings_and_compounds(edition):
    pairs = {**PROTECTED, **historical(edition)}
    if edition == CURRENT:
        pairs.update({new: root for root, new, _ in CHANGES})
        pairs.update({"花粉ᴾᴸo学家": "polenolog", "花粉ᴾᴸo学ᴸᴳ": "polenologi"})
    for body, root in pairs.items():
        for ending in ENDINGS:
            assert app.convert_kanji_esperanto_to_alphabet(body + ending, index(edition)) == root + ending


@pytest.mark.parametrize("root,new,old", CHANGES)
def test_only_the_selected_current_assignments_get_historical_aliases(root, new, old):
    def rows(*pairs):
        return rows_from_all_json({"items": [{"sourceRoot": r, "body": k} for r, k in pairs]})

    assert {row["kanji"] for row in rows((root, new))} == {new, old}
    assert [row["kanji"] for row in rows((root, "custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts"):
        rows((root, new), ("other", old))


@pytest.mark.parametrize("edition", [CURRENT, LEGACY])
def test_downloaded_readings_and_identifier_boundaries(edition):
    pairs = {**PROTECTED, **historical(edition)}
    if edition == CURRENT:
        pairs.update({new: root for root, new, _ in CHANGES})
    for payload in app.edition_download_data(edition):
        downloaded = app.build_mapping_index(app.read_assignment_csv(io.BytesIO(payload)))
        for key, root in pairs.items():
            assert app.convert_kanji_esperanto_to_alphabet(key + "o", downloaded) == root + "o"
        for root, key in (("polen", "花粉ᴾᴸ"), ("otari", "海狮ᴼ"), ("pakiderm", "厚皮ᴾᴷ")):
            assert root not in app.convert_kanji_esperanto_to_alphabet(key + "ᴸo", downloaded)

