"""Four approved assignments, fixed legacy, complete identifiers and shared text."""
import csv,hashlib,io,json
import pandas as pd
import pytest
import esperanto_converter as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620';OLD='pre-las-20261017'
CHANGES={'almenaŭ':('至ᴬ','至少'),'forniks':('脑弓','拱ᶠ'),'karen':('龙骨ᴷᴿ','船底'),'naŭz':('呕','恶心')}
GROUP_COUNTS={'ĝis':[3,2],'solstic':[3,2],'kil':[2,1],'volb':[1,2]}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')
CONTROLS={'至':'ĝis','至ˢ':'solstic','拱':'volb','龙骨':'kil','吐':'vom','鲨皮':'ŝagrin','裁ˢ':'sankci','思':'pens','宿':'pension'}

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_four_roots_all_endings_and_preserved_neighbours(source):
    mapping=index(source)
    for root,pair in CHANGES.items():
        body=pair[source==CURRENT]
        for suffix in SUFFIXES:
            for ending in (suffix,suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
    for body,root in CONTROLS.items():
        if body=='裁ˢ' and source==OLD:continue
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+suffix

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_complete_identifiers_and_preserved_spacing(source):
    mapping=index(source)
    for prefix,roots in [('拱ᶠ',('forniks','volb')),('至ᴬ',('almenaŭ','ĝis')),('龙骨ᴷᴿ',('karen','kil'))]:
        for char in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
            text=prefix+char+'o';actual=app.convert_kanji_esperanto_to_alphabet(text,mapping)
            assert not actual.startswith(roots),(text,actual)
    body='拱ᶠ' if source==CURRENT else '脑弓'
    assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  fornikso\n\tforniksas & <x>  '

def test_no_intermediate_profile_or_new_old_spelling_aliases():
    assert app.dictionary_options()==[CURRENT,OLD] and len(app.DICTIONARY_SOURCES)==8
    provenance=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
    for root,(old,new) in CHANGES.items():
        assert not [r for r in records if r[1]==old]
        assert {r[0] for r in records if r[1]==new}=={root}
        assert old not in provenance['reverse_only_aliases'] and new not in provenance['reverse_only_aliases']
        assert old not in app.CURRENT_INVERSE_ALIAS_PAIRS and new not in app.CURRENT_INVERSE_ALIAS_PAIRS
        assert app.convert_kanji_esperanto_to_alphabet(old+'o',index(OLD))==root+'o'

def test_current_manifest_downloads_and_group_descriptions():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    path=app.ROOT/source['four_assignments_manifest'];manifest=json.loads(path.read_bytes())
    assert source['revision']=='2026-10-25-madz-tribord'
    assert manifest['revision']=='2026-10-25-four-assignments'
    assert manifest['changes']=={r:list(v) for r,v in CHANGES.items()}
    assert manifest['safe_reverse_aliases']==manifest['ownership_transfers']=={}
    assert manifest['documentation_only_changes']=={r:{'group_count':v} for r,v in GROUP_COUNTS.items()}
    assert manifest['current_item_count']==manifest['baseline_item_count']==10640
    assert manifest['assignment_unchanged_item_count']==10636 and manifest['unrelated_items_count']==10632
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['four_assignments_manifest_sha256']
    monaco=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
    for root,(_,count) in GROUP_COUNTS.items():
        row=next(r for r in monaco['items'] if r['sourceRoot']==root)
        assert f'\nグループ数: {count}\n' in row['documentation']
    assert next(r for r in monaco['items'] if r['sourceRoot']=='s^agrin')['body']=='鲨皮'
    rows=list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding='utf-8'))));assert len(rows)==10678
    for root,(_,new) in CHANGES.items():assert [r['kanji'] for r in rows if r['source_root']==root]==[new]
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy,legacy_two=app.edition_download_data(OLD)
    assert hashlib.sha256(legacy).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(legacy_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

def test_exact_new_whole_keys_take_priority_over_compositional_reading():
    # One shared surface cannot distinguish both originals; no segmentation is changed.
    for body,old_reading,new_reading in [('船底','ŝipfund','karen'),('恶心','malickor','naŭz')]:
        for suffix in ('','o','a','i','as','ojn'):
            assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(OLD))==old_reading+suffix
            assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==new_reading+suffix

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_standard_html_keeps_original_spelling_gloss_and_protected_text(edition,mode):
    annotation={'almenaŭ':'少なくとも','forniks':'円蓋・脳弓・結膜円蓋','karen':'船底・竜骨突起・舟弁','naŭz':'吐き気・嫌悪を起こす'}
    pieces=[]
    for root,pair in CHANGES.items():
        body=pair[edition=='current'];suffix='' if root=='almenaŭ' else 'o'
        pieces.append((f'<ruby>{body}<rt>{root}</rt></ruby>' if mode=='kanji' else f'<ruby>{root}<rt>{annotation[root]}</rt></ruby>')+suffix)
    content='  '+' '.join(pieces)+'<br>\n\tŝagrino &lt;保護&gt; &amp;  '
    source=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-10-25T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result=recover_standard_html(source,mode)
    assert result['text']=='  almenaŭ fornikso kareno naŭzo\n\tŝagrino <保護> &  '
    assert result['assignment_edition']==edition and result['ruby_count']==4

def test_custom_assignment_is_not_replaced_by_bundled_profile():
    frame=pd.DataFrame([('custom','拱ᶠ','0')],columns=['esperanto','kanji','priority'])
    records=app.effective_mapping_records('custom',frame)
    assert records==app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet('拱ᶠo',app.build_mapping_index_cached(records))=='customo'
