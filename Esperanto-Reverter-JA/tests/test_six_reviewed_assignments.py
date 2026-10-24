"""Six user-approved assignments; two editions, identifier boundaries and aliases."""
import csv
import hashlib
import io
import json

import pandas as pd
import pytest
import esperanto_converter as app

CURRENT = "pejvo-piv-20260620"
OLD = "pre-las-20261017"
CHANGES = {
    "bedaŭr": ("憾", "惜ᴮ"),
    "raŭk": ("沙哑", "哑ᴿ"),
    "buf": ("蛤蟆", "蟆"),
    "lofi": ("蛤蟆鱼", "蟆鱼"),
    "aŭtomat": ("动ᴬ", "自动"),
    "aŭtomaci": ("动ᴬᶜ", "自动ᴬᶜ"),
}
SUFFIXES = ("", "o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "i", "as", "is", "os", "us", "u", "ado", "ita", "intajn", "igi", "ĉjo")

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source, app.load_dictionary_source(source)))

@pytest.mark.parametrize("source", (CURRENT, OLD))
def test_adopted_roots_endings_and_fixed_legacy(source):
    mapping = index(source)
    column = int(source == CURRENT)
    for root, values in CHANGES.items():
        for suffix in SUFFIXES:
            for ending in (suffix, suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(values[column] + ending, mapping) == root + suffix
    # Shared characters keep their existing owner and full identifier.
    for body, root in {"惜": "domaĝ", "哑": "mut", "沙": "sabl", "蛤": "meretrik", "动": "mov", "动ᴹᵀ": "motor", "动ⱽ": "verb"}.items():
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(body + suffix, mapping) == root + suffix

def test_new_bodies_do_not_consume_a_longer_identifier():
    mapping = index(CURRENT)
    for root, (_, body) in CHANGES.items():
        for extra in ("ᴮ", "ᴿ", "ᴬᶜ", "\u0302", "\u0306"):
            text = body + extra + "o"
            assert app.convert_kanji_esperanto_to_alphabet(text, mapping) != root + extra + "o"
    assert app.convert_kanji_esperanto_to_alphabet("自动o 自动ᴬᶜo", mapping) == "aŭtomato aŭtomacio"
    assert app.convert_kanji_esperanto_to_alphabet("惜o 惜ᴮas 哑a 哑ᴿa 蟆o 蟆鱼o", mapping) == "domaĝo bedaŭras muta raŭka bufo lofio"

def test_only_two_editions_and_no_new_historical_aliases():
    assert app.dictionary_options() == [CURRENT, OLD]
    assert len(app.DICTIONARY_SOURCES) == 8
    rows = list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding="utf-8"))))
    assert len(rows) == 10678
    for root, (old, new) in CHANGES.items():
        assert [r["kanji"] for r in rows if r["esperanto"] == root] == [new]
        assert old not in {r["kanji"] for r in rows}
    supplement = json.loads((app.ROOT / "data/current_inverse_aliases.json").read_bytes())
    assert len(supplement["aliases"]) == 9
    assert {r["kanji"]: r["esperanto"] for r in supplement["aliases"]} == app.CURRENT_INVERSE_ALIAS_PAIRS
    legacy_raw, legacy_two_column = app.edition_download_data(OLD)
    assert hashlib.sha256(legacy_raw).hexdigest() == app.EDITION_POLICY["fixed_csv_sha256"]
    assert hashlib.sha256(legacy_two_column).hexdigest() == app.EDITION_POLICY["fixed_two_column_sha256"]

def test_download_source_and_reviewed_manifest_are_consistent():
    source = json.loads((app.ROOT / "data/current_dictionary_source.json").read_bytes())
    manifest = json.loads((app.ROOT / source["six_assignments_manifest"]).read_bytes())
    assert source["revision"] == "2026-10-24-anksi"
    assert manifest["revision"] == "2026-10-20-six-assignments"
    assert manifest["changes"] == {("au^tomaci" if r == "aŭtomaci" else r): list(v) for r, v in CHANGES.items()}
    assert manifest["safe_reverse_aliases"] == manifest["ownership_transfers"] == {}
    assert len(manifest["baseline_target_items"]) == len(manifest["expected_target_items"]) == 6
    assert manifest["current_item_count"] == manifest["baseline_item_count"] == 10640
    assert manifest["unrelated_items_count"] == 10634
    assert hashlib.sha256((app.ROOT / source["six_assignments_manifest"]).read_bytes()).hexdigest() == source["six_assignments_manifest_sha256"]
    assert hashlib.sha256(app.PEJVO_PIV_20260620_CSV.read_bytes()).hexdigest() == source["current_csv_sha256"]
    full, two_column = app.edition_download_data(CURRENT)
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full))) == app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two_column)))

def test_custom_csv_ownership_is_not_replaced():
    for root, (_, body) in CHANGES.items():
        frame = pd.DataFrame([("custom", body, "0")], columns=["esperanto", "kanji", "priority"])
        records = app.effective_mapping_records("custom", frame)
        assert records == app.dataframe_to_mapping_records(frame)
        assert app.convert_kanji_esperanto_to_alphabet(body + "o", app.build_mapping_index_cached(records)) == "customo"

def test_shared_spelling_with_mem_mov_keeps_explicit_edition_policy():
    # The approved current whole-root spelling is identical to the valid
    # adjacent components mem=自 plus mov=动. Do not invent a new identifier
    # or change those components to force a unique plain-text restoration.
    assert app.convert_kanji_esperanto_to_alphabet("自动a", index(OLD)) == "memmova"
    assert app.convert_kanji_esperanto_to_alphabet("自动a", index(CURRENT)) == "aŭtomata"
    assert app.convert_kanji_esperanto_to_alphabet("自a 动a", index(CURRENT)) == "mema mova"
