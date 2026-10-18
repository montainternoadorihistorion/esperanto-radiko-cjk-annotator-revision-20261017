"""Two visible editions, immutable baseline, and revision-labelled saved results."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,shutil
import pytest
from streamlit.testing.v1 import AppTest
import esperanto_converter_zh as app
CURRENT='pejvo-piv-20260620';OLD='pre-las-20261017'
def result_download(at):return next(b for b in at.get('download_button') if b.proto.label in ('テキストをダウンロード','📥 下载文本'))
def test_only_two_editions_archive_api_and_selected_csv_formats():
 assert app.dictionary_options()==[CURRENT,OLD]
 assert [app.dictionary_label(v) for v in app.dictionary_options()]==['新版（更新中）','旧版（固定）']
 assert len(app.DICTIONARY_SOURCES)==8
 for source in app.DICTIONARY_SOURCES:
  assert not app.load_dictionary_source(source).empty
 for source in [CURRENT,OLD]:
  full,snippet=app.edition_download_data(source)
  assert app.build_mapping_index(app.read_assignment_csv(io.BytesIO(full)))==app.build_mapping_index(app.read_assignment_csv(io.BytesIO(snippet)))
  assert len(list(csv.reader(io.StringIO(snippet.decode()))))==(10678 if source==CURRENT else 10636)
  if source==OLD:
   assert hashlib.sha256(full).hexdigest()==app.EDITION_POLICY['fixed_csv_sha256']
   assert hashlib.sha256(snippet).hexdigest()==app.EDITION_POLICY['fixed_two_column_sha256']
  else:assert snippet==app.LEGACY_CSV.read_bytes()
  meta=app.source_provenance(source)
  assert meta['edition_id']==('current' if source==CURRENT else 'legacy')
  assert meta['dictionary_sha256']==hashlib.sha256(full).hexdigest()
  assert meta['dictionary_sha256'][:12] in meta['result_filename']
  assert meta['edition'] in meta['result_filename']
def test_ui_two_editions_preserves_created_label_and_download_names():
 captured=[];original=app.st.download_button
 def capture(*args,**kwargs):
  captured.append({'label':kwargs.get('label',args[0] if args else ''),'file_name':kwargs.get('file_name'),'data':kwargs.get('data',args[1] if len(args)>1 else None),'disabled':kwargs.get('disabled',False)})
  return original(*args,**kwargs)
 with patch.object(app.st,'download_button',side_effect=capture):
  at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run();assert not at.exception
  assert at.sidebar.selectbox[0].options==['新版（更新中）','旧版（固定）']
  assert at.sidebar.selectbox[0].value==CURRENT
  assert len([b for b in at.get('download_button') if 'CSV' in b.proto.label])==2
  text='留is 放is 簧o 讽o 精ˢo 妆o 移植o 嫁接i 嫁妆o'
  at.text_area[0].set_value(text);at.button[0].click().run();assert not at.exception
  assert at.text_area[1].value=='留is lasis risorto satiro silfo doto grefto grefti doto'
  newmeta=app.source_provenance(CURRENT);oldmeta=app.source_provenance(OLD)
  assert at.session_state[app.CONVERTED_PROVENANCE_KEY]==newmeta
  assert not result_download(at).proto.disabled
  assert any(c['file_name']==newmeta['result_filename'] and not c['disabled'] for c in captured)
  at.sidebar.selectbox[0].set_value(OLD).run();assert not at.exception and at.warning
  assert result_download(at).proto.disabled and at.session_state[app.CONVERTED_PROVENANCE_KEY]==newmeta
  assert any(newmeta['label'] in c.value for c in at.caption)
  assert captured[-1]['file_name']==newmeta['result_filename'] and captured[-1]['disabled']
  assert any(c['file_name']==oldmeta['dictionary_filename'] for c in captured)
  assert any(c['file_name']==oldmeta['snippet_filename'] for c in captured)
  at.button[0].click().run();assert not at.exception
  assert at.text_area[1].value=='lasis emancipis anĉo karikaturo spermato tualeto translaciplanto grefti doto'
  assert at.session_state[app.CONVERTED_PROVENANCE_KEY]==oldmeta and not result_download(at).proto.disabled
  assert captured[-1]['file_name']==oldmeta['result_filename']
  at.sidebar.selectbox[0].set_value(CURRENT).run();assert at.warning and result_download(at).proto.disabled
def test_custom_csv_is_independent_of_two_editions_and_content_is_tracked():
 at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run();assert not at.exception
 at.checkbox[0].check().run();assert not at.exception
 assert at.sidebar.selectbox[0].options==['新版（更新中）','旧版（固定）']
 assert at.sidebar.selectbox[0].disabled
 assert len(at.get('file_uploader'))==1
 custom=io.BytesIO('bon,良\n'.encode());custom.name='custom.csv';custom.size=len(custom.getvalue())
 with patch.object(app.st,'file_uploader',side_effect=lambda *a,**k:(custom.seek(0),custom)[1]):
  at.run();assert not at.exception
  at.text_area[0].set_value('良a');at.button[0].click().run();assert not at.exception
  assert at.text_area[1].value=='bona' and at.session_state[app.CONVERTED_PROVENANCE_KEY]['edition_id']=='custom'
  assert not result_download(at).proto.disabled
 other=io.BytesIO('bad,良\n'.encode());other.name=custom.name;other.size=custom.size
 assert app.source_provenance('custom',custom)['identity']!=app.source_provenance('custom',other)['identity']
 with patch.object(app.st,'file_uploader',side_effect=lambda *a,**k:(other.seek(0),other)[1]):
  at.run();assert not at.exception and at.warning and result_download(at).proto.disabled
 at.checkbox[0].uncheck().run();assert not at.exception and not at.sidebar.selectbox[0].disabled
def test_revision_change_keeps_old_result_label_until_reconversion(tmp_path):
 shutil.copytree(app.ROOT/'data',tmp_path/'data')
 target=tmp_path/Path(app.__file__).name;shutil.copy2(app.__file__,target)
 at=AppTest.from_file(str(target),default_timeout=20).run();assert not at.exception
 at.text_area[0].set_value('移植i');at.button[0].click().run();assert not at.exception
 created=dict(at.session_state[app.CONVERTED_PROVENANCE_KEY])
 metadata=tmp_path/'data/current_dictionary_source.json';value=json.loads(metadata.read_bytes());value['revision']+='-next-review'
 metadata.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
 # Simulate a reviewed dictionary revision together with its supplement pin.
 supplement=tmp_path/'data/current_inverse_aliases.json';pin=json.loads(supplement.read_bytes());pin['dictionary_revision']=value['revision'];supplement.write_text(json.dumps(pin,ensure_ascii=False),encoding='utf-8')
 at.run();assert not at.exception and at.warning and result_download(at).proto.disabled
 assert at.session_state[app.CONVERTED_PROVENANCE_KEY]==created
 assert any(created['label'] in c.value for c in at.caption)
 at.button[0].click().run();assert not at.exception and not result_download(at).proto.disabled
 assert at.session_state[app.CONVERTED_PROVENANCE_KEY]['revision']==value['revision']
 assert at.session_state[app.CONVERTED_PROVENANCE_KEY]['result_filename']!=created['result_filename']
def test_unversioned_previous_session_cannot_be_relabelled():
 at=AppTest.from_file(str(Path(app.__file__)),default_timeout=20).run()
 at.text_area[0].set_value('移植i');at.button[0].click().run();assert not at.exception
 at.session_state[app.CONVERTED_PROVENANCE_KEY]={}
 at.run();assert not at.exception and at.warning and result_download(at).proto.disabled
 assert any(('版情報のない' in c.value or '没有版本记录' in c.value) for c in at.caption)
def test_fixed_dictionary_tampering_is_rejected(tmp_path,monkeypatch):
 wrong=tmp_path/'old.csv';wrong.write_text('bon,良\n',encoding='utf-8')
 sources=dict(app.DICTIONARY_SOURCES);sources[OLD]={**sources[OLD],'path':wrong};monkeypatch.setattr(app,'DICTIONARY_SOURCES',sources)
 with pytest.raises(ValueError,match='fixed pre-assignment dictionary has changed'):app.source_provenance(OLD)
