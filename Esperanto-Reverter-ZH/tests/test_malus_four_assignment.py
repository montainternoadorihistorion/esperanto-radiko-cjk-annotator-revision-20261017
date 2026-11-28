"""Check the four approved roots, historical readings, and longer identifiers."""
import io

import pytest

import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
# Source root, earlier spelling, approved spelling, fixed-edition reading of the new spelling.
CASES = (
    ('malus', '木ᴹˢ', '苹ᴹ', '苹ᴹ'),
    ('kolibr', '鸟ᴷᴮ', '蜂鸟', 'abelbird'),
    ('unaŭ', '兽ᵁ', '树懒ᵁ', 'arb懒ᵁ'),
    ('mebl', '具ᴹ', '家具', 'istil'),
)
ENDINGS = (
    '', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'i', 'as',
    'is', 'os', 'u', 'us', 'anta', 'ita', 'ulo', 'igi', 'aro', 'inta', 'ilo', 'ado',
)
CONTROL_READINGS = {
    '苹o': 'pomo',
    '树懒o': 'akeo',
    '头ᴾo': 'pruo',
    '船头o': 'ŝipkapo',
    '具o': 'ilo',
    '具ᴹ家o': 'meblisto',
    '苹ᴹᴷo': '苹ᴹᴷo',
    '木ᴹˢᴷo': '木ᴹˢᴷo',
    '鸟ᴷᴮᴹo': '鸟ᴷᴮᴹo',
    '树懒ᵁᴷo': 'arb懒ᵁᴷo',
    '兽ᵁᴷo': '兽ᵁᴷo',
    '具ᴹᴷo': '具ᴹᴷo',
    '家具ᴹo': 'istmeblo',
    '蜂鸟ᴷᴮo': 'abelkolibro',
    '蜂o': 'abelo',
    '鸟o': 'birdo',
    '树o': 'arbo',
    '懒o': 'pigro',
}


@pytest.mark.parametrize('edition', [CURRENT, LEGACY])
def test_approved_four_in_edition_and_downloads(edition):
    source = app.load_dictionary_source(edition)
    indexes = [app.build_mapping_index_cached(app.effective_mapping_records(edition, source))]
    dictionaries = list(app.edition_download_data(edition))
    effective = app.current_effective_download_data if edition == CURRENT else app.legacy_effective_download_data
    dictionaries.append(effective(edition))
    for payload in dictionaries:
        records = app.read_assignment_csv(io.BytesIO(payload))
        indexes.append(app.build_mapping_index(records))

    expected = dict(CONTROL_READINGS)
    expected['家具家o'] = 'meblisto' if edition == CURRENT else 'istilisto'
    expected['树懒ᴮo'] = 'bradipo' if edition == CURRENT else 'arb懒ᴮo'
    for root, earlier, current, legacy_reading in CASES:
        for ending in ENDINGS:
            expected[earlier + ending] = root + ending
            expected[current + ending] = (root if edition == CURRENT else legacy_reading) + ending
    for index in indexes:
        for body, result in expected.items():
            assert app.convert_kanji_esperanto_to_alphabet(body, index) == result, (edition, body)


@pytest.mark.parametrize('root,earlier,current,legacy_reading', CASES)
def test_old_reverse_spelling_only_for_corresponding_dictionary(root, earlier, current, legacy_reading):
    def build(items):
        return rows_from_all_json({'items': [{'sourceRoot': r.replace('ŭ', 'u^'), 'body': body} for r, body in items]})

    assert {row['kanji'] for row in build([(root, current)])} == {current, earlier}
    assert [row['kanji'] for row in build([(root, 'custom')])] == ['custom']
    with pytest.raises(ValueError, match='conflicts'):
        build([(root, current), ('another', earlier)])

