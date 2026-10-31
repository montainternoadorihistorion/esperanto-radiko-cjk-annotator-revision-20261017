"""User-approved tril/sfinks/alcion and generated alced identifier and unchanged neighbouring decompositions."""
import csv
import hashlib
import io
import json

import pandas as pd
import pytest
import esperanto_converter_zh as app

CURRENT = "pejvo-piv-20260620"
OLD = "pre-las-20261017"
CHANGES = {
    "tril": ("颤歌", "颤音"),
    "sfinks": ("狮面", "人面狮"),
    "alcion": ("翠鸟", "鸟ᴬᴸ"),
    "alced": ("鸟ᴬᴸ", "鸟ᴬᴰ"),
}
CONTROLS = {"石笔": "grifel", "勇ᴮ": "brav", "轻浮": "frivol", "兽ᴬ": "animal", "鸟ᴬᴮ": "albatros"}
LEGACY = {root: old for root, (old, new) in CHANGES.items()}
LEGACY_CONTROLS = CONTROLS
SUFFIXES = ("", "o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "i", "as", "is", "os", "us", "u", "ado", "ita", "intajn", "igi", "ĉjo")

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source, app.load_dictionary_source(source)))

@pytest.mark.parametrize("source", (CURRENT, OLD))
def test_adopted_families_endings_and_neighbouring_decompositions(source):
    mapping = index(source)
    for root, values in CHANGES.items():
        body = values[1] if source == CURRENT else LEGACY[root]
        for suffix in SUFFIXES:
            for ending in (suffix, suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body + ending, mapping) == root + suffix
    for body, root in (CONTROLS if source == CURRENT else LEGACY_CONTROLS).items():
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(body + suffix, mapping) == root + suffix

def test_full_internal_identifiers_and_no_long_identifier_prefix_consumption():
    mapping = index(CURRENT)
    for root, (_, body) in CHANGES.items():
        for extra in ("ᴮ", "ᴿ", "ᴬᶜ", "\u0302", "\u0306"):
            text = body + extra + "o"
            assert app.convert_kanji_esperanto_to_alphabet(text, mapping) != root + extra + "o"
    # Bird identifiers share a prefix: matching must consume the complete ID.
    for text in ("鸟ᴬᴸᴰo", "鸟ᴬᴰᴸo", "鸟ᴬᴸ\u0302o", "鸟ᴬᴰ\u0306o"):
        actual = app.convert_kanji_esperanto_to_alphabet(text, mapping)
        assert not actual.startswith(("alcion", "alced")), (text, actual)

@pytest.mark.parametrize("source, expected", ((CURRENT, "alcion"), (OLD, "alced")))
def test_bird_identifier_owner_is_selected_by_edition_without_stale_alias(source, expected):
    mapping = index(source)
    assert app.convert_kanji_esperanto_to_alphabet("鸟ᴬᴸo 鸟ᴬᴸa 鸟ᴬᴸis", mapping) == f"{expected}o {expected}a {expected}is"
    records = app.effective_mapping_records(source, app.load_dictionary_source(source))
    exact = [row for row in records if row[1] == "鸟ᴬᴸ"]
    assert exact and {row[0] for row in exact} == {expected}
    if source == CURRENT:
        provenance = json.loads((app.ROOT / "data/current_dictionary_source.json").read_bytes())
        assert "鸟ᴬᴸ" not in provenance["reverse_only_aliases"]
        assert "鸟ᴬᴸ" not in app.CURRENT_INVERSE_ALIAS_PAIRS
        assert app.convert_kanji_esperanto_to_alphabet("鸟ᴬᴰo", mapping) == "alcedo"


def test_current_manifest_download_and_fixed_legacy():
    assert app.dictionary_options() == [CURRENT, OLD]
    assert len(app.DICTIONARY_SOURCES) == 8
    source = json.loads((app.ROOT / "data/current_dictionary_source.json").read_bytes())
    manifest_path = app.ROOT / source["tril_sfinks_alcion_manifest"]
    manifest = json.loads(manifest_path.read_bytes())
    assert source["revision"] == "2026-11-01-adopted"
    assert manifest["revision"] == "2026-10-21-tril-sfinks-alcion"
    assert manifest["changes"] == {k: list(v) for k, v in CHANGES.items()}
    assert manifest["safe_reverse_aliases"] == {}
    assert manifest["ownership_transfers"] == {"鸟ᴬᴸ": {"old": "alced", "current": "alcion", "old_profile": OLD}}
    assert manifest["current_item_count"] == manifest["baseline_item_count"] == 10640
    assert manifest["unrelated_items_count"] == 10636
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == source["tril_sfinks_alcion_manifest_sha256"]
    rows = list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding="utf-8"))))
    assert len(rows) == 10678
    for root, (old, new) in CHANGES.items():
        assert [r["kanji"] for r in rows if r["esperanto"] == root] == [new]
        if old not in {v[1] for v in CHANGES.values()}:
            assert old not in {r["kanji"] for r in rows}
    full, two = app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest() == source["current_csv_sha256"]
    assert hashlib.sha256(two).hexdigest() == source["current_snippet_csv_sha256"]
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full))) == app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy_raw, legacy_two = app.edition_download_data(OLD)
    assert hashlib.sha256(legacy_raw).hexdigest() == app.EDITION_POLICY["fixed_csv_sha256"]
    assert hashlib.sha256(legacy_two).hexdigest() == app.EDITION_POLICY["fixed_two_column_sha256"]
    supplement = json.loads((app.ROOT / "data/current_inverse_aliases.json").read_bytes())
    assert len(supplement["aliases"]) == 9
    assert {r["kanji"]: r["esperanto"] for r in supplement["aliases"]} == app.CURRENT_INVERSE_ALIAS_PAIRS

def test_user_csv_not_reassigned():
    for _, body in CHANGES.values():
        frame = pd.DataFrame([("custom", body, "0")], columns=["esperanto", "kanji", "priority"])
        records = app.effective_mapping_records("custom", frame)
        assert records == app.dataframe_to_mapping_records(frame)
        assert app.convert_kanji_esperanto_to_alphabet(body + "o", app.build_mapping_index_cached(records)) == "customo"
