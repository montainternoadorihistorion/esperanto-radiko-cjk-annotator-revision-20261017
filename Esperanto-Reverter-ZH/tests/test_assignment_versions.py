"""The 2026-10-17 assignment is explicit; old texts keep a separate dictionary."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

import esperanto_converter_zh as app
from dictionary_source import BUNDLED_MONACO_ALL, MANIFEST, default_monaco_source, validate_current_source

OLD_CSV_SHA256 = "eed2a8bfc21a97b719e40b703ca356a6b9cd37e772811bd6d62203cfc00c4c14"
TARGETS = {"las", "emancip", "ananas", "jakv", "prioritat", "strut", "sinergi", "oliv"}
MIRROR = json.loads((app.ROOT / "data/mirror-identifiers-20261017.json").read_text(encoding="utf-8"))
TARGETS |= {row["root"] for row in MIRROR["changes"]}
TARGETS.add("stafilokok")
TARGETS.add("observatori")
TARGETS.update({"protez", "ranc"})
TARGETS.update({"sutur", "fraj"})
TARGETS.update({"nostalgi", "onk", "fortres", "onkogen", "onkologi"})
TARGETS.update({"satir", "karikatur", "sarkasm"})
TARGETS.update({"dot", "greft", "tualet"})
TARGETS.update({"spermat", "spermati", "silf", "spermatocit", "spermatofit", "spermatogenez", "spermatozo"})
TARGETS.update({"krep", "difrakt", "mortez", "meger"})
TARGETS.update({"risort", "anc^", "lantern", "lubrik"})
TARGETS.update({"uve", "uveit"})
TARGETS.update({"psitak", "uv", "limon", "limonad"})
TARGETS.update(({'bedaŭr','raŭk','buf','lofi','aŭtomat','au^tomaci'}|({'mikrob','mikrobicid','mikrobologi','diafragm'}|({'tril','sfinks','alcion','alced'}|({'anksi'}|({'ŝtip','pensi','sankci'}|({'almenaŭ','forniks','karen','naŭz'}|({'armatur','arund','donak','androzac','armoraci','diktamn'}|({'letargi'}|({'madz','tribord'}|({'s^malc','sfeg','simuli'}|(({'klarion','stal','fuz','ligatur','eu^fori','sofism','hibisk'}|{'instig', 'karoten', 'psilofit', 'panak', 'pense', 'karot', 'pasiflor', 'ginseng', 'delic', 'delekt', 'elegi'})|{'agorafobi','fob','fobi','hidrofob','hidrofobi','ksenofob','ksenofobi','simptom','simptomologi','sozi'}))))))))))))  # later user-approved six assignments


def mapping(source_id):
    return app.build_mapping_index(app.read_assignment_csv(app.DICTIONARY_SOURCES[source_id]["path"]))


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_historical_csv_is_byte_exact_and_only_target_rows_changed():
    assert hashlib.sha256(app.PRE_LAS_20261017_CSV.read_bytes()).hexdigest() == OLD_CSV_SHA256
    old = csv_rows(app.PRE_LAS_20261017_CSV)
    new = csv_rows(app.PEJVO_PIV_20260620_CSV)
    assert len(old) == 10636
    assert len(new) == MIRROR["current_csv_count"] + 34  # dot/greft aliases and sperm root/aliases and satir aliases, nostalgi/onk/fortres/mirrors, sutur/fraj, krep/difrakt/mortez/meger, protez/ranc, stafilokok, four shared assignments, uve/uveit, observatori, and three-short aliases
    assert [r for r in old if r["source_root"] not in TARGETS] == [r for r in new if r["source_root"] not in TARGETS]
    assert {r["esperanto"]: r["kanji"] for r in new if r["source_root"] in {"las", "emancip"}} == {"las": "放", "emancip": "放ᴱ"}


@pytest.mark.parametrize("source_id", ["pejvo-piv-20260620", "legacy-minimal", "pre-mirror-20261017", "pre-las-20261017"])
def test_profile_roots_and_inflections_round_trip(source_id):
    index = mapping(source_id)
    old = source_id == "pre-las-20261017"
    roots = {"las": "留" if old else "放", "emancip": "放" if old else "放ᴱ"}
    for root, body in roots.items():
        for ending in ("", "i", "as", "is", "os", "u", "ita", "itaj", "itan", "intojn", "igi"):
            for suffix in (ending, ending.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body + suffix, index) == root + ending
    # A different root containing 放 is unchanged; do not blanket-replace the character.
    assert app.convert_kanji_esperanto_to_alphabet("放肆a", index) == "impertinenta"


def test_ambiguous_bare_character_requires_the_selected_profile():
    assert app.convert_kanji_esperanto_to_alphabet("留is 放is 放ᴱis", mapping("pejvo-piv-20260620")) == "留is lasis emancipis"
    assert app.convert_kanji_esperanto_to_alphabet("留is 放is 放ᴱis", mapping("pre-las-20261017")) == "lasis emancipis 放ᴱis"
    assert mapping("legacy-minimal") == mapping("pejvo-piv-20260620")


def test_current_source_guard_rejects_missing_or_unreviewed_input(tmp_path):
    with pytest.raises(ValueError, match="source is missing"):
        validate_current_source(tmp_path / "missing.json")
    wrong = tmp_path / "old-or-modified.json"
    wrong.write_text('{"items": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 differs"):
        validate_current_source(wrong)
    before = app.PEJVO_PIV_20260620_CSV.read_bytes()
    command = [sys.executable, "-B", str(app.ROOT / "tools" / "build_reverter_dictionary_from_all_json.py"), str(wrong), str(app.PEJVO_PIV_20260620_CSV)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 1
    assert "SHA256 differs" in result.stderr
    assert app.PEJVO_PIV_20260620_CSV.read_bytes() == before
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert hashlib.sha256(before).hexdigest() == manifest["current_csv_sha256"]


def test_standalone_source_is_reviewed_and_sibling_takes_precedence(tmp_path):
    validate_current_source(BUNDLED_MONACO_ALL)
    sibling = tmp_path / "all.json"
    assert default_monaco_source(sibling, BUNDLED_MONACO_ALL) == BUNDLED_MONACO_ALL
    sibling.write_text('{"items": []}', encoding="utf-8")
    assert default_monaco_source(sibling, BUNDLED_MONACO_ALL) == sibling
    with pytest.raises(ValueError, match="SHA256 differs"):
        validate_current_source(default_monaco_source(sibling, BUNDLED_MONACO_ALL))


def test_ui_selects_old_and_new_without_guessing_and_invalidates_stale_result():
    at = AppTest.from_file(str(Path(app.__file__)), default_timeout=20).run()
    assert not at.exception
    assert at.sidebar.selectbox[0].value == app.DEFAULT_DICTIONARY_ID
    assert app.dictionary_label("pre-las-20261017") in at.sidebar.selectbox[0].options
    at.text_area[0].set_value("留IS 放IS 放ᴱIS")
    at.button[0].click().run()
    assert not at.exception
    assert at.text_area[1].value == "留is lasis emancipis"
    at.sidebar.selectbox[0].set_value("pre-las-20261017").run()
    assert at.warning
    at.button[0].click().run()
    assert not at.exception
    assert at.text_area[1].value == "lasis emancipis 放ᴱis"
    assert not at.warning
    at.sidebar.selectbox[0].set_value("pejvo-piv-20260620").run()
    assert at.warning
    at.button[0].click().run()
    assert not at.exception
    assert at.text_area[1].value == "留is lasis emancipis"
