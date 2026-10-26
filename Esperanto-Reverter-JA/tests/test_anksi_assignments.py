"""Approved anksi shared-忧 assignment; fixed legacy and complete ID matching."""
import csv
import hashlib
import io
import json

import pandas as pd
import pytest
import esperanto_converter as app

CURRENT = "pejvo-piv-20260620"
OLD = "pre-las-20261017"
SUFFIXES = ("", "o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "i", "as", "is", "os", "us", "u", "ado", "ita", "intajn", "igi", "ĉjo")
CONTROLS = {"忧": "angor", "虑": "konsider", "水渠": "irigaci", "串联": "tandem"}

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source, app.load_dictionary_source(source)))

@pytest.mark.parametrize("source, body", ((CURRENT, "忧ᴬᴷ"), (OLD, "忧虑")))
def test_anksi_endings_and_preserved_owners(source, body):
    mapping = index(source)
    for suffix in SUFFIXES:
        for ending in (suffix, suffix.upper()):
            assert app.convert_kanji_esperanto_to_alphabet(body + ending, mapping) == "anksi" + suffix
        for control, root in CONTROLS.items():
            assert app.convert_kanji_esperanto_to_alphabet(control + suffix, mapping) == root + suffix

@pytest.mark.parametrize("source", (CURRENT, OLD))
def test_complete_identifier_boundaries(source):
    mapping = index(source)
    for text in ("忧ᴬᴷᴮo", "忧ᴬᴷᴿo", "忧ᴬᴷᴬᶜo", "忧ᴬᴷ\u0302o", "忧ᴬᴷ\u0306o", "忧ᴬo"):
        actual = app.convert_kanji_esperanto_to_alphabet(text, mapping)
        assert not actual.startswith(("anksi", "angor")), (text, actual)
    assert app.convert_kanji_esperanto_to_alphabet("忧o", mapping) == "angoro"

def test_old_text_uses_fixed_old_edition_without_intermediate_alias():
    current = index(CURRENT)
    assert app.convert_kanji_esperanto_to_alphabet("忧虑o", index(OLD)) == "anksio"
    assert app.convert_kanji_esperanto_to_alphabet("忧ᴬᴷo", current) == "anksio"
    records = app.effective_mapping_records(CURRENT, app.load_dictionary_source(CURRENT))
    assert {r[0] for r in records if r[1] == "忧ᴬᴷ"} == {"anksi"}
    assert {r[0] for r in records if r[1] == "忧"} == {"angor"}
    assert not [r for r in records if r[1] == "忧虑"]
    source = json.loads((app.ROOT / "data/current_dictionary_source.json").read_bytes())
    assert not {"忧虑", "忧ᴬᴷ"} & set(source["reverse_only_aliases"])
    assert not {"忧虑", "忧ᴬᴷ"} & set(app.CURRENT_INVERSE_ALIAS_PAIRS)

def test_current_manifest_downloads_group_metadata_and_frozen_legacy():
    assert app.dictionary_options() == [CURRENT, OLD]
    assert len(app.DICTIONARY_SOURCES) == 8
    source = json.loads((app.ROOT / "data/current_dictionary_source.json").read_bytes())
    path = app.ROOT / source["anksi_manifest"]
    manifest = json.loads(path.read_bytes())
    assert source["revision"] == "2026-10-26-sozi-fobi"
    assert manifest["revision"] == "2026-10-24-anksi"
    assert manifest["changes"] == {"anksi": ["忧虑", "忧ᴬᴷ"]}
    assert manifest["safe_reverse_aliases"] == manifest["ownership_transfers"] == {}
    assert manifest["documentation_only_changes"] == {"angor": {"group_count": [1, 2]}}
    assert manifest["assignment_unchanged_item_count"] == 10639
    assert manifest["current_item_count"] == manifest["baseline_item_count"] == 10640
    assert manifest["unrelated_items_count"] == 10638
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source["anksi_manifest_sha256"]
    monaco = json.loads((app.ROOT / "data/monaco_source_20261017.json").read_bytes())
    for root, expected in (("anksi", "忧ᴬᴷ"), ("angor", "忧")):
        row = next(r for r in monaco["items"] if r["sourceRoot"] == root)
        assert row["body"] == expected and "\nグループ数: 2\n" in row["documentation"]
    rows = list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding="utf-8"))))
    assert len(rows) == 10678
    assert [r["kanji"] for r in rows if r["source_root"] == "anksi"] == ["忧ᴬᴷ"]
    full, two = app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest() == source["current_csv_sha256"]
    assert hashlib.sha256(two).hexdigest() == source["current_snippet_csv_sha256"]
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full))) == app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    old, old_two = app.edition_download_data(OLD)
    assert hashlib.sha256(old).hexdigest() == app.EDITION_POLICY["fixed_csv_sha256"]
    assert hashlib.sha256(old_two).hexdigest() == app.EDITION_POLICY["fixed_two_column_sha256"]

def test_user_csv_mapping_is_not_reassigned():
    frame = pd.DataFrame([("custom", "忧ᴬᴷ", "0")], columns=["esperanto", "kanji", "priority"])
    records = app.effective_mapping_records("custom", frame)
    assert records == app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet("忧ᴬᴷo", app.build_mapping_index_cached(records)) == "customo"
