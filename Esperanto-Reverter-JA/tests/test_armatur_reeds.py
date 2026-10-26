"""Approved framework/reed changes; fixed legacy and identifier ownership."""
import csv,hashlib,io,json
import pandas as pd
import pytest
import esperanto_converter as app
from html_source_recovery import recover_standard_html

CURRENT='pejvo-piv-20260620';OLD='pre-las-20261017'
CHANGES={'armatur':('配筋','骨架'),'arund':('草ᴬᴰ','苇ᴬ'),'donak':('草ᴰᴷ','苇ᴰ'),'androzac':('草ᴬᶜ','草ᴬᴰ'),'armoraci':('草ᴬᴿᴹ','草ᴬᶜ'),'diktamn':('草ᴰᵀ','草ᴰᴷ')}
SUFFIXES=('', 'o','oj','on','ojn','a','aj','an','ajn','e','i','as','is','os','us','u','ado','ita','intajn','igi','ĉjo')
CONTROLS={'暴躁':'brusk','云杉':'pice','躁':'nervoz','苇':'kan','苇ᶠ':'fragmit'}

def index(source):
    return app.build_mapping_index_cached(app.effective_mapping_records(source,app.load_dictionary_source(source)))

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_six_roots_all_endings_and_preserved_neighbours(source):
    mapping=index(source)
    for root,pair in CHANGES.items():
        body=pair[source==CURRENT]
        for suffix in SUFFIXES:
            for ending in (suffix,suffix.upper()):
                assert app.convert_kanji_esperanto_to_alphabet(body+ending,mapping)==root+suffix
    for body,root in CONTROLS.items():
        for suffix in SUFFIXES:
            assert app.convert_kanji_esperanto_to_alphabet(body+suffix,mapping)==root+suffix

@pytest.mark.parametrize('source',(CURRENT,OLD))
def test_complete_identifiers_and_preserved_spacing(source):
    mapping=index(source)
    flat={key:owner for bucket in mapping.by_length.values() for key,owner in bucket.items()}
    for root,pair in CHANGES.items():
        body=pair[source==CURRENT]
        if not body.startswith(('草','苇')):continue
        for char in sorted(app._IDENTIFIER_CONTINUATION_CHARS):
            key=body+char;text=key+'o';actual=app.convert_kanji_esperanto_to_alphabet(text,mapping)
            if key in flat:assert actual==flat[key]+'o'
            else:assert not actual.startswith(root),(text,actual)
    body='苇ᴬ' if source==CURRENT else '草ᴬᴰ'
    assert app.convert_kanji_esperanto_to_alphabet('  '+body+'o\n\t'+body+'as & <x>  ',mapping)=='  arundo\n\tarundas & <x>  '

def test_no_intermediate_profile_or_ambiguous_old_spelling_aliases():
    assert app.dictionary_options()==[CURRENT,OLD] and len(app.DICTIONARY_SOURCES)==8
    provenance=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    records=app.effective_mapping_records(CURRENT,app.load_dictionary_source(CURRENT))
    new_bodies={pair[1] for pair in CHANGES.values()}
    for root,(old,new) in CHANGES.items():
        if old not in new_bodies:assert not [r for r in records if r[1]==old]
        assert {r[0] for r in records if r[1]==new}=={root}
        assert old not in provenance['reverse_only_aliases'] and new not in provenance['reverse_only_aliases']
        assert old not in app.CURRENT_INVERSE_ALIAS_PAIRS and new not in app.CURRENT_INVERSE_ALIAS_PAIRS
        assert app.convert_kanji_esperanto_to_alphabet(old+'o',index(OLD))==root+'o'
    for body,old_owner,new_owner in [('草ᴬᴰ','arund','androzac'),('草ᴬᶜ','androzac','armoraci'),('草ᴰᴷ','donak','diktamn')]:
        assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(OLD))==old_owner+'o'
        assert app.convert_kanji_esperanto_to_alphabet(body+'o',index(CURRENT))==new_owner+'o'

def test_current_manifest_downloads_and_group_descriptions():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    path=app.ROOT/source['armatur_reeds_manifest'];manifest=json.loads(path.read_bytes())
    assert source['revision']=='2026-10-26-klarion'
    assert manifest['revision']=='2026-10-25-armatur-reeds'
    assert manifest['changes']=={r:list(v) for r,v in CHANGES.items()}
    assert manifest['safe_reverse_aliases']=={}
    assert manifest['ownership_transfers']=={'草ᴬᴰ':['arund','androzac'],'草ᴬᶜ':['androzac','armoraci'],'草ᴰᴷ':['donak','diktamn']}
    assert manifest['user_adopted_roots']==['armatur','arund','donak']
    assert manifest['identifier_propagated_roots']==['androzac','armoraci','diktamn']
    assert manifest['current_item_count']==manifest['baseline_item_count']==10640
    assert manifest['assignment_unchanged_item_count']==10634
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['armatur_reeds_manifest_sha256']
    monaco=json.loads((app.ROOT/'data/monaco_source_20261017.json').read_bytes())
    items={row['sourceRoot']:row for row in monaco['items']}
    for root,doc in manifest['documentation_only_changes'].items():
        body=manifest['expected_target_items'][root]['body']
        row=next(row for row in monaco['items'] if row['sourceRoot']==root and row['body']==body)
        assert f"\nグループ数: {doc['group_count'][1]}\n" in row['documentation']
    for body,root in CONTROLS.items():assert items[root]['body']==body
    rows=list(csv.DictReader(io.StringIO(app.PEJVO_PIV_20260620_CSV.read_text(encoding='utf-8'))));assert len(rows)==10678
    for root,(_,new) in CHANGES.items():assert [r['kanji'] for r in rows if r['source_root']==root]==[new]
    full,two=app.edition_download_data(CURRENT)
    assert hashlib.sha256(full).hexdigest()==source['current_csv_sha256']
    assert hashlib.sha256(two).hexdigest()==source['current_snippet_csv_sha256']
    assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(two)))
    legacy,legacy_two=app.edition_download_data(OLD)
    assert hashlib.sha256(legacy).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
    assert hashlib.sha256(legacy_two).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']

def test_shared_composition_is_not_falsely_claimed_unique():
    # The new whole-root key takes priority over ost+rak; source segmentation is unchanged.
    for suffix in SUFFIXES:
        assert app.convert_kanji_esperanto_to_alphabet('骨架'+suffix,index(OLD))=='ostrak'+suffix
        assert app.convert_kanji_esperanto_to_alphabet('骨架'+suffix,index(CURRENT))=='armatur'+suffix

@pytest.mark.parametrize('edition',('current','legacy'))
@pytest.mark.parametrize('mode',('kanji','annotation'))
def test_standard_html_keeps_original_spelling_meanings_and_protected_text(edition,mode):
    annotations={'armatur':'骨組み・補強部材・接極子・極板','arund':'ダンチク属','donak':'ダンチク','androzac':'トチナイソウ属','armoraci':'セイヨウワサビ','diktamn':'ハクセン属'}
    pieces=[]
    for root,pair in CHANGES.items():
        body=pair[edition=='current']
        pieces.append((f'<ruby>{body}<rt>{root}</rt></ruby>' if mode=='kanji' else f'<ruby>{root}<rt>{annotations[root]}</rt></ruby>')+'o')
    content='  '+' '.join(pieces)+'<br>\n\tbruska piceo nervoza &lt;保護&gt; &amp;  '
    source=f'<!-- assignment-edition:{edition} signature:abcdef created-utc:2026-10-25T12:00:00Z -->\n<!DOCTYPE html>\n<html lang="ja"><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n{content}</p></body></html>'
    result=recover_standard_html(source,mode)
    assert result['text']=='  '+' '.join(r+'o' for r in CHANGES)+'\n\tbruska piceo nervoza <保護> &  '
    assert result['assignment_edition']==edition and result['ruby_count']==6

def test_custom_assignment_is_not_replaced_by_bundled_profile():
    frame=pd.DataFrame([('custom','草ᴬᴰ','0')],columns=['esperanto','kanji','priority'])
    records=app.effective_mapping_records('custom',frame)
    assert records==app.dataframe_to_mapping_records(frame)
    assert app.convert_kanji_esperanto_to_alphabet('草ᴬᴰo',app.build_mapping_index_cached(records))=='customo'
