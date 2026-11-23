"""Independent university and reindeer owners, including historical displays."""
from functools import lru_cache
import io
import pytest
import esperanto_converter_zh as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json

CURRENT = 'pejvo-piv-20260620'
LEGACY = 'pre-las-20261017'
APPROVED = [('universitat', '大学', '学ᵁ'), ('boac', '驯鹿ᴮ', '鹿ᴮ'), ('karibu', '驯鹿ᴷ', '兽ᴷᴿ')]
NEIGHBOURS = {'驯鹿': 'rangifer', '鹿': 'cerv', '学': 'lern', '大学ᴸᴳ': 'grandlogi',
              '大学ᵁ': 'granduniversitat', '木ᴳᴷ': 'gink'}
EARLIER = {'大学': 'grandlern', '驯鹿ᴮ': 'dresboac', '驯鹿ᴷ': 'dreskapreol'}


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
    indexes = [index(edition)] + [
        app.build_mapping_index(app.read_assignment_csv(io.BytesIO(payload))) for payload in (full, snippet, effective)]
    for idx in indexes:
        for key, root in wanted.items():
            for ending in ('', 'o', 'ojn', 'a', 'ajn', 'e', 'i', 'as', 'IS', 'os', 'igi', 'isto'):
                assert app.convert_kanji_esperanto_to_alphabet(key + ending, idx) == root + ending.lower()
        assert app.convert_kanji_esperanto_to_alphabet('驯鹿ᴷᴿo', idx) == 'dres鹿ᴷᴿo'
        assert app.convert_kanji_esperanto_to_alphabet('驯鹿ᴮᴸo', idx) == 'dres鹿ᴮᴸo'


@pytest.mark.parametrize('root,new,old', APPROVED)
def test_reverse_alias_needs_the_approved_current_source(root, new, old):
    def build(*pairs):
        return rows_from_all_json({'items': [{'sourceRoot': r, 'body': v} for r, v in pairs]})
    assert {r['kanji'] for r in build((root, new))} == {new, old}
    assert [r['kanji'] for r in build((root, 'custom'))] == ['custom']
    with pytest.raises(ValueError, match='conflicts with another root'):
        build((root, new), ('another', old))

