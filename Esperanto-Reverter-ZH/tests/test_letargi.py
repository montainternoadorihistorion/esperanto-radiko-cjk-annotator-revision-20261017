"""Approved letargi body, fixed legacy, retained emerit family and shared spelling."""
import hashlib, io, json
import pandas as pd
import pytest
import esperanto_converter_zh as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'; OLD='pre-las-20261017'
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source, app.load_dictionary_source(source)))

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_all_endings_and_retained_emerit_family(source):
    mapping=index(source); body='昏睡' if source==CURRENT else '嗜睡'
    for suffix in SUFFIXES:
        for ending in (suffix,suffix.upper()):
            assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)=='letargi'+suffix
        for keep,root in {'退':'emerit','退休金':'emeritur','昏':'sven','睡':'dorm'}.items():
            assert app.convert_kanji_esperanto_to_alphabet(keep+suffix,mapping)==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  letargio\n\tletargias & <x>  '

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_no_partial_matching_inside_longer_identifiers(source):
    mapping=index(source); body='昏睡' if source==CURRENT else '嗜睡'
    flat={key:owner for bucket in mapping.by_length.values() for key,owner in bucket.items()}
    for continuation in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
        key=body+continuation; actual=app.convert_kanji_esperanto_to_alphabet(key+'o',mapping)
        if key in flat: assert actual==flat[key]+'o'
        else: assert not actual.startswith('letargi'), (key,actual)

def test_shared_composition_and_two_editions():
    assert app.dictionary_options()==[CURRENT,OLD] and len(app.DICTIONARY_SOURCES)==8
    for suffix in SUFFIXES:
        assert app.convert_kanji_esperanto_to_alphabet('昏睡'+suffix,index(OLD))=='svendorm'+suffix
        assert app.convert_kanji_esperanto_to_alphabet('昏睡'+suffix,index(CURRENT))=='letargi'+suffix
    records=app.effective_mapping_records(CURRENT, app.load_dictionary_source(CURRENT))
    assert not [r for r in records if r[1]=='嗜睡']
    assert {r[0] for r in records if r[1]=='昏睡'}=={'letargi'}
    assert '嗜睡' not in app.CURRENT_INVERSE_ALIAS_PAIRS

def test_source_manifest_downloads():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    path=app.ROOT/source['letargi_manifest']; manifest=json.loads(path.read_bytes())
    assert source['revision']=='2026-10-31-ligatur'
    assert manifest['revision']=='2026-10-25-letargi'
    assert manifest['changes']=={'letargi':['嗜睡','昏睡']}
    assert manifest['safe_reverse_aliases']==manifest['ownership_transfers']=={}
    assert manifest['assignment_unchanged_item_count']==10639
    assert manifest['current_item_count']==manifest['baseline_item_count']==10640
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['letargi_manifest_sha256']
    for body in ('昏睡','嗜睡'): assert body not in source['reverse_only_aliases']
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy,legacy_two=app.edition_download_data(OLD)
    assert hashlib.sha256(legacy).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(legacy_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_html_preserves_meaning_and_original_including_shared_surface(edition,mode):
    body='昏睡' if edition=='current' else '嗜睡'
    ruby=f'<ruby>{body}<rt>letargi</rt></ruby>' if mode=='kanji' else '<ruby>letargi<rt>昏睡状態・無気力・無感動</rt></ruby>'
    content='  '+ruby+'o <ruby>昏<rt>sven</rt></ruby><ruby>睡<rt>dorm</rt></ruby>o<br>\n\t&lt;保護&gt; &amp;  '
    if mode=='annotation': content=content.replace('<ruby>昏<rt>sven</rt></ruby><ruby>睡<rt>dorm</rt></ruby>', '<ruby>sven<rt>気絶</rt></ruby><ruby>dorm<rt>眠る</rt></ruby>')
    html=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-10-25T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='  letargio svendormo\n\t<保護> &  '
    assert result['assignment_edition']==edition

def test_custom_dictionary_is_unchanged():
    frame=pd.DataFrame([('custom','昏睡','0')], columns=['esperanto','kanji','priority'])
    records=app.effective_mapping_records('custom',frame)
    assert records==app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet('昏睡o',app.build_mapping_index_cached(records))=='customo'
