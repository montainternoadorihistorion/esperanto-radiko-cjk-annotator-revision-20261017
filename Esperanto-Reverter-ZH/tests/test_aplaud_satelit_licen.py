"""Round trips for three roots, previous spellings, and immutable identifier owners."""
import io

import pytest

import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
# Source root, earlier spelling, approved spelling, fixed-edition reading of the new spelling.
CASES = (
    ('aplaŭd', '鼓ᴬ', '拍手', 'fotman'),
    ('satelit', '星ˢᵀ', '卫星', 'gvardistel'),
    ('licen', '虫ᴸᶜ', '蝶ᴸᶜ', '蝶ᴸᶜ'),
)
ENDINGS = (
    '', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'i', 'as',
    'is', 'os', 'u', 'us', 'anta', 'ita', 'ulo', 'igi', 'aro', 'inta', 'ilo', 'ado',
)
CONTROL_READINGS = {
    '鼓o': 'tamburo', '拍o': 'foto', '手o': 'mano', '星o': 'stelo', '卫o': 'gvardio',
    '虫o': 'insekto', '蝶o': 'papilio', '蝶ᴸo': 'lepidoptero', '糖ᴷᴰo': 'kando',
    '虫ᴸᶜᴷo': '虫ᴸᶜᴷo', '蝶ᴸᶜᴷo': '蝶ᴸᶜᴷo', '鼓ᴬᴷo': '鼓ᴬᴷo', '星ˢᵀᴷo': '星ˢᵀᴷo',
}


@pytest.mark.parametrize('edition', [CURRENT, LEGACY])
def test_three_roots_in_edition_and_downloads(edition):
    source = app.load_dictionary_source(edition)
    indexes = [app.build_mapping_index_cached(app.effective_mapping_records(edition, source))]
    dictionaries = list(app.edition_download_data(edition))
    effective = app.current_effective_download_data if edition == CURRENT else app.legacy_effective_download_data
    dictionaries.append(effective(edition))
    for payload in dictionaries:
        records = app.read_assignment_csv(io.BytesIO(payload))
        indexes.append(app.build_mapping_index(records))

    expected = dict(CONTROL_READINGS)
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

