"""Cloud regression: cached indices must survive replacement of __main__."""
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import ast
import sys

import pandas as pd
import esperanto_converter as app


RECORDS = (
    ("less", "同", "9"), ("win", "同", "1"),
    ("fic", "藻ᶠᶜ", "0"), ("alg", "藻", "0"),
    ("or", "金", "0"), ("eŭropi", "金ᴱᵁ̆", "0"),
    ("ĉio", "全o", "0"), ("integr", "全", "1"),
)
TEXT = "同 藻ᶠᶜoj 藻oj 金ᴱᵁ̆o 全O ABC"
EXPECTED = "win ficoj algoj eŭropio ĉio abc"


@contextmanager
def entrypoint_module():
    """Execute the real entrypoint as Streamlit does, without invoking its UI."""
    source = Path(app.__file__)
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    # Only remove the final UI invocation; retain the actual classes/cache code.
    last = tree.body[-1]
    assert isinstance(last, ast.If)
    assert ast.unparse(last.test) == "__name__ == '__main__'"
    assert len(last.body) == 1 and ast.unparse(last.body[0]) == "main()"
    tree.body.pop()
    module = ModuleType("__main__")
    module.__file__ = str(source)
    with patch.dict(sys.modules, {"__main__": module}):
        exec(compile(tree, str(source), "exec"), module.__dict__)
        yield module


def test_mapping_cache_survives_unrelated_main_module():
    # Streamlit's cached data is shared by sessions, but the process-wide
    # __main__ may meanwhile refer to a different run without MappingIndex.
    with entrypoint_module() as first_run:
        first_run.build_mapping_index_cached.clear()
        try:
            cold = first_run.build_mapping_index_cached(RECORDS)
            assert first_run.convert_kanji_esperanto_to_alphabet(TEXT, cold) == EXPECTED
            other_session = ModuleType("__main__")
            other_session.__file__ = "another_streamlit_run.py"
            with patch.dict(sys.modules, {"__main__": other_session}):
                warm = first_run.build_mapping_index_cached(RECORDS)
            assert type(warm) is first_run.MappingIndex
            assert first_run.convert_kanji_esperanto_to_alphabet(TEXT, warm) == EXPECTED
        finally:
            first_run.build_mapping_index_cached.clear()


def test_mapping_cache_hit_uses_recreated_entrypoint_class():
    with entrypoint_module() as first_run:
        first_run.build_mapping_index_cached.clear()
        try:
            cold = first_run.build_mapping_index_cached(RECORDS)
            with entrypoint_module() as next_run:
                assert next_run.MappingIndex is not first_run.MappingIndex
                with patch.object(next_run, "build_mapping_index", side_effect=AssertionError("Cache hit unexpectedly rebuilt the index")):
                    warm = next_run.build_mapping_index_cached(RECORDS)
                assert type(warm) is next_run.MappingIndex
                assert warm.by_length == cold.by_length
                assert next_run.convert_kanji_esperanto_to_alphabet(TEXT, warm) == EXPECTED
        finally:
            first_run.build_mapping_index_cached.clear()


def test_mapping_cache_clear_and_session_copy_isolation():
    app.build_mapping_index_cached.clear()
    try:
        with patch.object(app, "build_mapping_index", wraps=app.build_mapping_index) as build:
            first = app.build_mapping_index_cached(RECORDS)
            first.by_length[1]["同"] = "caller_mutation"
            second = app.build_mapping_index_cached(RECORDS)
            assert app.convert_kanji_esperanto_to_alphabet(TEXT, second) == EXPECTED
            assert build.call_count == 1
            app.build_mapping_index_cached.clear(RECORDS)
            app.build_mapping_index_cached(RECORDS)
            assert build.call_count == 2
            app.build_mapping_index_cached.clear()
            app.build_mapping_index_cached(RECORDS)
            assert build.call_count == 3
    finally:
        app.build_mapping_index_cached.clear()


def test_empty_mapping_cache_survives_recreated_entrypoint():
    with entrypoint_module() as first_run:
        first_run.build_mapping_index_cached.clear()
        try:
            cold = first_run.build_mapping_index_cached(())
            with entrypoint_module() as next_run:
                with patch.object(next_run, "build_mapping_index", side_effect=AssertionError("Empty cache unexpectedly rebuilt")):
                    warm = next_run.build_mapping_index_cached(())
                assert type(warm) is next_run.MappingIndex
                assert warm.by_length == cold.by_length == {}
                assert warm.lengths_desc == []
                assert warm.entry_count == warm.max_length == 0
                assert next_run.convert_kanji_esperanto_to_alphabet("ABC 同", warm) == "abc 同"
        finally:
            first_run.build_mapping_index_cached.clear()



def test_cached_current_and_fixed_indices_equal_uncached_all_keys():
    app.build_mapping_index_cached.clear()
    try:
        for source_id in app.VISIBLE_EDITION_IDS:
            frame = app.load_dictionary_source(source_id)
            records = app.dataframe_to_mapping_records(frame)
            # The pre-existing cached implementation builds from these records,
            # so compare that exact source frame, including row order/priority.
            expected = app.build_mapping_index(pd.DataFrame(records, columns=["esperanto", "kanji", "priority"]))
            actual = app.build_mapping_index_cached(records)
            assert actual.by_length == expected.by_length
            assert actual.lengths_desc == expected.lengths_desc
            assert actual.entry_count == expected.entry_count
    finally:
        app.build_mapping_index_cached.clear()
