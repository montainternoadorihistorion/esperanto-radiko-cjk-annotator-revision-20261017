"""Two adopted bodies, immutable old edition, and identifier-owner controls."""
import hashlib, io, json
import pandas as pd
import pytest
import esperanto_converter_zh as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620'; OLD='pre-las-20261017'
CHANGES={'madz':('钉头锤','棍ᴹ'),'tribord':('右边','船右')}
CONTROLS={'棍':'klab','船左':'babord','程ᴾᶜ':'proces','程ᴾᶻ':'procez'}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_endings_and_control_owners(source):
    mapping=index(source)
    for root,pair in CHANGES.items():
        body=pair[source==CURRENT]
        for suffix in SUFFIXES:
            for ending in (suffix,suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
            for keep,owner in CONTROLS.items():
                assert app.convert_kanji_esperanto_to_alphabet(keep+suffix,mapping)==owner+suffix
        assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  '+root+'o\n\t'+root+'as & <x>  '

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_longer_identifier_boundaries(source):
    mapping=index(source);flat={key:owner for bucket in mapping.by_length.values() for key,owner in bucket.items()}
    for root,pair in CHANGES.items():
        body=pair[source==CURRENT]
        for continuation in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
            key=body+continuation;actual=app.convert_kanji_esperanto_to_alphabet(key+'o',mapping)
            if key in flat:assert actual==flat[key]+'o'
            else:assert not actual.startswith(root),(key,actual)
    assert app.convert_kanji_esperanto_to_alphabet('棍ᴹo',mapping)==('madzo' if source==CURRENT else '棍ᴹo')

def test_only_two_visible_editions_and_no_old_aliases():
    assert app.dictionary_options()==[CURRENT,OLD] and len(app.DICTIONARY_SOURCES)==8
    records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
    for root,(old,new) in CHANGES.items():
        assert not [r for r in records if r[1]==old]
        assert {r[0] for r in records if r[1]==new}=={root}
        assert old not in app.CURRENT_INVERSE_ALIAS_PAIRS

def test_manifest_and_downloads():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    path=app.ROOT/source['madz_tribord_manifest'];manifest=json.loads(path.read_bytes())
    assert source['revision']=='2026-10-29-fuz'
    assert manifest['revision']=='2026-10-25-madz-tribord'
    assert manifest['changes']=={root:list(pair) for root,pair in CHANGES.items()}
    assert manifest['safe_reverse_aliases']==manifest['ownership_transfers']=={}
    assert manifest['documentation_only_changes']=={'klab':{'group_count':[1,2]}}
    assert manifest['assignment_unchanged_item_count']==10638
    assert manifest['current_item_count']==manifest['baseline_item_count']==10640
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['madz_tribord_manifest_sha256']
    for pair in CHANGES.values():
        for body in pair:assert body not in source['reverse_only_aliases']
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy,legacy_two=app.edition_download_data(OLD)
    assert hashlib.sha256(legacy).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(legacy_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_standard_html_and_protected_text(edition,mode):
    def ruby(root,annotation):
        body=CHANGES[root][edition=='current']
        return f'<ruby>{body}<rt>{root}</rt></ruby>' if mode=='kanji' else f'<ruby>{root}<rt>{annotation}</rt></ruby>'
    content='  '+ruby('madz','金属頭を持つ棍棒・儀杖')+'o '+ruby('tribord','船首を向いたときの右舷')+'o<br>\n\t&lt;保護&gt; &amp;  '
    html=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-10-25T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='  madzo tribordo\n\t<保護> &  ' and result['assignment_edition']==edition

def test_custom_dictionary_stays_custom():
    frame=pd.DataFrame([('custom','棍ᴹ','0')],columns=['esperanto','kanji','priority'])
    records=app.effective_mapping_records('custom',frame)
    assert records==app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet('棍ᴹo',app.build_mapping_index_cached(records))=='customo'
