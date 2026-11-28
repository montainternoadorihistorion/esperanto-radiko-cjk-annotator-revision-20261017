"""Check the six approved roots and the uterit derivative, historical readings, and longer identifiers."""
import io

import pytest

import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json


CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
# Source root, earlier spelling, approved spelling, fixed-edition reading of the new spelling.
CASES = (
    ('tazet', '草ᵀᶻ', '水仙ᵀ', 'akv仙ᵀ'),
    ('makaon', '虫ᴹᴷ', '蝶ᴹ', '蝶ᴹ'),
    ('turbot', '鱼ᵀᴮ', '比目鱼ᵀ', 'olokultinus'),
    ('uter', '宫ᵁ', '子宫', 'idpalac'),
    ('pirus', '木ᴾᴵ', '梨ᴾˢ', '梨ᴾˢ'),
    ('eklezi', '教ᴱ', '教会', 'instrukongres'),
    ('uterit', '宫ᵁ炎ᵀ', '子宫炎ᵀ', 'idpalacit'),
)
ENDINGS = (
    '', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'i', 'as',
    'is', 'os', 'u', 'us', 'anta', 'ita', 'ulo', 'igi', 'aro', 'inta', 'ilo', 'ado',
)
CONTROL_READINGS = {
    '梨o': 'piro',
    '水仙o': 'narciso',
    '水仙ᴶo': 'jonkvilo',
    '蝶o': 'papilio',
    '蝶ᴸo': 'lepidoptero',
    '蝶ᴾᴺo': 'papiliono',
    '比目鱼o': 'pleŭronekto',
    '比目鱼ᶠo': 'fleso',
    '比目鱼ᴸo': 'limando',
    '比目鱼ᴾᵀo': 'plateso',
    '教o': 'instruo',
    '宫o': 'palaco',
    '子o': 'ido',
    '库ᴳo': 'garaĝo',
    '祈所o': 'preĝejo',
    '水仙ᵀᴷo': 'akv仙ᵀᴷo',
    '梨ᴾˢᴷo': '梨ᴾˢᴷo',
    '教会ᴿo': 'instru会ᴿo',
    '木ᴾᴵᴬo': '木ᴾᴵᴬo',
}

EDITION_READINGS = {
    '子宫颈ᶜo': ('utercerviko', 'idpalaccerviko'),
    '教会员o': ('ekleziano', 'instrukongresano'),
    '国ˢ̂教会o': ('ŝtateklezio', 'ŝtatinstrukongreso'),
    '子宫a': ('utera', 'idpalaca'),
}


@pytest.mark.parametrize('edition', [CURRENT, LEGACY])
def test_approved_six_and_derivative_in_edition_and_downloads(edition):
    source = app.load_dictionary_source(edition)
    indexes = [app.build_mapping_index_cached(app.effective_mapping_records(edition, source))]
    dictionaries = list(app.edition_download_data(edition))
    effective = app.current_effective_download_data if edition == CURRENT else app.legacy_effective_download_data
    dictionaries.append(effective(edition))
    for payload in dictionaries:
        records = app.read_assignment_csv(io.BytesIO(payload))
        indexes.append(app.build_mapping_index(records))

    # The fixed full/two-column CSVs predate mirror entries and supplemental suffix aliases.
    for name, index in zip(('app', 'full', 'two-column', 'effective'), indexes, strict=True):
        plain = name in ('full', 'two-column')
        expected = dict(CONTROL_READINGS)
        expected.update({key: current if edition == CURRENT else legacy
                         for key, (current, legacy) in EDITION_READINGS.items()})
        expected['炎ᵀo'] = '炎ᵀo' if plain else 'ito'
        for root, earlier, current, legacy_reading in CASES:
            earlier_reading = root
            current_reading = root if edition == CURRENT else legacy_reading
            if root == 'uterit' and edition == LEGACY and plain:
                earlier_reading = 'uter炎ᵀ'
                current_reading = 'idpalac炎ᵀ'
            for ending in ENDINGS:
                expected[earlier + ending] = earlier_reading + ending
                expected[current + ending] = current_reading + ending
        for body, result in expected.items():
            assert app.convert_kanji_esperanto_to_alphabet(body, index) == result, (edition, name, body)


@pytest.mark.parametrize('root,earlier,current,legacy_reading', CASES)
def test_old_reverse_spelling_only_for_corresponding_dictionary(root, earlier, current, legacy_reading):
    def build(items):
        return rows_from_all_json({'items': [{'sourceRoot': r, 'body': body} for r, body in items]})

    assert {row['kanji'] for row in build([(root, current)])} == {current, earlier}
    assert [row['kanji'] for row in build([(root, 'custom')])] == ['custom']
    with pytest.raises(ValueError, match='conflicts'):
        build([(root, current), ('another', earlier)])
