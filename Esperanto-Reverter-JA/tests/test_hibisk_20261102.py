"""Hibisk representative character, existing owners and immutable legacy."""
import hashlib
import io
import json
import pandas as pd
import pytest
import esperanto_converter as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'
OLD='pre-las-20261017'
CHANGES={'hibisk':('芙蓉','芙')}
CONTROLS={'快':'agrabl','快ᴬᴸ':'alegr','伪':'fals','伪ᴾ':'pseŭdo','残船':'vrak','册ᴱ':'ekzempler'}
PRIOR_ADOPTIONS={'eŭfori':('欣快','快ᴱ'),'sofism':('诡辩','伪辩')}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_hibisk_and_prior_adoptions_with_endings(source):
    mapping=index(source)
    selected={pair[source==CURRENT]:root for root,pair in (CHANGES|PRIOR_ADOPTIONS).items()}
    for body,root in (selected|CONTROLS).items():
        for suffix in SUFFIXES:
            for ending in (suffix,suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
        assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  '+root+'o\n\t'+root+'as & <x>  '

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_unknown_long_identifier_is_not_partially_consumed(source):
    mapping=index(source)
    flat={key:owner for bucket in mapping.by_length.values() for key,owner in bucket.items()}
    body=CHANGES['hibisk'][source==CURRENT]
    for continuation in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
        key=body+continuation
        actual=app.convert_kanji_esperanto_to_alphabet(key+'o',mapping)
        if key in flat:assert actual==flat[key]+'o'
        else:assert not actual.startswith('hibisk'),(key,actual)
    if source==CURRENT:
        assert app.convert_kanji_esperanto_to_alphabet('芙o 芙ᴬo 快ᴱo 快ᴱᴬo',mapping)=='hibisko 芙ᴬo eŭforio 快ᴱᴬo'

def test_exactly_two_visible_editions_and_no_intermediate_alias():
    assert app.dictionary_options()==[CURRENT,OLD]
    assert len(app.DICTIONARY_SOURCES)==8
    records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
    assert not [r for r in records if r[1]=='芙蓉']
    assert {r[0] for r in records if r[1]=='芙'}=={'hibisk'}
    assert '芙' not in app.CURRENT_INVERSE_ALIAS_PAIRS
    assert '芙蓉' not in app.CURRENT_INVERSE_ALIAS_PAIRS

def test_current_manifest_and_downloads_preserve_frozen_edition():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    path=app.ROOT/source['hibisk_20261102_manifest']
    manifest=json.loads(path.read_bytes())
    assert source['revision']==manifest['revision']=='2026-11-02-hibisk'
    assert manifest['changes']=={'hibisk':['芙蓉','芙']}
    assert manifest['safe_reverse_aliases']=={}
    assert manifest['user_adopted_roots']==['hibisk']
    assert manifest['identifier_propagated_roots']==[]
    assert manifest['documentation_only_changes']==manifest['metadata_only_changes']=={}
    assert manifest['assignment_unchanged_item_count']==10639
    assert manifest['current_item_count']==manifest['baseline_item_count']==10640
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['hibisk_20261102_manifest_sha256']
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy,legacy_two=app.edition_download_data(OLD)
    assert hashlib.sha256(legacy).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(legacy_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_standard_html_original_spaces_and_protected_characters(edition,mode):
    body=CHANGES['hibisk'][edition=='current']
    ruby=f'<ruby>{body}<rt>hibisk</rt></ruby>' if mode=='kanji' else '<ruby>hibisk<rt>ハイビスカス</rt></ruby>'
    content='  '+ruby+'o<br>\n\t&lt;保護&gt; &amp;  '
    html=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-11-02T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='  hibisko\n\t<保護> &  '
    assert result['assignment_edition']==edition

def test_custom_dictionary_keeps_its_selected_owner():
    frame=pd.DataFrame([('custom','芙','0')],columns=['esperanto','kanji','priority'])
    records=app.effective_mapping_records('custom',frame)
    assert records==app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet('芙o',app.build_mapping_index_cached(records))=='customo'
