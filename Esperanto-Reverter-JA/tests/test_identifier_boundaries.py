"""A superscript identifier must be consumed whole, by any dictionary key."""
import string

import pandas as pd
import pytest
import esperanto_converter as app


def index(rows):
    return app.build_mapping_index(pd.DataFrame(rows, columns=['esperanto', 'kanji', 'priority']))


def convert(text, rows):
    return app.convert_kanji_esperanto_to_alphabet(text, index(rows))


@pytest.mark.parametrize('source', ['pejvo-piv-20260620', 'pre-las-20261017'])
def test_real_long_identifiers_do_not_fall_back_to_short_whole_keys(source):
    records = app.effective_mapping_records(source, app.load_dictionary_source(source))
    idx = app.build_mapping_index_cached(records)
    assert app.convert_kanji_esperanto_to_alphabet(
        '远复ᴷˢ 远复ᴷᴹ 远复ᴷo 在ᶜ̂ 天ᶜ̂o', idx
    ) == 'telekompleks telekomplik telekopio ĉe ĉielo'
    assert app.convert_kanji_esperanto_to_alphabet(
        '丸ᵀ炎ᵀo 丸ᴼ炎ᵀo 兰炎ᵀa', idx
    ) == 'testikito orkidito orkidita'


def test_rejecting_only_the_new_alias_would_still_be_wrong():
    rows = [('tele', '远', '0'), ('telekopi', '远复', '0'),
            ('telekopi', '远复ᴷ', '0'), ('kopi', '复ᴷ', '0'),
            ('kompleks', '复ᴷˢ', '0'), ('komplik', '复ᴷᴹ', '0')]
    assert convert('远复ᴷˢo 远复ᴷᴹa', rows) == 'telekomplekso telekomplika'
    # It must also work without the new alias: old 远复 must not eat part of ᴷˢ.
    assert convert('远复ᴷˢo', [r for r in rows if r[1] != '远复ᴷ']) == 'telekomplekso'


@pytest.mark.parametrize('identifier', ['ᴷˢ', 'ᴷᴹ', 'ᶜ̂', 'ᵁ̆', 'ᶜ̂ᴷ', 'ᴳ̂ˢ'])
def test_unknown_identifier_cannot_be_replaced_by_any_short_prefix(identifier):
    rows = [('bare', '字', '0')]
    rows += [('prefix', '字' + identifier[:n], '0') for n in range(1, len(identifier))]
    assert convert('字' + identifier + 'o', rows) == '字' + identifier + 'o'
    rows += [('complete', '字' + identifier, '0')]
    assert convert('字' + identifier + 'o', rows) == 'completeo'


def test_unknown_run_is_not_restarted_at_a_known_suffix():
    # A suffix-only custom entry must not consume the second half of an unknown ID.
    rows = [('short', '精ˢ', '0'), ('tail', 'ᵀ', '0'), ('hat', '̂', '0')]
    assert convert('精ˢᵀo 字ᶜ̂a', rows) == '精ˢᵀo 字ᶜ̂a'
    assert convert('ˢᵀ', rows) == 'ˢᵀ'
    # An explicit custom key for the entire standalone run still has its own meaning.
    assert convert('ˢᵀ', rows + [('whole', 'ˢᵀ', '0')]) == 'whole'


def test_combining_mark_is_part_of_the_identifier_and_is_not_normalized_away():
    rows = [('ordinaryc', '字ᶜ', '0'), ('ĉ', '字ᶜ̂', '0'),
            ('ordinaryu', '字ᵁ', '0'), ('ŭ', '字ᵁ̆', '0')]
    assert convert('字ᶜ 字ᶜ̂ 字ᵁ 字ᵁ̆', rows) == 'ordinaryc ĉ ordinaryu ŭ'


def test_custom_complete_key_priority_and_greedy_longest_match_are_unchanged():
    rows = [('short', '天', '0'), ('long', '天空', '3'),
            ('loser', '天空ᶜ̂', '5'), ('winner', '天空ᶜ̂', '-1')]
    frame = pd.DataFrame(rows, columns=['esperanto', 'kanji', 'priority'])
    custom = app.effective_mapping_records('custom', frame)
    assert custom == app.dataframe_to_mapping_records(frame)
    idx = app.build_mapping_index_cached(custom)
    assert app.convert_kanji_esperanto_to_alphabet('天空 天空ᶜ̂O', idx) == 'long winnero'
    # The complete preceding component may still convert; the unknown final identifier stays intact.
    assert app.convert_kanji_esperanto_to_alphabet('天空ᶜ̂ᴷo', idx) == 'short空ᶜ̂ᴷo'


def test_unrelated_punctuation_and_latin_endings_remain_separate():
    rows = [('nom', '名', '0')]
    assert convert("名o 名! 名？ 名’ 名ʼ 名²", rows) == "nomo nom! nom？ nom’ nomʼ nom²"


def old_greedy(text, idx):
    """Frozen pre-change behavior, for complete-key suffix regression only."""
    text = text.translate(str.maketrans(string.ascii_uppercase, string.ascii_lowercase))
    output = []; pos = 0
    while pos < len(text):
        for size in idx.lengths_desc:
            value = idx.by_length[size].get(text[pos:pos + size])
            if value is not None and pos + size <= len(text):
                output.append(value); pos += size
                break
        else:
            output.append(text[pos]); pos += 1
    return ''.join(output).lower()


@pytest.mark.parametrize('source', ['pejvo-piv-20260620', 'pre-las-20261017'])
def test_all_effective_complete_keys_with_24_endings_preserve_existing_results(source):
    records = app.effective_mapping_records(source, app.load_dictionary_source(source))
    idx = app.build_mapping_index_cached(records)
    suffixes = ('', 'o', 'oj', 'on', 'ojn', 'a', 'aj', 'an', 'ajn', 'e', 'i',
                'as', 'is', 'os', 'us', 'u', 'ado', 'ita', 'anta', 'inta',
                'onta', 'ilo', 'aro', 'ulo')
    for bucket in idx.by_length.values():
        for key in bucket:
            for suffix in suffixes:
                text = key + suffix
                assert app.convert_kanji_esperanto_to_alphabet(text, idx) == old_greedy(text, idx), text
