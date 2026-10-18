"""Exact inverse-only additions selected from the full observed-output audit."""
from pathlib import Path
import hashlib
import io
import json
import shutil

import pandas as pd
import pytest
import esperanto_converter as app

CURRENT = 'pejvo-piv-20260620'
OLD = 'pre-las-20261017'
COMMON = {
    '盐ᴬ': 'at', '盐ᴵ': 'it', '炎ᵀ': 'it', '兄ᶠᴿ': 'fra',
    '父ᴾᴬ': 'pa', '插ᴾ': 'pol', '白ᴸᴱ': 'leŭk',
}
OLD_EXTRA = {
    '两ᴴ': 'herm', '名ᴺᴵ': 'nim', '远声ᶠᴼ': 'telefon',
    '微镜ˢᴷ': 'mikroskop', '氧生ᴳ': 'oksigen',
    '间学ᴸᴺ': 'interlingvistik', '越形具ᴬ': 'transformator',
    '单色ᴷᴿ': 'monokromat',
}
PREVIOUS = {
    CURRENT: {'兰炎ᵀ': 'orkidit'},
    OLD: {'丸ᵀ炎ᵀ': 'testikit', '丸ᴼ炎ᵀ': 'orkidit', '兰炎ᵀ': 'orkidit'},
}
NEW = {CURRENT: COMMON, OLD: {**COMMON, **OLD_EXTRA}}
SUFFIXES = ('', 'o', 'oj', 'on', 'ojn', 'a', 'aj', 'an', 'ajn', 'e', 'i',
            'as', 'is', 'os', 'us', 'u', 'ado', 'ita', 'ĉjo', 'ĉjoj', 'o!', 'O')


def records(source):
    return app.dataframe_to_mapping_records(app.load_dictionary_source(source))


def index(rows):
    return app.build_mapping_index_cached(tuple(rows))


def flat(idx):
    return {key: owner for bucket in idx.by_length.values() for key, owner in bucket.items()}


@pytest.mark.parametrize('source', (CURRENT, OLD))
def test_exact_reviewed_set_existing_owners_and_previous_repairs(source):
    base = records(source)
    previous = base + tuple((owner, key, '0') for key, owner in PREVIOUS[source].items())
    final = app.effective_mapping_records(source, app.load_dictionary_source(source))
    expected = previous + tuple((owner, key, '0') for key, owner in NEW[source].items())
    assert final == expected
    before, after = flat(index(previous)), flat(index(final))
    assert {key: value for key, value in after.items() if key not in before} == NEW[source]
    assert all(after[key] == value for key, value in before.items())
    idx = index(final)
    for key, owner in {**PREVIOUS[source], **NEW[source]}.items():
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(key + suffix, idx) == owner + suffix.lower()
    assert app.effective_mapping_records(source, pd.DataFrame(final, columns=['esperanto', 'kanji', 'priority'])) == final


@pytest.mark.parametrize('source', (CURRENT, OLD))
def test_actual_missing_components_improve_without_reinterpreting_ambiguities(source):
    idx = index(app.effective_mapping_records(source, app.load_dictionary_source(source)))
    expected = {
        '安息香盐ᴬa 酸o': 'benzoata acido',
        '兄ᶠᴿĉjo 父ᴾᴬĉjo': 'fraĉjo paĉjo',
        '间插ᴾ物': 'interpolaĵ', '白ᴸᴱ血ᴱ': 'leŭkemi',
        'mejbom炎ᵀo': 'mejbomito',
        '丸ᵀ炎ᵀo 丸ᴼ炎ᵀo 兰炎ᵀa': 'testikito orkidito orkidita',
    }
    if source == CURRENT:
        expected.update({'亚碘盐ᴵ': 'hipojodit', '外ᴷˢ节ᴬᴿ炎ᵀa': 'ksenartrita'})
    else:
        expected.update({'矿ˢ盐ᴵ': 'selenit', '微镜ˢᴷio': 'mikroskopio',
                         '两ᴴ性ᴬᶠ': 'hermafrodit', '同ᴴ名ᴺᴵ': 'homonim'})
    for body, original in expected.items():
        assert app.convert_kanji_esperanto_to_alphabet(body, idx) == original
    # Do not mechanically add eŭfoni: the forward app already leaves its i visible.
    assert app.convert_kanji_esperanto_to_alphabet('良ᴱ声ᶠᴼio', idx) == 'eŭfonio'
    base = records(source) + tuple((owner, key, '0') for key, owner in PREVIOUS[source].items())
    previous = index(base)
    protected = ['全o', '无o', '性ˢ学家', '切ᵀᴼ', '醇馏',
                 '囊室除ᴱᴷ', '戏法员ᴬᵀ', '内ᴱᴰ镜ˢᴷ',
                 '无ᴬ缩ˢio', '盐o 炎o 兄o 父o', 'k无o']
    if source == CURRENT:
        protected += ['两ᴴ', '名ᴺᴵ']
    for body in protected:
        assert app.convert_kanji_esperanto_to_alphabet(body, idx) == app.convert_kanji_esperanto_to_alphabet(body, previous)


@pytest.mark.parametrize('source', (CURRENT, OLD))
def test_every_new_alias_conflict_is_rejected_but_custom_ownership_wins(source):
    frame = app.load_dictionary_source(source)
    for key in NEW[source]:
        custom = pd.DataFrame([('uploaded', key, '-99')], columns=['esperanto', 'kanji', 'priority'])
        conflicting = pd.concat([frame, custom], ignore_index=True)
        with pytest.raises(ValueError, match='conflicts with an existing root'):
            app.effective_mapping_records(source, conflicting)
        rows = app.effective_mapping_records('custom', custom)
        assert rows == app.dataframe_to_mapping_records(custom)
        assert app.convert_kanji_esperanto_to_alphabet(key+'o', index(rows)) == 'uploadedo'


@pytest.mark.parametrize('edition', ('current', 'legacy'))
@pytest.mark.parametrize('mutation', ('duplicate', 'missing', 'wrong_owner', 'unapproved'))
def test_closed_manifest_rejects_every_kind_of_unreviewed_set(tmp_path, monkeypatch, edition, mutation):
    shutil.copytree(app.ROOT/'data', tmp_path/'data')
    path = tmp_path/'data'/f'{edition}_inverse_aliases.json'
    data = json.loads(path.read_bytes())
    if mutation == 'duplicate': data['aliases'].append(dict(data['aliases'][-1]))
    elif mutation == 'missing': data['aliases'].pop()
    elif mutation == 'wrong_owner': data['aliases'][-1]['esperanto'] = 'another'
    else: data['aliases'].append({'kanji': '醇馏', 'esperanto': 'alkoholat'})
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(app, 'ROOT', tmp_path)
    loader = app.load_current_inverse_aliases if edition == 'current' else app.load_legacy_inverse_aliases
    with pytest.raises(ValueError, match='inverse alias supplement'):
        loader()


@pytest.mark.parametrize('source', (CURRENT, OLD))
def test_effective_exports_are_exact_ui_records_and_fixed_exports_remain_fixed(source):
    export = app.current_effective_download_data if source == CURRENT else app.legacy_effective_download_data
    raw = export(source)
    custom = app.read_assignment_csv(io.BytesIO(raw))
    expected = app.effective_mapping_records(source, app.load_dictionary_source(source))
    assert app.dataframe_to_mapping_records(custom) == expected
    assert index(app.effective_mapping_records('custom', custom)) == index(expected)
    fixed, _ = app.edition_download_data(source)
    expected_sha = ('4718bbd7f5900ad7f5abc3434caa9381fb867b89f521bfe4031c1579a21e3074'
                    if source == CURRENT else 'eed2a8bfc21a97b719e40b703ca356a6b9cd37e772811bd6d62203cfc00c4c14')
    assert hashlib.sha256(fixed).hexdigest() == expected_sha
    meta = app.source_provenance(source)
    assert meta['inverse_compatibility_revision'] == ('current' if source == CURRENT else 'legacy')+'-unique-inverse-20261018-v2'
    for field in ('identity', 'label', 'result_filename', 'effective_dictionary_filename'):
        assert meta['inverse_compatibility_revision'] in meta[field]
        assert meta['inverse_compatibility_sha256'][:12] in meta[field]
