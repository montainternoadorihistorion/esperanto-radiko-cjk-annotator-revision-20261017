"""Approved three-root migration; fixed legacy, identifiers and HTML source kept distinct."""
import csv,hashlib,io,json
import pandas as pd
import pytest
import esperanto_converter_zh as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620';OLD='pre-las-20261017'
CHANGES={'ŝtip':('圆木','木块'),'pensi':('养老','年金'),'sankci':('制裁','裁ˢ')}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')
CONTROLS={'裁':'tajl','裁ᵀᴿ':'tajlor','裁ᴬ':'arbitraci','思':'pens','宿':'pension','忧ᴬᴷ':'anksi'}

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))

@pytest.mark.parametrize('source', (CURRENT,OLD))
def test_roots_all_endings_and_preserved_neighbours(source):
    mapping=index(source)
    for root,bodies in CHANGES.items():
        body=bodies[source==CURRENT]
        for suffix in SUFFIXES:
            for ending in (suffix,suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
    controls={k:v for k,v in CONTROLS.items() if source==CURRENT or k!='忧ᴬᴷ'}
    for body,root in controls.items():
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('思i 养老o 宿o' if source==OLD else '思i 年金o 宿o',mapping)=='pensi pensio pensiono'

@pytest.mark.parametrize('source', (CURRENT,OLD))
def test_complete_identifier_boundary_and_plain_whitespace(source):
    mapping=index(source)
    for char in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
        text='裁ˢ'+char+'o';actual=app.convert_kanji_esperanto_to_alphabet(text,mapping)
        assert not actual.startswith(('sankci','tajl')),(text,actual)
    body='裁ˢ' if source==CURRENT else '制裁'
    assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  sankcio\n\tsankcias & <x>  '

def test_current_and_legacy_are_explicit_no_new_intermediate_aliases():
    assert app.dictionary_options()==[CURRENT,OLD] and len(app.DICTIONARY_SOURCES)==8
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
    for root,(old,new) in CHANGES.items():
        assert not [r for r in records if r[1]==old]
        assert {r[0] for r in records if r[1]==new}=={root}
        assert old not in source['reverse_only_aliases'] and new not in source['reverse_only_aliases']
        assert old not in app.CURRENT_INVERSE_ALIAS_PAIRS and new not in app.CURRENT_INVERSE_ALIAS_PAIRS
        assert app.convert_kanji_esperanto_to_alphabet(old+'o',index(OLD))==root+'o'

def test_source_manifest_downloads_and_group_descriptions():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    path=app.ROOT/source['shtip_pensi_sankci_manifest'];manifest=json.loads(path.read_bytes())
    assert source['revision']=='2026-10-25-armatur-reeds'
    assert manifest['revision']=='2026-10-24-shtip-pensi-sankci'
    assert manifest['changes']=={r:list(v) for r,v in CHANGES.items()}
    assert manifest['safe_reverse_aliases']==manifest['ownership_transfers']=={}
    assert manifest['documentation_only_changes']=={r:{'group_count':[3,4]} for r in ('tajl','tajlor','arbitraci')}
    assert manifest['current_item_count']==manifest['baseline_item_count']==10640
    assert manifest['assignment_unchanged_item_count']==10637 and manifest['unrelated_items_count']==10634
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['shtip_pensi_sankci_manifest_sha256']
    monaco=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
    for root in ('tajl','tajlor','arbitraci','sankci'):
        row=next(r for r in monaco['items'] if r['sourceRoot']==root)
        assert '\nグループ数: 4\n' in row['documentation']
    rows=list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding='utf-8'))));assert len(rows)==10678
    for root,(old,new) in CHANGES.items():assert [r['kanji'] for r in rows if r['source_root']==root]==[new]
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    old,old_two=app.edition_download_data(OLD)
    assert hashlib.sha256(old).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(old_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_standard_html_keeps_explicit_roots_glosses_and_protected_characters(edition,mode):
    annotation={'ŝtip':'木塊・丸太・薪','pensi':'定期的に支給する年金','sankci':'裁可・承認する；処罰・制裁する'}
    pieces=[]
    for root,bodies in CHANGES.items():
        body=bodies[edition=='current']
        pieces.append(f'<ruby>{body}<rt>{root}</rt></ruby>o' if mode=='kanji' else f'<ruby>{root}<rt>{annotation[root]}</rt></ruby>o')
    content='  '+' '.join(pieces)+'<br>\n\tŝtipo &lt;保護&gt; &amp;  '
    source=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-10-24T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result=recover_standard_html(source,mode)
    assert result['text']=='  ŝtipo pensio sankcio\n\tŝtipo <保護> &  '
    assert result['assignment_edition']==edition and result['ruby_count']==3

def test_custom_mapping_not_reassigned_by_current_profile():
    frame=pd.DataFrame([('custom','裁ˢ','0')],columns=['esperanto','kanji','priority'])
    records=app.effective_mapping_records('custom',frame)
    assert records==app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet('裁ˢo',app.build_mapping_index_cached(records))=='customo'
