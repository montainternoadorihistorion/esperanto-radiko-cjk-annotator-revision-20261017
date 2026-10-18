"""Approved shortening, historical aliases, and frozen oval/elips assignments."""
import pytest
import esperanto_converter_zh as app
from build_reverter_dictionary_from_all_json import rows_from_all_json
MAPPINGS={"strut":("鸵","鸵鸟"),"sinergi":("协同","协同作用"),"oliv":("榄","橄榄")}
@pytest.mark.parametrize("source_id",["pejvo-piv-20260620","legacy-minimal"])
def test_current_and_old_forms(source_id):
    index=app.build_mapping_index(app.load_dictionary_source(source_id))
    for root,bodies in MAPPINGS.items():
        for body in bodies:
            for ending in ("","o","oj","on","ojn","a","aj","an","ajn","e","i","igi","igxis"):
                for suffix in (ending,ending.upper()):
                    assert app.convert_kanji_esperanto_to_alphabet(body+suffix,index)==root+ending
    assert app.convert_kanji_esperanto_to_alphabet("椭圆a 椭圆ᴱo",index)=="ovala elipso"
    assert app.convert_kanji_esperanto_to_alphabet("鸵鸟o 鸟o 鸵o",index)=="struto birdo struto"
    assert app.convert_kanji_esperanto_to_alphabet("协同作用o 协同o",index)=="sinergio sinergio"
@pytest.mark.parametrize("root",list(MAPPINGS))
def test_custom_and_conflicting_sources(root):
    current,old=MAPPINGS[root]
    assert [r["kanji"] for r in rows_from_all_json({"items":[{"sourceRoot":root,"body":old}]})]==[old]
    with pytest.raises(ValueError,match="conflicts with another root"):
        rows_from_all_json({"items":[{"sourceRoot":root,"body":current},{"sourceRoot":"other","body":old}]})
def test_unchanged_legacy_dictionary():
    index=app.build_mapping_index(app.load_dictionary_source("pre-las-20261017"))
    for root,(_,old) in MAPPINGS.items():
        assert app.convert_kanji_esperanto_to_alphabet(old+"o",index)==root+"o"
