"""Approved spekulativ root: current/legacy, old-key compatibility and identifier limits."""
import hashlib
import json

import pandas as pd
import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json

CURRENT='pejvo-piv-20260620'
LEGACY='pre-las-20261017'
CHANGES={'spekulativ':('猜ˢ','思辨')}
SUFFIXES=('', 'o', 'ojn', 'a', 'aj', 'i', 'as', 'is', 'os', 'us', 'u', 'igi', 'ita')

def index(edition):
    return app.build_mapping_index_cached(app.effective_mapping_records(edition,app.load_dictionary_source(edition)))

@pytest.mark.parametrize('root',CHANGES)
@pytest.mark.parametrize('suffix',SUFFIXES)
def test_current_both_spellings_and_fixed_legacy(root,suffix):
    old,new=CHANGES[root]
    current=index(CURRENT);legacy=index(LEGACY)
    assert app.convert_kanji_esperanto_to_alphabet(old+suffix,current)==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet(new+suffix,current)==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet(old+suffix,legacy)==root+suffix
    legacy_keys={k for bucket in legacy.by_length.values() for k in bucket}
    assert new not in legacy_keys

def test_identifier_boundaries_preserve_longer_owner():
    idx=index(CURRENT)
    flat={k:v for bucket in idx.by_length.values() for k,v in bucket.items()}
    for root,(old,new) in CHANGES.items():
        for body in (old,new):
            for continuation in app._IDENTIFIER_CONTINUATION_CHARS:
                key=body+continuation
                actual=app.convert_kanji_esperanto_to_alphabet(key+'o',idx)
                if key in flat:assert actual==flat[key]+'o'
                else:assert not actual.startswith(root),(key,actual)
    assert app.convert_kanji_esperanto_to_alphabet('猜o 猜ᴷo',idx)=='diveno konjekto'
    assert app.convert_kanji_esperanto_to_alphabet('思辨a 猜ˢa',idx)=='spekulativa spekulativa'

def test_download_and_source_have_new_forward_and_previous_reverse_keys():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    manifest=json.loads((app.ROOT/'data/spekulativ_20261108.json').read_bytes())
    data=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
    assert source['revision']==manifest['revision']=='spekulativ-20261108'
    assert source['current_csv_count']==10683
    assert manifest['safe_reverse_aliases']=={old:root for root,(old,new) in CHANGES.items()}
    assert app.dictionary_options()==[CURRENT,LEGACY]
    records=rows_from_all_json(data)
    assert len(records)==10683
    for root,(old,new) in CHANGES.items():
        assert [r['body'] for r in data['items'] if r['sourceRoot']==root]==[new]
        assert sorted(r['kanji'] for r in records if r['source_root']==root)==sorted([old,new])
        assert source['reverse_only_aliases'][old]==root
    assert hashlib.sha256(app.PEJVO_PIV_20260620_CSV.read_bytes()).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256((app.ROOT/'エスペラント語根-漢字対応表_スニペット用最小限.csv').read_bytes()).hexdigest()==source['current_snippet_csv_sha256']

@pytest.mark.parametrize('root',CHANGES)
def test_generator_is_conditional_normalized_and_conflict_safe(root):
    old,new=CHANGES[root]
    assert [r['kanji'] for r in rows_from_all_json({'items':[{'sourceRoot':root,'body':old}]})]==[old]
    assert [r['kanji'] for r in rows_from_all_json({'items':[{'sourceRoot':root,'body':'custom'}]})]==['custom']
    assert sorted(r['kanji'] for r in rows_from_all_json({'items':[{'sourceRoot':' '+root+' ','body':' '+new+' '}]}))==sorted([old,new])
    for old_body in (old,' '+old+' '):
        with pytest.raises(ValueError,match='conflicts'):
            rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':'other','body':old_body}]})
    with pytest.raises(ValueError,match='Expected one'):
        rows_from_all_json({'items':[{'sourceRoot':root,'body':new},{'sourceRoot':root,'body':' '+new+' '}]})
    # Empty-root/empty-body rows retain the pre-existing skip behavior.
    assert rows_from_all_json({'items':[{'sourceRoot':root,'body':''}]})==[]
    assert [r['esperanto'] for r in rows_from_all_json({'items':[{'body':new},{'sourceRoot':'other','body':old}]})]==['other']
    frame=pd.DataFrame([('customroot',new,'0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',frame)==app.dataframe_to_mapping_records(frame)
    custom=app.build_mapping_index_cached(app.effective_mapping_records('custom',frame))
    assert app.convert_kanji_esperanto_to_alphabet(new+'o',custom)=='customrooto'
    assert app.convert_kanji_esperanto_to_alphabet(old+'o',custom)==old+'o'
