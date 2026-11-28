"""Check the five approved roots, historical readings, and longer identifiers."""
import io

import pytest

import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
# Source root, earlier spelling, approved spelling, fixed-edition reading of the new spelling.
CASES = (
    ('gosipi', '草ᴳˢ', '棉ᴳ', '棉ᴳ'),
    ('kupres', '木ᴷˢ', '柏ᴷ', '柏ᴷ'),
    ('desmod', '兽ᴰˢ', '蝠ᴰ', '蝠ᴰ'),
    ('stakis', '草ˢᵀᴬ', '水苏ˢˢ', 'akv苏ˢˢ'),
    ('legend', '传ᴸ', '读须', 'legend'),
)
ENDINGS = (
    '', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'i', 'as',
    'is', 'os', 'u', 'us', 'anta', 'ita', 'ulo', 'igi', 'aro', 'inta', 'ilo', 'ado',
)
CONTROL_READINGS = {
    '棉o': 'vato',
    '棉ᴷo': 'kotono',
    '柏o': 'cipreso',
    '柏ᵀo': 'taksuso',
    '蝠o': 'vesperto',
    '蝠ᶠo': 'filostomo',
    '蝠ⱽᴸo': 'vespertiliono',
    '水苏o': 'stakio',
    '水苏ᴮo': 'betoniko',
    '水苏糖ᴼo': 'stakiozo',
    '读o': 'lego',
    '须a': 'enda',
    '读须a': 'legenda',
    '传o': 'komuniko',
    '传ᵀo': 'transmisio',
    '遗传o': 'genetiko',
    '棉ᴳᴷo': '棉ᴳᴷo',
    '柏ᴷᴹo': '柏ᴷᴹo',
    '蝠ᴰᴷo': '蝠ᴰᴷo',
    '水苏ˢˢᴮo': 'akv苏ˢˢᴮo',
    '草ˢᵀᴬᴷo': '草ˢᵀᴬᴷo',
}


@pytest.mark.parametrize('edition', [CURRENT, LEGACY])
def test_approved_five_in_edition_and_downloads(edition):
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
