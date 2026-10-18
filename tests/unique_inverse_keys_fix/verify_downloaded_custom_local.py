"""Local fallback only: reimport actual browser-downloaded CSVs with production code."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, io, json, sys

HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_bytes())
class Uploaded(io.BytesIO):
    def __init__(self,raw,name):super().__init__(raw);self.name=name;self.size=len(raw)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=HERE);parser.add_argument('--source-root',type=Path,required=True);args=parser.parse_args()
    base=args.base;evidence=read(base/'cloud_evidence.json');fixture=read(base/'cloud_release_fixture.json')
    cases=[];source_hashes=[]
    for lang,name in [('JA','esperanto_converter.py'),('ZH','esperanto_converter_zh.py')]:
        rel=Path('Esperanto-Reverter-'+lang)/name;path=args.source_root/rel
        spec=importlib.util.spec_from_file_location('actual_download_custom_'+lang,path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        source_hashes.append({'path':rel.as_posix(),'sha256':sha(path.read_bytes())})
        for edition in ('current','legacy'):
            observed=next(r for r in evidence['downloads'] if r['language']==lang and r['edition']==edition and r['kind']=='effective')
            path=Path(observed['path']);path=path if path.is_absolute() else base/path;raw=path.read_bytes()
            expected_file=next(r for r in fixture['downloads'] if r['language']==lang and r['edition']==edition and r['kind']=='effective')
            assert sha(raw)==expected_file['expected_sha256'] and raw==(base/expected_file['expected_file']).read_bytes()
            case=next(r for r in fixture['inverse_cases'] if r['language']==lang and r['edition']==edition)
            uploaded=Uploaded(raw,observed['filename'])
            df=module.load_selected_dataframe('custom',uploaded);assert df is not None
            records=module.effective_mapping_records('custom',df)
            assert records==module.dataframe_to_mapping_records(df)
            index=module.build_mapping_index_cached(records)
            actual=module.convert_kanji_esperanto_to_alphabet(case['input'],index)
            assert actual==case['expected_output'],(lang,edition,actual)
            source_id='pejvo-piv-20260620' if edition=='current' else 'pre-las-20261017'
            official=module.build_mapping_index_cached(module.effective_mapping_records(source_id,module.load_dictionary_source(source_id)))
            assert index.by_length==official.by_length and index.lengths_desc==official.lengths_desc and index.entry_count==official.entry_count
            provenance=module.source_provenance('custom',uploaded)
            assert provenance['dictionary_sha256']==sha(raw)
            cases.append({'case_id':lang+'_'+edition+'_effective_local_reimport','language':lang,'edition':edition,'download_case_id':observed['case_id'],'downloaded_filename':observed['filename'],'downloaded_sha256':sha(raw),'downloaded_bytes':len(raw),'input':case['input'],'expected_output':case['expected_output'],'actual_output':actual,'custom_provenance':provenance,'entire_mapping_matches_selected_ui_dictionary':True,'mapping_entries':index.entry_count,'automatic_alias_injection_into_custom':False,'passed':True})
    report={'completed':True,'passed':True,'verification_kind':'local_production_reimport_of_actual_cloud_downloads','not_a_cloud_upload_test':True,'cloud_upload_verified':False,'reason':'Chrome file URL permission blocks browser upload; this verifies downloaded content and production import/conversion locally only.','utc':datetime.now(timezone.utc).isoformat(),'fixture_sha256':sha((base/'cloud_release_fixture.json').read_bytes()),'cases':cases,'source_files':source_hashes,'script_sha256':sha(Path(__file__).read_bytes())}
    (base/'cloud_custom_local_fallback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'local_cases':len(cases),'cloud_upload_verified':False},ensure_ascii=False))

if __name__=='__main__':main()
