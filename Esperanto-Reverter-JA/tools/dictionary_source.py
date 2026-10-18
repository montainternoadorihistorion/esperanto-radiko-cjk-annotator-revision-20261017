"""Validate the reviewed integrated-repository source before updating current CSVs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_CSV = ROOT / "data" / "pejvo_piv_20260620_reverter.csv"
MANIFEST = ROOT / "data" / "current_dictionary_source.json"
SIBLING_MONACO_ALL = ROOT.parent / "kanji-esperanto-monaco" / "all.json"
BUNDLED_MONACO_ALL = ROOT / "data" / "monaco_source_20261017.json"


def default_monaco_source(sibling: Path = SIBLING_MONACO_ALL, bundled: Path = BUNDLED_MONACO_ALL) -> Path:
    # An existing sibling wins even if stale: validation must reject it, not hide it
    # by silently selecting a different version. Standalone copies use the byte copy.
    return sibling if sibling.is_file() else bundled


def validate_current_source(source: Path, manifest: Path = MANIFEST) -> None:
    provenance = json.loads(manifest.read_text(encoding="utf-8"))
    if not source.is_file():
        raise ValueError(
            "Current Monaco source is missing. Restore the sibling "
            "kanji-esperanto-monaco/all.json or bundled data/monaco_source_20261017.json, "
            "or provide that same file explicitly. monaco-commit.txt records only the old dictionary."
        )
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != provenance["monaco_all_sha256"]:
        raise ValueError(
            "Monaco source SHA256 differs from data/current_dictionary_source.json. "
            "Do not regenerate current CSVs from the historical upstream pin; "
            "a new source requires a reviewed provenance update."
        )
