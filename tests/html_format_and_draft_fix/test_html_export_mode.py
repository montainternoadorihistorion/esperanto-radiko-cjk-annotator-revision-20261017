"""Actual forward UI: only unedited bundled standard downloads record direction.

Each language runs in a fresh process to isolate Streamlit caches. Download and
upload transports are instrumented; conversion, editor and save-dialog code run.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, io, json, logging, os, re, subprocess, sys, unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
MARKER='name="esperanto-ruby-mode"'
SOURCE='lasis\n@greganta@ %放ᴱ & <b>@literal@</b>%  fino\n'
EXPECTED='lasis\ngreganta 放ᴱ & <b>@literal@</b>  fino\n'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def worker(language,report=None):
    logging.disable(logging.WARNING)
    sys.dont_write_bytecode=True
    app=ROOT/f'Esperanto-Kanji-Ruby-{language}'
    sys.path.insert(0,str(app));os.chdir(ROOT)
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    import esp_assignment_edition as ed
    parsers={lang:load(ROOT/f'Esperanto-Reverter-{lang}/html_source_recovery.py',f'export_parser_{lang}') for lang in ('JA','ZH')}
    downloads=[];custom_active=False
    real_download=st.download_button;real_upload=st.file_uploader
    custom_payload={ed.GLOBAL:[['lasis','<ruby>放<rt>las</rt></ruby>is','CUSTOMEXPORT000000']],ed.LOCAL:[],ed.TWO:[]}
    custom_bytes=json.dumps(custom_payload,ensure_ascii=False).encode('utf8')
    def download(label,data,*args,**kwargs):
        if hasattr(data,'read'):
            position=data.tell();raw=data.read();data.seek(position)
        else:raw=data if isinstance(data,bytes) else data.encode('utf8')
        downloads.append({'filename':kwargs.get('file_name'),'raw':raw})
        return real_download(label,data,*args,**kwargs)
    def upload(label,*args,**kwargs):
        if custom_active and kwargs.get('key') is None:
            result=io.BytesIO(custom_bytes);result.name='custom.json';result.file_id='format-boundary';result.size=len(custom_bytes)
            return result
        return real_upload(label,*args,**kwargs)
    def run(at):
        at.run();assert not at.exception,[e.message for e in at.exception]
        assert not at.error,[e.value for e in at.error]
    def save(at):
        downloads.clear();at.button(key='confirm_download').click();run(at)
        item=next(x for x in reversed(downloads) if (x['filename'] or '').endswith('.html'))
        return item['raw'].decode('utf8')
    rows=[]
    with patch.object(st,'download_button',side_effect=download),patch.object(st,'file_uploader',side_effect=upload):
        at=AppTest.from_file(app/'main.py',default_timeout=180);run(at)
        for edition in ('current','legacy'):
            at.selectbox(key='_assignment_edition_widget').set_value(edition);run(at)
            for mode,emoji in (('kanji','🈶'),('annotation','📖')):
                choice=next(x for x in at.radio(key='_conversion_mode_widget').options if x.startswith(emoji))
                at.radio(key='_conversion_mode_widget').set_value(choice);run(at)
                at.text_area(key='text0_value').set_value(SOURCE)
                at.button(key='convert_text').click();run(at)
                generated=at.session_state['result_html']
                assert MARKER not in generated and at.text_area(key='edited_html').value==generated
                saved=save(at)
                assert saved.startswith('<!-- assignment-edition:'+edition+' ')
                assert saved.count(MARKER)==1
                tag=f'<meta {MARKER} content="{mode}">\n'
                assert tag in saved
                assert saved.split('\n',1)[1].replace(tag,'',1)==generated
                assert at.session_state['result_html']==generated and at.text_area(key='edited_html').value==generated
                other='annotation' if mode=='kanji' else 'kanji'
                for parser in parsers.values():
                    result=parser.recover_standard_html(saved,mode)
                    assert result['text']==EXPECTED and result['recorded_ruby_mode']==mode
                    try:parser.recover_standard_html(saved,other)
                    except parser.HtmlRubyModeError as exc:assert exc.reason=='mismatch'
                    else:raise AssertionError('Wrong recorded direction was accepted')
                    # Copying the unchanged editor's source keeps the previous no-record contract.
                    assert 'recorded_ruby_mode' not in parser.recover_standard_html(generated,other)
                # Flip the ruby direction in the editor: no inherited mode may constrain it.
                fragment=('<ruby>las<rt>放</rt></ruby>is' if mode=='kanji' else '<ruby>放<rt>las</rt></ruby>is')
                edited=re.sub(r'(<p class="text-M_M">\n).*?(</p>)',lambda m:m[1]+fragment+m[2],generated,flags=re.S)
                assert edited!=generated
                at.text_area(key='edited_html').set_value(edited);run(at)
                edited_saved=save(at)
                assert MARKER not in edited_saved and edited_saved.split('\n',1)[1]==edited
                assert at.session_state['result_html']==generated
                for parser in parsers.values():
                    assert parser.recover_standard_html(edited_saved,other)['text']=='lasis'
                    assert 'recorded_ruby_mode' not in parser.recover_standard_html(edited_saved,mode)
                rows.append({'edition':edition,'mode':mode,'generated_sha256':hashlib.sha256(generated.encode()).hexdigest(),
                             'saved_sha256':hashlib.sha256(saved.encode()).hexdigest(),'edited_saved_sha256':hashlib.sha256(edited_saved.encode()).hexdigest(),
                             'correct_recovery':EXPECTED,'wrong_mode_blocked':True,'editor_untouched':True,'opposite_direction_edit_allowed':True})
        # The same custom JSON format selector can carry the opposite direction.
        custom_active=True
        custom_choice=next(x for x in at.radio(key='_conversion_mode_widget').options if x.startswith('📤'))
        at.radio(key='_conversion_mode_widget').set_value(custom_choice);run(at)
        at.text_area(key='text0_value').set_value('lasis')
        at.button(key='convert_text').click();run(at)
        assert at.session_state['result_assignment_metadata']['render_options']['format']=='HTML格式_Ruby文字_大小调整'
        custom_saved=save(at)
        assert MARKER not in custom_saved and custom_saved.startswith('<!-- assignment-edition:custom_json ')
        for parser in parsers.values():
            assert parser.recover_standard_html(custom_saved,'kanji')['text']=='lasis'
            assert parser.recover_standard_html(custom_saved,'annotation')['text']=='放is'
        # A changed whitespace character is still an edit, and unsupported output
        # formats or non-bundled calls must not accidentally get a direction tag.
        metadata=ed.result_metadata(app/'app_data','current',render_options={'format':'HTML格式_Ruby文字_大小调整_汉字替换'})
        bare=generated
        assert MARKER not in ed.html_download_document(metadata,bare+' ',bare,'kanji')
        assert MARKER not in ed.html_download_document(metadata,bare,bare,None)
        assert MARKER not in ed.html_download_document(metadata,bare,bare,'annotation')
    result={'passed':True,'language':language,'rows':rows,'custom_opposite_payload_preserved':True,
            'standard_saves':4,'edited_saves':4,'custom_saves':1,'recovery_parsers':['JA','ZH'],
            'method':'Actual local AppTest entrypoint and save dialogs; upload/download transport instrumented. No Cloud claim.'}
    if report:
        report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'language':language,'standard_saves':4,'edited_saves':4,'custom_saves':1},ensure_ascii=False),flush=True)

class HtmlExportModeTests(unittest.TestCase):
    def test_all_language_entrypoints(self):
        for language in ('JA','ZH','KO'):
            with self.subTest(language=language):
                result=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--language',language],cwd=ROOT,text=True,encoding='utf8',capture_output=True,timeout=600)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--language');parser.add_argument('--report',type=Path)
    args,other=parser.parse_known_args()
    if args.language:worker(args.language,args.report)
    else:unittest.main(argv=[sys.argv[0]]+other)
