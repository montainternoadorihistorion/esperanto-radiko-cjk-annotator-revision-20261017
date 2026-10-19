"""Real app: exact local payloads, edition switching and saved bytes.

Only download transport is captured. All controls, conversion, provenance and
save-confirmation dialog logic run as the production Streamlit app.
"""
from pathlib import Path
import argparse, hashlib, json, logging, os, sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
SOURCE='greganta preganta kordonita\n@greganta@ @preganta@ @kordonita@\nsene kseno'
LABELS={'JA':'置換結果のダウンロード（編集を反映）','ZH':'下载转换结果（已反映编辑）','KO':'치환 결과 다운로드(편집 반영)'}

def check(language, report):
    logging.disable(logging.WARNING)
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    app=ROOT/f'Esperanto-Kanji-Ruby-{language}'
    sys.path.insert(0,str(app)); sys.path.insert(1,str(ROOT/'Esperanto-Reverter-JA'))
    import esp_assignment_edition as editions
    from html_source_recovery import recover_standard_html
    correction_bytes=(app/'app_data/user_corrections.json').read_bytes()
    original_download=st.download_button
    captures=[]; rows=[]; guards=[]
    def download(label,data,*args,**kwargs):
        if label==LABELS[language]:
            captures.append({'data':data if isinstance(data,bytes) else data.encode('utf8'),'filename':kwargs['file_name'],'mime':kwargs['mime']})
        return original_download(label,data,*args,**kwargs)
    at=AppTest.from_file(app/'main.py',default_timeout=180)
    def run():
        captures.clear(); at.run()
        assert not at.exception,[e.message for e in at.exception]
        assert not at.error,[e.value for e in at.error]
    os.chdir(ROOT)
    with patch.object(st,'download_button',side_effect=download):
        run()
        for edition in ('current','legacy','current'):
            at.selectbox(key='_assignment_edition_widget').set_value(edition); run()
            if rows:
                assert at.text_area(key='text0_value').value==SOURCE
                assert not any(b.key=='confirm_download' for b in at.button)
                guards.append('edition switch invalidated previous result and retained draft: '+edition)
            for mode,option in [('pure',2),('kanji',1),('ruby',0)]:
                choices=at.radio(key='_conversion_mode_widget').options
                at.radio(key='_conversion_mode_widget').set_value(choices[option]); run()
                at.text_area(key='text0_value').set_value(SOURCE)
                at.button(key='convert_text').click(); run()
                result=at.session_state['result_html']
                metadata=dict(at.session_state['result_assignment_metadata'])
                assert metadata['edition_id']==edition
                if mode=='pure':
                    lines=result.strip().splitlines()
                    assert lines[0]==('群ᴳ在a 压ᴾᴳ在a kordonita' if edition=='legacy' else 'g治在a p治在a k令受a'),lines
                    assert lines[1]=='群ᴳ在a 压ᴾᴳ在a 带ᴷ受a',lines
                    assert lines[2]=='s内e 外ᴷˢo',lines
                else:
                    assert recover_standard_html(result,'annotation' if mode=='ruby' else 'kanji')['text']==SOURCE.replace('@','')
                assert not captures
                at.button(key='confirm_download').click(); run()
                assert len(captures)==1
                saved=captures[0]
                prefix='' if mode=='pure' else editions.html_download_metadata(metadata)
                assert saved['data']==(prefix+result).encode('utf8')
                assert saved['filename'].endswith('_'+edition+'_'+metadata['signature'][:12]+('.txt' if mode=='pure' else '.html'))
                assert saved['mime']==('text/plain' if mode=='pure' else 'text/html')
                rows.append({'edition':edition,'mode':mode,'output_sha256':hashlib.sha256(result.encode()).hexdigest(),
                             'download_sha256':hashlib.sha256(saved['data']).hexdigest(),'filename':saved['filename'],'mime':saved['mime']})
                run()
                assert not captures
                at.text_area(key='text0_value').set_value(SOURCE+'\n%NEW%')
                at.button(key='confirm_download').click(); run()
                assert not captures
                assert not any(b.key=='confirm_download' for b in at.button)
                guards.append(edition+'/'+mode+': changed input cannot save previous output')
                at.text_area(key='text0_value').set_value(SOURCE); run()
                print(language,edition,mode,'target UI PASS',flush=True)
        assert (app/'app_data/user_corrections.json').read_bytes()==correction_bytes
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'passed':True,'language':language,'input':SOURCE,'rows':rows,'guards':guards,'saved_corrections_unchanged':True,
                                  'method':'Local real Streamlit AppTest; download transport captured; no Cloud claim.'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--language',required=True); parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args(); check(args.language,args.report)
