"""Actual manual-preview and custom-upload UI paths; capture engine flags only."""
from pathlib import Path
import argparse, io, json, logging, os, sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]

def check(language,report):
    logging.disable(logging.WARNING)
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    app=ROOT/f'Esperanto-Kanji-Ruby-{language}';sys.path.insert(0,str(app));os.chdir(ROOT)
    import esp_text_replacement_module as rt
    import esp_assignment_edition as ed
    original=rt.orchestrate_comprehensive_esperanto_text_replacement
    corrections=app/'app_data/user_corrections.json';saved=corrections.read_bytes();calls=[];rows=[]
    def call(*args,**kwargs):
        value=original(*args,**kwargs)
        calls.append({'text':args[0] if args else kwargs.get('text'),
                      'opt_in':kwargs.get('reviewed_local_decompositions',False), 'output':value})
        return value
    def run(at):
        calls.clear();at.run()
        assert not at.exception,[e.message for e in at.exception]
        assert not at.error,[e.value for e in at.error]
    with patch.object(rt,'orchestrate_comprehensive_esperanto_text_replacement',side_effect=call):
        original_upload=st.file_uploader
        payload={ed.GLOBAL:[['greganta','CUSTOMGLOBALG','$9080000$'],['preganta','CUSTOMGLOBALP','$9080001$']],
                 ed.LOCAL:[['greganta','CUSTOMLOCALG','$9080002$'],['preganta','CUSTOMLOCALP','$9080003$'],
                           ['greg','ATOM-G','$9080004$'],['preg','ATOM-P','$9080005$'],['ant','ATOM-A','$9080006$']],ed.TWO:[]}
        raw=json.dumps(payload,ensure_ascii=False).encode()
        def upload(label,*args,**kwargs):
            if kwargs.get('key') is None:
                f=io.BytesIO(raw);f.name='置換リスト_漢字_純粋置換.json';f.file_id='same-built-in-name';f.size=len(raw);return f
            return original_upload(label,*args,**kwargs)
        with patch.object(st,'file_uploader',side_effect=upload):
            at=AppTest.from_file(app/'main.py',default_timeout=180);run(at)
            options=at.radio(key='_conversion_mode_widget').options
            at.radio(key='_conversion_mode_widget').set_value(options[3]);run(at)
            fmt=next(w for w in at.selectbox if w.key!='_assignment_edition_widget')
            fmt.set_value(fmt.options[-1]);run(at)
            for edition in ('current','legacy'):
                at.selectbox(key='_assignment_edition_widget').set_value(edition);run(at)
                at.text_area(key='text0_value').set_value('@greganta@ @preganta@\ngreganta preganta')
                at.button(key='convert_text').click();run(at)
                result=at.session_state['result_html']
                assert result=='CUSTOMLOCALG CUSTOMLOCALP\nCUSTOMGLOBALG CUSTOMGLOBALP',result
                assert calls and all(c['opt_in'] is False for c in calls),calls
                metadata=at.session_state['result_assignment_metadata']
                assert metadata['source_id']=='custom_json' and metadata['edition_id'] is None
                rows.append({'surface':'custom_upload','edition':edition,'upload_name':'置換リスト_漢字_純粋置換.json',
                             'result':result,'all_opt_out':True,'metadata_source':'custom_json','real_engine_calls':len(calls)})
                print(language,edition,'custom upload PASS',flush=True)
        # Start main before the page: Streamlit's process-global page registry
        # otherwise treats main.py as a second-page entry and loses url_pathname.
        page=next(p for p in (app/'pages').glob('1_*.py'))
        at=AppTest.from_file(page,default_timeout=180);run(at)
        for edition in ('current','legacy'):
            at.selectbox(key='_assignment_edition_widget').set_value(edition);run(at)
            for word,decomp in (('@greganta@','greg/ant/a'),('@preganta@','preg/ant/a'),('@kordonita@','kordon/it/a')):
                at.text_input(key='word_probe').set_value(word)
                at.button[0].click();run(at)
                assert at.session_state['probe_ruby']==decomp,(language,edition,word,at.session_state['probe_ruby'])
                assert len(calls)==3 and all(c['opt_in'] is True for c in calls),calls
                rows.append({'surface':'manual_preview','edition':edition,'input':word,'decomposition':decomp,'real_engine_calls':len(calls),'all_opt_in':True})
                print(language,edition,word,'manual preview PASS',flush=True)
    assert corrections.read_bytes()==saved
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'passed':True,'language':language,'rows':rows,'saved_corrections_unchanged':True,
                                 'method':'Real AppTest pages and production engine; custom file transport and engine-call recording instrumented. No Cloud claim.'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();check(a.language,a.report)
