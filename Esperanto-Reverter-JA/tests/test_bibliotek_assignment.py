"""Round-trip the standalone library root, prior spelling, and neighboring compounds."""
import io

import pytest

import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
# Source root, earlier spelling, approved spelling, fixed-edition reading of the new spelling.
CASES = (('bibliotek', '库ᴮ', '书库', 'librkas'),)
ENDINGS = (
    '', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'i', 'as',
    'is', 'os', 'u', 'us', 'anta', 'ita', 'ulo', 'igi', 'aro', 'inta', 'ilo', 'ado',
)
CONTROL_READINGS = {
    '库o': 'kaso', '书o': 'libro', '库ᴳo': 'garaĝo', '库ᴿo': 'remizo', '库ᴬo': 'arsenalo',
    '书库ᴮo': 'librbiblioteko', '库ᴮᴷo': '库ᴮᴷo', '书库ᴳo': 'librgaraĝo',
    '草ᴬᴷᴼo': 'akonito', '库ᴮ家o': 'bibliotekisto', '书o板ᴮo': 'librobreto',
}


@pytest.mark.parametrize('edition', [CURRENT, LEGACY])
def test_library_in_edition_and_downloads(edition):
    source = app.load_dictionary_source(edition)
    indexes = [app.build_mapping_index_cached(app.effective_mapping_records(edition, source))]
    dictionaries = list(app.edition_download_data(edition))
    effective = app.current_effective_download_data if edition == CURRENT else app.legacy_effective_download_data
    dictionaries.append(effective(edition))
    for payload in dictionaries:
        records = app.read_assignment_csv(io.BytesIO(payload))
        indexes.append(app.build_mapping_index(records))

    expected = dict(CONTROL_READINGS)
    expected['书库家o'] = 'bibliotekisto' if edition == CURRENT else 'librkasisto'
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

