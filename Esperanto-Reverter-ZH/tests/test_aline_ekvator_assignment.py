"""Paragraph and equator spellings in current, historical and custom dictionaries."""
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
@pytest.mark.parametrize("ending", ["", "o", "on", "oj", "ojn", "a", "aj", "ajn", "as", "is", "os", "e", "i"])
def test_editions_and_previous_spellings(edition, ending):
    roots = {
        "换行": "aline", "赤": "ekvator", "赤褐": "ruf", "段": "etap",
        "段ᴱᴾ": "epizod", "段ˢ": "segment", "段ᴹ": "metamer",
        "赤道": "ekvator" if edition == CURRENT else "ekvatoravenu",
        "段ᴬ": "aline" if edition == CURRENT else "段ᴬ",
        "段ᴬᴿ": "段ᴬᴿ", "段ᴱᴾᴹ": "段ᴱᴾᴹ",
    }
    for spelling, root in roots.items():
        assert app.convert_kanji_esperanto_to_alphabet(spelling + ending, mapping(edition)) == root + ending

def test_derived_word_and_phrase():
    assert app.convert_kanji_esperanto_to_alphabet("段ᴬ物o 赤道a", mapping(CURRENT)) == "alineaĵo ekvatora"
    assert app.convert_kanji_esperanto_to_alphabet("换行物o 赤a", mapping(LEGACY)) == "alineaĵo ekvatora"

@pytest.mark.parametrize("root,current,old", [("aline","段ᴬ","换行"), ("ekvator","赤道","赤")])
def test_historical_alias_requires_corresponding_assignment(root, current, old):
    def rows(*items):
        return rows_from_all_json({"items": [{"sourceRoot": owner, "body": key} for owner, key in items]})
    assert {r["kanji"] for r in rows((root, current))} == {current, old}
    assert [r["kanji"] for r in rows((root, "custom"))] == ["custom"]
    with pytest.raises(ValueError, match="conflicts"):
        rows((root, current), ("another", old))

def test_custom_input_uses_its_own_mapping():
    df = pd.DataFrame([("custom","赤道","0"), ("other","段ᴬ","0")], columns=["esperanto","kanji","priority"])
    idx = app.build_mapping_index_cached(app.effective_mapping_records("custom",df))
    assert app.convert_kanji_esperanto_to_alphabet("赤道o 段ᴬo 赤 换行", idx) == "customo othero 赤 换行"

