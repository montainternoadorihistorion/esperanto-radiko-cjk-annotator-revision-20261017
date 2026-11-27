"""Current and legacy reverse readings for robur, aŭrikulari, futbal, negund and citron."""
from functools import lru_cache
import io
import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json

CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
APPROVED = [('robur', '橡ᴿ', '木ᴿᴮ'), ('aŭrikulari', '木耳', '菌ᴬᵁ̆'), ('futbal', '足球', '球ᶠ'), ('negund', '枫ᴺ', '木ᴺᴳ'), ('citron', '柠ᶜ', '果ᶜ')]
NEIGHBOURS = {'橡': 'kverk', '橡ᴳ': 'glan', '枫': 'acer', '木': 'lign', '耳': 'orel', '球': 'pilk', '麦ᴴ': 'horde'}
EARLIER = {'橡ᴿ': '橡ᴿ', '木耳': 'lignorel', '足球': 'piedpilk', '枫ᴺ': '枫ᴺ', '柠ᶜ': '柠ᶜ'}


@lru_cache()
def index(edition):
    data = app.load_dictionary_source(edition)
    return app.build_mapping_index_cached(app.effective_mapping_records(edition, data))


@pytest.mark.parametrize('edition', [CURRENT, LEGACY])
def test_edition_and_downloads_restore_whole_roots(edition):
    wanted = NEIGHBOURS | {old: root for root, _, old in APPROVED}
    wanted.update({new: root for root, new, _ in APPROVED} if edition == CURRENT else EARLIER)
    full, snippet = app.edition_download_data(edition)
    effective = (app.current_effective_download_data if edition == CURRENT
                 else app.legacy_effective_download_data)(edition)
    def from_download(payload):
        return app.build_mapping_index(app.read_assignment_csv(io.BytesIO(payload)))

    indexes = {
        'runtime': index(edition), 'effective': from_download(effective),
        'full': from_download(full), 'snippet': from_download(snippet),
    }
    for kind, idx in indexes.items():
        expected = wanted.copy()
        for key, root in expected.items():
            for ending in ('', 'o', 'ojn', 'a', 'ajn', 'e', 'i', 'as', 'IS', 'os', 'igi', 'isto'):
                assert app.convert_kanji_esperanto_to_alphabet(key + ending, idx) == root + ending.lower()
        assert app.convert_kanji_esperanto_to_alphabet('木耳ᴷo', idx) == 'lign耳ᴷo'
        assert app.convert_kanji_esperanto_to_alphabet('足球ᴷo', idx) == 'pied球ᴷo'
        assert app.convert_kanji_esperanto_to_alphabet('柠ᶜᴷo', idx) == '柠ᶜᴷo'
        assert app.convert_kanji_esperanto_to_alphabet('柠o', idx) == ('limono' if edition == CURRENT else '柠o')
        assert app.convert_kanji_esperanto_to_alphabet('足球场o', idx) == ('futbalsceno' if edition == CURRENT else 'piedpilksceno')


@pytest.mark.parametrize('root,new,old', APPROVED)
def test_reverse_alias_needs_the_approved_current_source(root, new, old):
    root = root.replace('ŭ', 'u^')
    def build(*pairs):
        return rows_from_all_json({'items': [{'sourceRoot': r, 'body': v} for r, v in pairs]})
    assert {r['kanji'] for r in build((root, new))} == {new, old}
    assert [r['kanji'] for r in build((root, 'custom'))] == ['custom']
    with pytest.raises(ValueError, match='conflicts with another root'):
        build((root, new), ('another', old))

