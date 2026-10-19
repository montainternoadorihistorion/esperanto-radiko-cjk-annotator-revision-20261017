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
GUIDANCE = {
    "JA": {
        "title": "同じ結果を再現するには",
        "raw": "このページのJSONは置換表の原本です。@の個別補正や自動補正など、アプリ側の処理をすべて含むわけではありません。JSONだけを別のプログラムで使うと、結果が異なる場合があります。",
        "steps": "同じ結果を再現するには、**対応するソース版とデータ**を保存し、**言語版・入力本文・新旧の選択・変換モード・文字表記などの設定**をそろえてください。手動補正を追加・読み込みして使った場合は、下の手動補正ページから**現在有効な補正のバックアップ**も保存してください。",
        "legacy": "旧版で固定されているのは漢字割り当てです。確認済みの処理上の不具合修正は旧版にも適用されるため、旧版のJSONだけでは当時のアプリ全体を再現できません。",
        "custom": "自作JSON本体は新旧の選択対象外で、同梱データ専用の補正も適用されません。自動語根補正には共通の最新注釈を使います。",
        "manual_link": "現在有効な手動補正を確認・バックアップする",
        "source": "この版のアプリソースを見る",
        "zip": "この版のソース一式を保存（ZIP）",
        "source_note": "このアプリのソースと選択中のデータが一致する公開ソース版",
        "source_missing": "このローカル状態に一致する公開ソース版を確認できないため、再現用のソースリンクは表示していません。データの保存は下から行えます。",
        "bundled": "同梱の承認済み補正（セッションの変更を含まない）",
        "bundled_note": "下の user_corrections.json はアプリ同梱の承認済み補正です。このセッションで追加・読み込みした補正や削除の結果は含みません。再現に使う現在の手動補正は、手動補正ページから保存してください。"
    },
    "ZH": {
        "title": "如何重现相同结果",
        "raw": "本页的JSON是替换表原文件，不包含应用中的全部处理，例如@的专门校正和自动校正。仅在其他程序中使用JSON，结果可能不同。",
        "steps": "要重现相同结果，请保存**对应版本的源代码和数据**，并使用相同的**界面语言、输入原文、新旧版本、转换模式、字母表示方式等设置**。如果添加或导入过手动校正，还需从下面的手动校正页面保存**当前生效校正的备份**。",
        "legacy": "旧版固定的是汉字分配。已确认的程序问题修复仍会应用于旧版，因此仅保存旧版JSON无法重现当时的整个应用。",
        "custom": "新旧版本选择不改变自定义JSON本身，内置数据专用的校正也不会应用于自定义JSON。自动词根校正使用共用的最新注释。",
        "manual_link": "查看并备份当前生效的手动校正",
        "source": "查看此版本的应用源代码",
        "zip": "保存此版本的完整源代码（ZIP）",
        "source_note": "与此应用源代码及所选数据一致的已公开版本",
        "source_missing": "无法确认与当前本地状态一致的已公开源代码版本，因此不显示用于重现结果的源代码链接。仍可在下方保存数据。",
        "bundled": "应用内置的已确认校正（不含本次会话的修改）",
        "bundled_note": "下方的user_corrections.json是应用内置的已确认校正，不包含本次会话中添加、导入或删除后的结果。用于重现结果的当前手动校正，请从手动校正页面保存。"
    },
    "KO": {
        "title": "같은 결과를 재현하려면",
        "raw": "이 페이지의 JSON은 치환표 원본입니다. @ 전용 보정과 자동 보정 등 앱에서 수행하는 모든 처리가 포함되어 있지는 않습니다. 다른 프로그램에서 JSON만 사용하면 결과가 달라질 수 있습니다.",
        "steps": "같은 결과를 재현하려면 **해당 버전의 소스 코드와 데이터**를 보관하고 **언어판·입력 원문·신판/구판 선택·변환 모드·문자 표기 등의 설정**을 맞춰 주세요. 수동 보정을 추가하거나 불러와 사용했다면, 아래 수동 보정 페이지에서 **현재 적용 중인 보정의 백업**도 저장해 주세요.",
        "legacy": "구판에서 고정되는 것은 한자 배정입니다. 확인된 프로그램 오류 수정은 구판에도 적용되므로, 구판 JSON만으로 당시 앱 전체를 재현할 수는 없습니다.",
        "custom": "신판/구판 선택은 사용자 JSON 자체에 적용되지 않으며, 앱 내장 데이터 전용 보정도 적용되지 않습니다. 자동 어근 보정에는 공통 최신 주석을 사용합니다.",
        "manual_link": "현재 적용 중인 수동 보정 확인·백업",
        "source": "이 버전의 앱 소스 코드 보기",
        "zip": "이 버전의 전체 소스 코드 저장（ZIP）",
        "source_note": "현재 앱 소스 코드 및 선택한 데이터와 일치하는 공개 버전",
        "source_missing": "현재 로컬 상태와 일치하는 공개 소스 버전을 확인할 수 없어 재현용 소스 링크를 표시하지 않습니다. 데이터는 아래에서 저장할 수 있습니다.",
        "bundled": "앱에 내장된 승인 보정（현재 세션의 변경 제외）",
        "bundled_note": "아래 user_corrections.json은 앱에 내장된 승인 보정입니다. 현재 세션에서 추가·불러오기·삭제한 결과는 포함하지 않습니다. 재현에 사용할 현재 수동 보정은 수동 보정 페이지에서 저장해 주세요."
    }
}[LANG]


def _matching_source_links():
    """Reuse the verified-asset cache; never call mutable main a matching source."""
    paths = list(APP_DIR.glob("*.py")) + list((APP_DIR / "pages").glob("*.py"))
    paths += [APP_DIR / "requirements.txt", ROOT / "requirements.txt"]
    paths += [editions.resolve_path(DATA_DIR, role, edition)
              for role in ("kanji", "pure", "ruby", "kanji_csv", "ruby_csv")]
    paths += [DATA_DIR / name for name in
              ("char_widths.json", "placeholders_skip.txt", "placeholders_localcapture.txt",
               "user_corrections.json", "分解設定.json", "word_anno.json", "E_stem.json")]
    prefix = "https://raw.githubusercontent.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017/"
    commit = None
    for path in sorted(set(paths)):
        url = editions.pinned_asset_url(DATA_DIR, path)
        if not url or not url.startswith(prefix):
            return None
        candidate = url[len(prefix):].split("/", 1)[0]
        if len(candidate) != 40 or any(c not in "0123456789abcdef" for c in candidate):
            return None
        if commit is not None and candidate != commit:
            return None
        commit = candidate
    repository = "https://github.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017"
    return {"commit": commit, "source": repository + "/tree/" + commit,
            "zip": repository + "/archive/" + commit + ".zip"}

st.set_page_config(page_title=WORDS['title'],page_icon='📦',layout='wide')
st.title(WORDS['title'])
edition=editions.select_edition(DATA_DIR)
meta=editions.result_metadata(DATA_DIR,edition)
st.caption(WORDS['id']+': '+meta['edition_label']+' · '+meta['signature'][:12])
st.write(WORDS['note'])

st.subheader(GUIDANCE['title'])
st.write(GUIDANCE['raw'])
st.markdown(GUIDANCE['steps'])
st.caption(GUIDANCE['legacy'])
st.caption(GUIDANCE['custom'])
manual_page = next((APP_DIR / 'pages').glob('1_*.py')).relative_to(APP_DIR).as_posix()
st.page_link(manual_page, label=GUIDANCE['manual_link'], icon='🔧')
source_links = _matching_source_links()
if source_links:
    st.caption(GUIDANCE['source_note'] + ': ' + source_links['commit'][:12])
    st.markdown(f"[{GUIDANCE['source']}]({source_links['source']}) · [{GUIDANCE['zip']}]({source_links['zip']})")
else:
    st.caption(GUIDANCE['source_missing'])

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
st.caption(GUIDANCE['bundled_note'])
csv=editions.resolve_path(DATA_DIR,'kanji_csv',edition)
st.download_button(WORDS['csv'],csv.read_bytes(),
                   file_name=editions.download_filename('kanji_assignments',meta,'csv'),mime='text/csv')
for path in (editions.resolve_path(DATA_DIR,'ruby_csv',edition), DATA_DIR/'分解設定.json',
             DATA_DIR/'word_anno.json',DATA_DIR/'E_stem.json',DATA_DIR/'user_corrections.json'):
    if path.exists():
        label = GUIDANCE['bundled'] + ' · user_corrections.json' if path.name == 'user_corrections.json' else path.name
        st.download_button(label,path.read_bytes(),file_name=path.name)
manifest=ROOT/'assignment_editions/legacy/manifest.json'
manifest_url=editions.pinned_asset_url(DATA_DIR,manifest)
if manifest_url:
    st.markdown(f"[{WORDS['manifest']}]({manifest_url})")
