"""Four accepted roots, the singer compound, downloads and custom dictionaries."""
import io

import pytest

import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
# Source root, earlier spelling, approved spelling, fixed-edition reading of the new spelling.
CASES = (
    ('pumili', '木ᴾᴹ', '松ᴾᴹ', '松ᴾᴹ'),
    ('labrusk', '草ᴸᴮ', '葡ᴸ', '葡ᴸ'),
    ('dafodil', '草ᴰᶠ', '水仙ᴰ', 'akv仙ᴰ'),
    ('kontralt', '女低', '女低音', 'kontraltprononc'),
)
ENDINGS = (
    '', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'i', 'as',
    'is', 'os', 'u', 'us', 'anta', 'ita', 'ulo', 'igi', 'aro', 'inta', 'ilo', 'ado',
)
CONTROL_READINGS = {
    '松o': 'pino', '葡o': 'vito', '水仙o': 'narciso', '水仙ᴶo': 'jonkvilo',
    '女高音o': 'soprano', '男中音o': 'baritono', '低音o': 'borduno', '中音o': 'aldo',
    '女低者女o': 'kontraltulino',
    '松ᴾᴹᴷo': '松ᴾᴹᴷo', '草ᴸᴮᴷo': '草ᴸᴮᴷo', '草ᴰᶠᴷo': '草ᴰᶠᴷo',
    '葡ᴸᴷo': '葡ᴸᴷo', '水仙ᴰᴷo': 'akv仙ᴰᴷo', '女低音ᴷo': 'kontralt音ᴷo',
}


@pytest.mark.parametrize('edition', [CURRENT, LEGACY])
def test_four_roots_in_edition_and_downloads(edition):
    source = app.load_dictionary_source(edition)
    indexes = [app.build_mapping_index_cached(app.effective_mapping_records(edition, source))]
    dictionaries = list(app.edition_download_data(edition))
    effective = app.current_effective_download_data if edition == CURRENT else app.legacy_effective_download_data
    dictionaries.append(effective(edition))
    for payload in dictionaries:
        records = app.read_assignment_csv(io.BytesIO(payload))
        indexes.append(app.build_mapping_index(records))

    expected = dict(CONTROL_READINGS)
    expected['女低音者女o'] = 'kontraltulino' if edition == CURRENT else 'kontraltprononculino'
    expected['松ᴹo'] = 'mugo' if edition == CURRENT else '松ᴹo'
    expected['葡ᵁo'] = 'uvo' if edition == CURRENT else '葡ᵁo'
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

