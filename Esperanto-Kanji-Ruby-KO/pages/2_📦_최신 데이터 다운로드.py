"""Download exactly the selected assignment edition; annotations remain shared."""
from pathlib import Path
from urllib.parse import quote
import streamlit as st
import esp_assignment_edition as editions

APP_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=APP_DIR/'app_data'
ROOT=APP_DIR.parent
LANG=editions.language(DATA_DIR)
WORDS={
    'JA': {'title':'データのダウンロード','large':'置換用データ','small':'辞書・補正データ','note':'漢字化データは選択した版、注釈は両版共通の最新データです。旧版の .gz ファイルは展開すると通常の JSON として利用できます。','kanji':'漢字＋語根ルビ','pure':'漢字化・純粋置換','ruby':'注釈ルビ（共通・最新）','csv':'漢字割り当てCSV','manifest':'旧版の固定データ・検証情報','id':'選択中の版'},
    'ZH': {'title':'下载数据','large':'替换数据','small':'词典及校正数据','note':'汉字化数据使用所选版本，注释为两版共用的最新数据。旧版 .gz 文件解压后可作为普通 JSON 使用。','kanji':'汉字＋词根Ruby','pure':'汉字化·纯替换','ruby':'注释Ruby（共用·最新）','csv':'汉字分配CSV','manifest':'旧版固定数据及验证信息','id':'所选版本'},
    'KO': {'title':'데이터 다운로드','large':'치환 데이터','small':'사전·보정 데이터','note':'한자화 데이터는 선택한 판을 사용하며 주석은 두 판이 최신 데이터를 공유합니다. 구판의 .gz 파일은 압축 해제 후 일반 JSON으로 사용할 수 있습니다.','kanji':'한자＋어근 루비','pure':'한자화·순수 치환','ruby':'주석 루비（공통·최신）','csv':'한자 배정 CSV','manifest':'구판 고정 데이터 및 검증 정보','id':'선택한 판'},
}[LANG]
st.set_page_config(page_title=WORDS['title'],page_icon='📦',layout='wide')
st.title(WORDS['title'])
edition=editions.select_edition(DATA_DIR)
meta=editions.result_metadata(DATA_DIR,edition)
st.caption(WORDS['id']+': '+meta['edition_label']+' · '+meta['signature'][:12])
st.write(WORDS['note'])

# Keep large datasets out of Streamlit's per-session download memory.
st.header(WORDS['large'])
for role in ('kanji','pure','ruby'):
    path=editions.resolve_path(DATA_DIR,role,edition)
    rel=path.relative_to(ROOT).as_posix()
    url=editions.pinned_asset_url(DATA_DIR,path)
    if url:
        st.markdown(f"- [{WORDS[role]} ({path.stat().st_size/1e6:.2f} MB)]({url})")
    else:
        st.caption(WORDS[role]+': '+{'JA':'このローカル版に一致する公開済み固定リンクはありません。','ZH':'此本地数据没有可确认一致的已公开固定链接。','KO':'이 로컬 데이터와 일치하는 공개 고정 링크를 확인할 수 없습니다。'}[LANG])

st.header(WORDS['small'])
csv=editions.resolve_path(DATA_DIR,'kanji_csv',edition)
st.download_button(WORDS['csv'],csv.read_bytes(),
                   file_name=editions.download_filename('kanji_assignments',meta,'csv'),mime='text/csv')
for path in (editions.resolve_path(DATA_DIR,'ruby_csv',edition), DATA_DIR/'分解設定.json',
             DATA_DIR/'word_anno.json',DATA_DIR/'E_stem.json',DATA_DIR/'user_corrections.json'):
    if path.exists():
        st.download_button(path.name,path.read_bytes(),file_name=path.name)
manifest=ROOT/'assignment_editions/legacy/manifest.json'
manifest_url=editions.pinned_asset_url(DATA_DIR,manifest)
if manifest_url:
    st.markdown(f"[{WORDS['manifest']}]({manifest_url})")
