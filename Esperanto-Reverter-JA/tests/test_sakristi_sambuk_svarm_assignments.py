"""Adopted room/plant/swarm displays, safe old keys and fixed legacy."""
import json
import pandas as pd
import pytest
import esperanto_converter as app
from tools.build_reverter_dictionary_from_all_json import rows_from_all_json
from html_source_recovery import recover_standard_html
CURRENT='pejvo-piv-20260620';LEGACY='pre-las-20261017'
CHANGES=[('sakristi','圣器室','圣器'),('sambuk','接骨木','接骨'),('svarm','群ˢ','拥')]
SUFFIXES=('', 'o','on','oj','ojn','a','aj','ajn','e','i','as','is','os','us','u','igi','ant','ita')
SHARED=[('凯','triumf'),('群','ar'),('群ᴳ','greg'),('群ᴴ','hord'),('圣','sankt'),('器','uj'),('室','ĉambr'),('木','lign')]
def records(edition):return app.effective_mapping_records(edition,app.load_dictionary_source(edition))
def index(edition):return app.build_mapping_index_cached(records(edition))

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_current_new_safe_old_and_shared_owners(suffix):
    pairs=SHARED+[(body,root) for root,new,old in CHANGES for body in (new,old)]
    for body,root in pairs:assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(CURRENT))==root+suffix

@pytest.mark.parametrize('suffix',SUFFIXES)
def test_legacy_original_keys_shared_owners_and_compound_reading(suffix):
    for body,root in SHARED+[(old,root) for root,new,old in CHANGES]:
        assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index(LEGACY))==root+suffix
    assert app.convert_kanji_esperanto_to_alphabet('群ˢ'+suffix,index(LEGACY))=='群ˢ'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('圣器室'+suffix,index(LEGACY))=='sakristiĉambr'+suffix
    assert app.convert_kanji_esperanto_to_alphabet('接骨木'+suffix,index(LEGACY))=='sambuklign'+suffix

def test_unknown_long_identifier_does_not_newly_match_shorter_key():
    newrecords=records(CURRENT)
    newbodies={new for _,new,_ in CHANGES}
    previous=app.build_mapping_index_cached(tuple(r for r in newrecords if r[1] not in newbodies))
    current=index(CURRENT);flat={k:v for bucket in current.by_length.values() for k,v in bucket.items()}
    for body in newbodies|{'圣器','接骨','拥','群','群ᴳ','群ᴴ'}:
        for tail in app._IDENTIFIER_CONTINUATION_CHARS:
            key=body+tail;text=key+'o'
            expected=flat[key]+'o' if key in flat else app.convert_kanji_esperanto_to_alphabet(text,previous)
            assert app.convert_kanji_esperanto_to_alphabet(text,current)==expected
    assert app.convert_kanji_esperanto_to_alphabet('群ˢᴿo',current)=='群ˢᴿo'

@pytest.mark.parametrize('root,new,old',CHANGES)
def test_generator_adds_only_approved_safe_old_key(root,new,old):
    rows=lambda xs:rows_from_all_json({'items':xs})
    item=lambda body,owner=root:dict(body=body,sourceRoot=owner)
    assert [r['kanji'] for r in rows([item(old)])]==[old]
    assert [r['kanji'] for r in rows([item('custom')])]==['custom']
    assert {r['kanji'] for r in rows([item(new)])}=={old,new}
    assert len(rows([item(new),item(old)]))==2
    with pytest.raises(ValueError,match='conflicts'):rows([item(new),item(old,'other')])
    with pytest.raises(ValueError,match='Expected one'):rows([item(new),item(new)])

def test_custom_dictionary_owns_its_mappings():
    df=pd.DataFrame([('own','圣器室','0'),('other','圣器','0'),('plant','接骨木','0'),('swarm','群ˢ','0')],columns=['esperanto','kanji','priority'])
    assert app.effective_mapping_records('custom',df)==app.dataframe_to_mapping_records(df)
    idx=app.build_mapping_index_cached(app.effective_mapping_records('custom',df))
    assert app.convert_kanji_esperanto_to_alphabet('圣器室o 圣器o 接骨木o 群ˢo',idx)=='owno othero planto swarmo'

@pytest.mark.parametrize('edition',['current','legacy'])
@pytest.mark.parametrize('mode',['kanji','annotation'])
def test_html_preserves_root_source_spaces_and_protected_text(edition,mode):
    pairs=[(root,new if edition=='current' else old) for root,new,old in CHANGES]
    content='  '.join('<ruby>'+(display+'<rt>'+root if mode=='kanji' else root+'<rt>注釈')+'</rt></ruby>o' for root,display in pairs)
    html='<!-- assignment-edition:'+edition+' signature:abcdef created-utc:2026-11-14T00:00:00Z -->\n<!DOCTYPE html>\n<html><head><meta charset="UTF-8"></head><body>\n<p class="text-M_M">\n'+content+'<br>\n&lt;literal&gt; &amp; 圣器 接骨 拥</p></body></html>'
    result=recover_standard_html(html,mode)
    assert result['text']=='sakristio  sambuko  svarmo\n<literal> & 圣器 接骨 拥'
    assert result['assignment_edition']==edition

def test_revision_no_new_owner_transfer_or_third_edition():
    source=json.loads((app.ROOT/'data/current_dictionary_source.json').read_bytes())
    assert source['revision']=='beton-20261114'
    assert source['current_item_count']==10640 and source['current_csv_count']==10698
    for root,new,old in CHANGES:
        assert source['reverse_only_aliases'][old]==root
        assert old not in source['ownership_transfers'] and new not in source['ownership_transfers']
    assert source['ownership_transfers']['洪']=={'old':'diluv','current':'inund','old_profile':LEGACY}
