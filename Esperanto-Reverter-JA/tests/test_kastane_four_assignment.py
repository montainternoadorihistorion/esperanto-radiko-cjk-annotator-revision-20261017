"""Check the four approved roots, historical readings, and longer identifiers."""
import io

import pytest

import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
# Source root, earlier spelling, approved spelling, fixed-edition reading of the new spelling.
CASES = (
    ('kastane', '木ᴷᴬˢ', '栗ᴷˢ', '栗ᴷˢ'),
    ('hipermetrop', '远ᴴ', '远视', 'teletelevid'),
    ('kalson', '裤ᴷ', '内裤', 'enpantalon'),
    ('streptopeli', '鸟ˢᴱ', '鸽ˢ', '鸽ˢ'),
)
ENDINGS = (
    '', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'i', 'as',
    'is', 'os', 'u', 'us', 'anta', 'ita', 'ulo', 'igi', 'aro', 'inta', 'ilo', 'ado',
)
CONTROL_READINGS = {
    '鸽o': 'kolombo',
    '鸽ᵀo': 'turto',
    '栗o': 'kaŝtano',
    '栗ᴹo': 'marono',
    '近ᴹo': 'miopo',
    '座ᵀo': 'trono',
    '裤o': 'pantalono',
    '视o': 'televido',
    '近视o': 'proksimtelevido',
    '王座o': 'reĝingo',
    '栗ᴷˢᴹo': '栗ᴷˢᴹo',
    '鸽ˢᴷo': '鸽ˢᴷo',
    '木ᴷᴬˢᴹo': '木ᴷᴬˢᴹo',
    '鸟ˢᴱᴹo': '鸟ˢᴱᴹo',
    '裤ᴷᴹo': '裤ᴷᴹo',
    '远ᴴᴹo': '远ᴴᴹo',
    '远视ᴷo': 'tele视ᴷo',
    '内裤ᴷo': 'enkalsono',
    '远视ⱽo': 'televideo',
    '内裤ᴹo': 'en裤ᴹo',
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
    expected['浴内裤o'] = 'bankalsono' if edition == CURRENT else 'banenpantalono'
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
        return rows_from_all_json({'items': [{'sourceRoot': r, 'body': body} for r, body in items]})

    assert {row['kanji'] for row in build([(root, current)])} == {current, earlier}
    assert [row['kanji'] for row in build([(root, 'custom')])] == ['custom']
    with pytest.raises(ValueError, match='conflicts'):
        build([(root, current), ('another', earlier)])

