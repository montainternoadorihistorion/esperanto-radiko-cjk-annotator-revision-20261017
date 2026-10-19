"""Independent actual UI test for download guidance and session backups.

Upload/download transport is instrumented; production page logic, data,
correction import/save, edition handling and source-link checks run unchanged.
Run each language in a fresh process after committing the reviewed source.
"""
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote, unquote, urlparse
import argparse, hashlib, io, json, logging, os, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[3]
REPO='montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017'

def check(language,report):
    logging.disable(logging.WARNING)
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    app=ROOT/f'Esperanto-Kanji-Ruby-{language}'; data_dir=app/'app_data'
    sys.path.insert(0,str(app));os.chdir(ROOT)
    import esp_assignment_edition as ed
    baseline_path=data_dir/'user_corrections.json'; baseline=baseline_path.read_bytes()
    manual_path=next((app/'pages').glob('1_*.py')); data_path=next((app/'pages').glob('2_*.py'))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    source_hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (manual_path,data_path,app/'main.py',app/'esp_assignment_edition.py')}
    captured=[]; nav=[]; import_active=False
    real_download=st.download_button;real_upload=st.file_uploader;real_page_link=st.page_link
    imported=[{'word':'semajno','decomp':'semajn/o'},
              {'word':'lasis','decomp':'las/is','kanji':[['lasis','STALE_IMPORT_GLYPH']]}]
    upload_bytes=json.dumps(imported,ensure_ascii=False).encode()
    def download(label,data,*args,**kwargs):
        if hasattr(data,'read'):
            position=data.tell();raw=data.read();data.seek(position)
        else:
            raw=data if isinstance(data,bytes) else data.encode('utf8')
        captured.append({'label':label,'filename':kwargs.get('file_name'),'mime':kwargs.get('mime'),'raw':raw})
        return real_download(label,data,*args,**kwargs)
    def upload(label,*args,**kwargs):
        if import_active and kwargs.get('key')=='cor_upload':
            stream=io.BytesIO(upload_bytes);stream.name='user_corrections.json'
            stream.file_id='independent-import';stream.size=len(upload_bytes);return stream
        return real_upload(label,*args,**kwargs)
    def page_link(page,*args,**kwargs):
        nav.append({'page':str(page),'label':kwargs.get('label')})
        return real_page_link(page,*args,**kwargs)
    def run(at):
        captured.clear();nav.clear();at.run()
        assert not at.exception,[e.message for e in at.exception]
        assert not at.error,[e.value for e in at.error]
    def result_signature(at,edition):
        session=[{k:c.get(k) for k in ('word','decomp','_disabled')}
                 for c in at.session_state['user_corrections_session']]
        corrections=hashlib.sha256(json.dumps(session,ensure_ascii=False,sort_keys=True).encode('utf8')).hexdigest()
        return hashlib.sha256(json.dumps([ed.edition_signature(data_dir,edition),corrections,None,None],sort_keys=True).encode('utf8')).hexdigest()
    def backup(at,edition):
        item=next(c for c in captured if (c['filename'] or '').startswith('user_corrections_'))
        parsed=json.loads(item['raw'])
        assert {x['word']:x['decomp'] for x in parsed}=={'semajno':'semajn/o','greganta':'greg/ant/a','lasis':'las/i/s'}
        assert all(x['assignment_edition']==edition for x in parsed)
        assert all(x['assignment_signature']==ed.edition_signature(data_dir,edition) for x in parsed)
        assert item['filename']=='user_corrections_'+edition+'_'+result_signature(at,edition)[:12]+'.json',item['filename']
        assert b'STALE_IMPORT_GLYPH' not in item['raw']
        las=next(x for x in parsed if x['word']=='lasis')['kanji'][0][1]
        assert ('放' if edition=='current' else '留') in las
        return {'label':item['label'],'filename':item['filename'],'sha256':hashlib.sha256(item['raw']).hexdigest(),
                'bytes':len(item['raw']),'content':parsed,'selected_edition':edition}
    rows=[]
    with patch.object(st,'download_button',side_effect=download),patch.object(st,'file_uploader',side_effect=upload),patch.object(st,'page_link',side_effect=page_link):
        for edition in ('current','legacy'):
            manual=AppTest.from_file(app/'main.py',default_timeout=180);run(manual)
            manual.switch_page(manual_path.relative_to(app).as_posix());run(manual)
            manual.selectbox(key='_assignment_edition_widget').set_value(edition);run(manual)
            import_active=True;run(manual)
            next(b for b in manual.button if b.label.startswith('⬆')).click();run(manual)
            import_active=False;run(manual)
            assert {x['word']:x['decomp'] for x in manual.session_state['user_corrections_session']}=={'semajno':'semajn/o','lasis':'las/is'}
            for decomp in ('greg/ant/a','las/i/s'):
                manual.text_input(key='decomp_in').set_value(decomp);run(manual)
                next(b for b in manual.button if b.label.startswith('✅')).click();run(manual)
            final_backup=backup(manual,edition)
            final_draft=manual.text_input(key='decomp_in').value
            assert final_draft=='las/i/s'
            other='legacy' if edition=='current' else 'current'
            manual.selectbox(key='_assignment_edition_widget').set_value(other);run(manual)
            alternate_backup=backup(manual,other)
            assert manual.text_input(key='decomp_in').value==final_draft
            manual.selectbox(key='_assignment_edition_widget').set_value(edition);run(manual)
            assert backup(manual,edition)==final_backup
            manual_nav=list(nav)
            assert any(Path(x['page'])==Path('pages')/data_path.name for x in manual_nav),manual_nav
            manual_text=[e.value for kind in ('markdown','caption','info') for e in manual.get(kind)]
            session=[dict(c) for c in manual.session_state['user_corrections_session']]
            data=manual.switch_page(data_path.relative_to(app).as_posix())
            run(data)
            data_text=[e.value for kind in ('markdown','caption','info') for e in data.get(kind)]
            urls=[url for text in data_text for url in re.findall(r'\]\((https?://[^\s)]+)\)',text)]
            expected_source=f'https://github.com/{REPO}/tree/{commit}'
            expected_zip=f'https://github.com/{REPO}/archive/{commit}.zip'
            assert expected_source in urls and expected_zip in urls,('source links not verifiable or wrong commit',urls)
            asset_rows=[]
            for role in ('kanji','pure','ruby'):
                path=ed.resolve_path(data_dir,role,edition)
                rel=path.relative_to(ROOT).as_posix()
                expected_url=f'https://raw.githubusercontent.com/{REPO}/{commit}/'+quote(rel)
                assert expected_url in urls,(role,expected_url,urls)
                git_blob=subprocess.check_output(['git','rev-parse',commit+':'+rel],cwd=ROOT).decode().strip()
                actual_blob=subprocess.check_output(['git','hash-object','--no-filters',str(path)],cwd=ROOT).decode().strip()
                assert git_blob==actual_blob
                asset_rows.append({'role':role,'url':expected_url,'path':rel,'git_blob':git_blob,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            expected_paths=[ed.resolve_path(data_dir,'kanji_csv',edition),ed.resolve_path(data_dir,'ruby_csv',edition)]+[data_dir/name for name in ('分解設定.json','word_anno.json','E_stem.json','user_corrections.json')]
            payloads=[]
            for path in expected_paths:
                filename=('kanji_assignments_'+edition+'_'+result_signature(data,edition)[:12]+'.csv') if path==expected_paths[0] else path.name
                item=next(x for x in captured if x['filename']==filename)
                assert item['raw']==path.read_bytes(),filename
                payloads.append({'label':item['label'],'filename':filename,'bytes':len(item['raw']),
                                 'sha256':hashlib.sha256(item['raw']).hexdigest(),'matches_original_asset':True})
            raw_backup=next(x for x in captured if x['filename']=='user_corrections.json')
            assert raw_backup['raw']==baseline
            assert any(Path(x['page'])==Path('pages')/manual_path.name for x in nav),nav
            assert data.session_state['user_corrections_session']==session
            rows.append({'edition':edition,'source_url':expected_source,'zip_url':expected_zip,'large_assets':asset_rows,
              'small_downloads':payloads,'manual_backup':final_backup,'alternate_edition_backup':alternate_backup,
              'session_import_preserved':True,'new_entry_preserved':True,'edited_entry_preserved':True,
              'draft_retained_across_edition_switch':True,'bundled_baseline_excludes_session':True,
              'manual_page_navigation':manual_nav,'data_page_navigation':list(nav),
              'manual_visible_text':manual_text,'data_visible_text':data_text})
            print(language,edition,'download guidance and backup UI PASS',flush=True)
    assert baseline_path.read_bytes()==baseline
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in source_hashes.items())
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'passed':True,'language':language,'source_commit':commit,'rows':rows,
      'source_hashes':source_hashes,'application_and_baseline_unchanged':True,
      'method':'Actual local Streamlit AppTest pages; upload/download transport and navigation-call recording only are instrumented. Import two decompositions with stale glyph data, add a third and edit an existing decomposition through real buttons, preserve them across edition changes and data-page session transfer. Every small download payload compared byte for byte to selected asset; large URLs verified against selected paths and committed blobs; source and ZIP URLs must match the same committed source. No Cloud claim.'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--language',required=True);p.add_argument('--report',type=Path,required=True)
    args=p.parse_args();check(args.language,args.report)
