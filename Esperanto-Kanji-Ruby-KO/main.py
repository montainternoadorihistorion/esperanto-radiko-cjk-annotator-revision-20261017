##  main.py(1つ目)
# main.py (メインの Streamlit アプリ/機能拡充版202502)

import streamlit as st
import re
import io
import json
import pandas as pd  # 必要なら使う
from typing import List, Dict, Tuple, Optional
import streamlit.components.v1 as components
import os

# Resolve data from this file without changing Streamlit's working directory.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "app_data")
REPO_DIR = os.path.dirname(APP_DIR)

import multiprocessing

#=================================================================
# Streamlit で multiprocessing を使う際、PicklingError 回避のため
# 明示的に 'spawn' モードを設定する必要がある。
#=================================================================
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass  # すでに start method が設定済みの場合はここで無視する

#=================================================================
# エスペラント文の(漢字)置換・ルビ振りなどを行う独自モジュールから
# 関数をインポートする。
# esp_text_replacement_module.py内に定義されているツールをまとめて呼び出す
#=================================================================
from esp_text_replacement_module import (
    x_to_circumflex,
    x_to_hat,
    hat_to_circumflex,
    circumflex_to_hat,
    replace_esperanto_chars,
    import_placeholders,
    orchestrate_comprehensive_esperanto_text_replacement,
    parallel_process,
    apply_ruby_html_header_and_footer,
    circumflex_to_x, hat_to_x,
)

#=================================================================
# Streamlit の @st.cache_data デコレータを使い、読み込み結果をキャッシュして
# JSONファイルのロード高速化を図る。大きなJSON(50MB程度)を都度読むと遅いので、
# ここで呼び出す関数をキャッシュする作り。
#=================================================================
@st.cache_data
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    """
    JSONファイルをロードし、以下の3つのリストをタプルとして返す:
    1) replacements_final_list
    2) replacements_list_for_localized_string
    3) replacements_list_for_2char
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    replacements_final_list = data.get(
        "全域替换用のリスト(列表)型配列(replacements_final_list)", []
    )
    replacements_list_for_localized_string = data.get(
        "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", []
    )
    replacements_list_for_2char = data.get(
        "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", []
    )
    return (
        replacements_final_list,
        replacements_list_for_localized_string,
        replacements_list_for_2char,
    )

#=================================================================
# Streamlit ページの見た目設定
# page_title: ブラウザタブに表示されるタイトル
# layout="wide" で横幅を広く使えるUIにする
#=================================================================
st.set_page_config(page_title="에스페란토 문장 주석 루비·한자화 도구", page_icon="📖", layout="wide")

# タイトル部分
st.title("에스페란토 문장 주석 루비·한자화 도구")
st.caption("어근별 한국어 주석 루비 표시 / 한자 치환(루비 포함·순수 텍스트)")
st.markdown("📘 [**프로젝트 빠른 가이드**](https://takatakatake.github.io/kanji_assign/index.ko.html) — 어근 분해·한자 할당·각 앱의 전체 구조를 한 페이지로(日本語/中文/한국어 전환 가능)")
st.write("---")

#=================================================================
# 1) JSONファイル (置換ルール) をロード
#   (デフォルトを使うか、ユーザーがアップロードするかの選択)
#=================================================================
selected_option = st.radio(
    "변환 모드 선택:",
    ("📖 주석 루비（어근 위에 한국어 주석）", "🈶 한자화（한자＋어근 루비）", "✂️ 한자화·순수 치환（태그 없는 텍스트）", "📤 사용자 JSON 사용（고급）")
)

st.caption("처음이라면 기본값인 **「📖 주석 루비」** 그대로 진행하세요(원문은 그대로, 어근 위에 한국어 주석이 표시됩니다).")

if "🈶" in selected_option or "✂️" in selected_option:
    st.caption("💡 한자 모드에서는 한자 오른쪽 위에 작은 글자(예: 扩ᴬᴷ, 金ⱽ, 员ᴬ)가 붙을 수 있습니다. 같은 한자를 여러 어근이 공유할 때의 **구별 표시**(어근 철자에서 유래)로, 어근을 판별하는 데 도움이 됩니다.")

# Streamlit の折りたたみ (expander) でサンプルJSONのダウンロードを案内
#=================================================================
# 置換ルールとして使うリスト3種を初期化しておく。
# (JSONファイル読み込み後に代入される)
#=================================================================
replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

# JSONファイルの読み込み方を分岐
if selected_option == "📖 주석 루비（어근 위에 한국어 주석）":
    default_json_path = os.path.join(DATA_DIR, '置換リスト_ルビ.json')
    try:
        (replacements_final_list,
         replacements_list_for_localized_string,
         replacements_list_for_2char) = load_replacements_lists(default_json_path)
        st.success("✅ 주석 루비 모드 준비 완료.")
    except Exception as e:
        st.error(f"JSON 파일 불러오기에 실패했습니다: {e}")
        st.stop()
elif selected_option == "🈶 한자화（한자＋어근 루비）":
    kanji_json_path = os.path.join(DATA_DIR, '置換リスト_漢字.json')
    try:
        (replacements_final_list,
         replacements_list_for_localized_string,
         replacements_list_for_2char) = load_replacements_lists(kanji_json_path)
        st.success("✅ 한자화 모드 준비 완료(한자 본문·어근 루비).")
    except Exception as e:
        st.error(f"한자화 버전 JSON 불러오기에 실패했습니다: {e}")
        st.stop()
elif selected_option == "✂️ 한자화·순수 치환（태그 없는 텍스트）":
    pure_json_path = os.path.join(REPO_DIR, "Esperanto-Kanji-Ruby-JA", "app_data", "置換リスト_漢字_純粋置換.json")
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(pure_json_path)
        st.success("순수 치환판 JSON을 불러왔습니다. 에스페란토 문장이 태그 없는 한자 텍스트로 변환됩니다(예: amikeco → 友性o).")
    except Exception as e:
        st.error(f"순수 치환판 JSON 불러오기에 실패했습니다: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("3개의 JSON을 병합한 치환용 .json 파일을 업로드해 주세요(파일명이 「○○(合并3个JSON文件).json」 형태)", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("업로드한 JSON을 성공적으로 불러왔습니다.")
            if not (replacements_final_list or replacements_list_for_localized_string or replacements_list_for_2char):
                st.error("이 JSON에서 치환 규칙을 찾을 수 없습니다(키 이름이 예상과 다를 수 있음). 「合并3个JSON文件」 형식인지 확인해 주세요.")
            _probe = next((e[1] for e in replacements_final_list[:200] if isinstance(e, (list, tuple)) and len(e) >= 2 and isinstance(e[1], str) and e[1].strip()), "")
            if "<ruby>" in _probe:
                st.caption("🔍 감지: 이 JSON은 **HTML 루비 형식**인 듯합니다 → 아래 출력 형식은 「HTML 루비 형식」계열을 선택하세요.")
            elif _probe:
                st.caption("🔍 감지: 이 JSON은 **태그 없는 형식**인 듯합니다 → 아래 출력 형식은 「괄호 형식」또는「단순 치환」을 선택하세요.")
        except Exception as e:
            st.error(f"업로드한 JSON 파일 불러오기에 실패했습니다: {e}")
            st.stop()
    else:
        st.warning("JSON 파일이 업로드되지 않았습니다. 처리를 중단합니다.")
        st.stop()

# 1.5) 수동 보정(경량 overlay)을 최우선으로 적용
#   「어근 분해 수동 보정」페이지에서 저장한 보정(app_data/user_corrections.json)을,
#   치환용 JSON을 재생성하지 않고 실행 시점에 반영한다.
# 1.4) 로컬 user_corrections.json 을 이 세션에 불러오기(선택)
with st.expander("📂 수동 보정 파일(user_corrections.json) 불러오기(선택)"):
    st.caption("「어근 분해 수동 보정」페이지에서 다운로드한 보정을 이 세션에 적용합니다(다른 사용자에게 영향 없음).")
    _cor_up = st.file_uploader("user_corrections.json", type="json", key="main_cor_upload")
    if _cor_up is not None and st.session_state.get("main_cor_loaded") != getattr(_cor_up, "file_id", True):
        try:
            import esp_overlay_module as _ovu
            _decs = [c.get("decomp") for c in json.load(_cor_up) if isinstance(c, dict) and c.get("decomp")]
            _new = []
            for _dc in _decs:
                try: _new.append(_ovu.build_correction(_dc, DATA_DIR))
                except Exception: pass
            if _new:
                _ovu.save_corrections(DATA_DIR, _new)
            else:
                st.error("유효한 보정이 0건이었습니다. 「어근 분해 수동 보정」 페이지에서 다운로드한 user_corrections.json 파일인지 확인해 주세요(현재 보정은 변경되지 않았습니다).")
            st.session_state["main_cor_loaded"] = getattr(_cor_up, "file_id", True)
            st.success(f"{len(_new)} 건의 보정을 이 세션에 적용했습니다.") if _new else None
        except Exception as _e:
            st.error(f"불러오기 실패({_e}). 「어근 분해 수동 보정」 페이지에서 다운로드한 user_corrections.json 파일인지 확인해 주세요.")

try:
    import esp_overlay_module as _ov
    _ov_mode = "kanji" if selected_option in ("🈶 한자화（한자＋어근 루비）", "✂️ 한자화·순수 치환（태그 없는 텍스트）") else "ruby"
    _ov_entries_raw = _ov.load_overlay_entries(DATA_DIR, _ov_mode)
    if selected_option == "✂️ 한자화·순수 치환（태그 없는 텍스트）":
        import re as _re_ov
        _ov_entries = [[o, _re_ov.sub(r"</?ruby>", "", _re_ov.sub(r"<rt[^>]*>.*?</rt>", "", n, flags=_re_ov.DOTALL | _re_ov.IGNORECASE), flags=_re_ov.IGNORECASE), ph] for o, n, ph in _ov_entries_raw]
    else:
        _ov_entries = _ov_entries_raw
    if _ov_entries and not str(selected_option).startswith("📤"):
        # 自作JSONモードは形式が不明のため補正オーバーレイ(HTML)は適用しない
        replacements_final_list = _ov.merge_overlay(replacements_final_list, _ov_entries)
        st.info(f"어근 분해 품질 보정 데이터 {len(_ov.load_corrections(DATA_DIR))}건을 자동 적용 중입니다(**조작 불필요**. 내용은 「어근 분해 수동 보정」 페이지에서 확인·편집할 수 있습니다).")
except Exception:
    pass

#=================================================================
# 2) placeholders (占位符) の読み込み
#    %...% や @...@ で囲った文字列を守るために使用する文字列群を読み込む
#=================================================================
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    os.path.join(DATA_DIR, 'placeholders_skip.txt')
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    os.path.join(DATA_DIR, 'placeholders_localcapture.txt')
)

st.write("---")

#=================================================================
# 設定パラメータ (UI) - 高度な設定
# 並列処理 (multiprocessing) を利用できるかどうかのスイッチと、
# 同時プロセス数の選択
#=================================================================
with st.expander("⚙️ 고급 설정(병렬 처리·보통은 변경 불필요)"):
    st.write("""
    여기에서는 문자열(한자) 치환 시에 사용할 병렬 처리 프로세스 개수를 결정합니다. 
    """)
    use_parallel = st.checkbox("병렬 처리를 사용하기", value=False)
    num_processes = st.number_input("동시 프로세스 수", min_value=2, max_value=2, value=2, step=1)
    st.caption("⚠️ 병렬 처리는 프로세스마다 치환 리스트(약 400MB)를 복제합니다. Streamlit Cloud 등 메모리가 작은 환경에서는 메모리 초과로 앱이 중지될 수 있습니다(로컬 멀티코어 PC용 기능입니다).")

st.write("---")

#=================================================================
# 例: 出力形式の選択
# (HTMLルビ形式・括弧形式・文字列のみ など)
#=================================================================

# 출력 형식: 기본 JSON 사용 시 자동 선택(조작 불필요). 업로드 JSON일 때만 수동 선택.
_FMT_CHOICES = [
    ("HTML 루비 형식·폭 조정【표준】 — 어근 위에 주석 표시: amiko → amik(위에「友」)o", "HTML格式_Ruby文字_大小调整"),
    ("HTML 루비 형식·폭 조정【한자 치환】 — 한자 본문·어근 루비: amiko → 友(위에「amik」)o", "HTML格式_Ruby文字_大小调整_汉字替换"),
    ("HTML 루비 형식·심플(폭 조정 없음)", "HTML格式"),
    ("HTML 루비 형식·심플【한자 치환】", "HTML格式_汉字替换"),
    ("괄호 형식 — 태그 없음: amiko → amik(友)o", "括弧(号)格式"),
    ("괄호 형식【한자 치환】 — 태그 없음: amiko → 友(amik)o", "括弧(号)格式_汉字替换"),
    ("단순 치환 — 주석/한자만 남김: amiko → 友o", "替换后文字列のみ(仅)保留(简单替换)"),
]
if selected_option == "📖 주석 루비（어근 위에 한국어 주석）":
    format_type = "HTML格式_Ruby文字_大小调整"
    st.info("출력 형식: **HTML 루비 형식(폭 조정)** — 기본 주석 루비 JSON에 맞춰 자동 선택됨. 어근 위에 주석이 루비로 표시됩니다.")
elif selected_option == "🈶 한자화（한자＋어근 루비）":
    format_type = "HTML格式_Ruby文字_大小调整_汉字替换"
    st.info("출력 형식: **HTML 루비 형식(한자 본문+어근 루비)** — 기본 한자화 JSON에 맞춰 자동 선택됨.")
elif selected_option == "✂️ 한자화·순수 치환（태그 없는 텍스트）":
    format_type = "替换后文字列のみ(仅)保留(简单替换)"
    st.info("출력 형식: **단순 치환(태그 없는 텍스트)** — 순수 치환 JSON에 맞춰 자동 선택됨. HTML 없이 바로 복사해 사용할 수 있습니다.")
else:
    _sel = st.selectbox(
        "출력 형식 선택 (업로드한 JSON을 **생성했을 때의 형식**에 맞추세요)",
        [label for label, _v in _FMT_CHOICES],
    )
    format_type = dict(_FMT_CHOICES)[_sel]


# フォーム外で、変数 processed_text を初期化しておく
processed_text = ""

#=================================================================
# 4) 入力テキストのソースを選択 (手動入力 or ファイルアップロード)
#=================================================================
st.subheader("입력 텍스트의 소스")
source_option = st.radio("입력 텍스트를 어떻게 하시겠습니까?", ("직접 입력", "파일 업로드"))
uploaded_text = ""

# ファイルアップロードが選択された場合
if source_option == "파일 업로드":
    text_file = st.file_uploader("텍스트 파일을 업로드하십시오 (UTF-8)", type=["txt", "csv", "md"])
    if text_file is not None:
        uploaded_text = text_file.read().decode("utf-8", errors="replace")
        st.info("파일을 불러왔습니다.")
    else:
        st.warning("텍스트 파일이 업로드되지 않았습니다. 직접 입력으로 전환하거나 파일을 업로드해 주십시오.")

#=================================================================
# フォーム: 実行ボタン(送信/キャンセル)を配置
#  - テキストエリアにエスペラント文を入力してもらう
#=================================================================
# 업로드가 있으면 폼 생성 전에 session_state 에 반영 (key 바인딩의 초기값으로)
if uploaded_text:
    # 同一ファイルの再セットは初回のみ(欄内の手動修正が毎rerunで上書き破棄されるのを防ぐ)
    _tfid = getattr(text_file, "file_id", True)
    if st.session_state.get("_last_text_upload") != _tfid:
        st.session_state["text0_value"] = uploaded_text
        st.session_state["_last_text_upload"] = _tfid

_c1, _c2 = st.columns([1, 3])
with _c1:
    st.button("📝 샘플 문장 넣기", on_click=lambda: st.session_state.update(text0_value='Saluton! Ĉu vi jam aŭdis, ke Esperanto estas internacia lingvo? Mi eĉ komencis lerni ĝin hodiaŭ, ĉar la komputilo kaj la telefono faciligas la lernadon. La amikeco inter la popoloj kreskas ĉiutage.'))
with _c2:
    st.caption("처음이신가요? 버튼을 누르면 샘플 문장이 입력되어 바로 변환을 체험할 수 있습니다.")

# st.stop経路(自作JSON未アップロード等)で text0_value がwidget cleanupで消えた場合の復元
if "text0_value" not in st.session_state and "_text0_keep" in st.session_state:
    st.session_state["text0_value"] = st.session_state["_text0_keep"]

with st.form(key='profile_form'):

    # text_area 를 key="text0_value" 로 session_state 와 양방향 바인딩한다.
    # 기존 방식(value=initial_text)은 제출 시 위젯이 이전 값으로 되돌려져
    # "제출하면 한 번은 이전 입력으로 변환된다(한 스텝 지연)" 버그의 원인이었다.
    # key= 방식은 제출 시 현재 입력이 즉시 반영된다.
    text0 = st.text_area(
        "에스페란토 문장을 입력해 주십시오",
        height=150,
        key="text0_value"
    )
    st.session_state["_text0_keep"] = text0  # st.stop経路のwidget cleanup対策(非ウィジェットキーは生存)
    st.caption("💡 모자 기호 문자는 **cx / c^ / ĉ** 어느 표기로도 입력할 수 있습니다(예: sxatas·s^atas·ŝatas). 긴 글(수천 행)은 변환에 수십 초 걸릴 수 있습니다.")

    with st.expander("🔖 부분 변환 조정(%·@ 마커)"):
        st.markdown("""
- `%...%` 로 감싼 부분은 **어근 변환을 건너뜁니다**(같은 줄에서 50자 이내. 문자 표기와 공백은 정규화됩니다).
  예: `%Universala Kongreso% okazos.`
- `@...@` 로 감싼 부분은 **국소 치환 목록으로 처리하고 양 끝의 @를 제거합니다**(같은 줄에서 단어의 일부도 지정할 수 있습니다).
  예: `@semajn@tagoj` → **semajn** 을 하나의 어근으로 국소 처리합니다. 마커 바깥의 텍스트도 일반 방식으로 변환됩니다.
- 이메일 주소의 @는 마커로 처리하지 않습니다. 문자열 전체를 유지하려면 `%...%` 를 사용하세요.
""")


    # 출力文字形式 (エスペラント特有文字の表記形式)
    letter_type = st.radio('에스페란토 문자 표기(출력)', ('ĉ ĝ ĥ ĵ ŝ ŭ (표준)', 'cx gx hx jx sx ux (x형식)', 'c^ g^ h^ j^ s^ u^ (^형식)'))

    submit_btn = st.form_submit_button('🔁 변환하기', type="primary")


    if submit_btn and not (text0 or "").strip():
        st.warning("텍스트가 비어 있습니다. 에스페란토 문장을 입력한 뒤 「변환하기」를 눌러주세요.")
        st.stop()

    if submit_btn:
        # text0 는 key="text0_value" 로 session_state 와 양방향 바인딩되어 있다.
        # 여기서 수동 대입하면 위젯 생성 후 session_state 변경이 되어 오류가 나므로 하지 않는다.

        if use_parallel:
            processed_text = parallel_process(
                text=text0,
                num_processes=num_processes,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )
        else:
            processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                text=text0,
                placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                replacements_list_for_localized_string=replacements_list_for_localized_string,
                placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                replacements_final_list=replacements_final_list,
                replacements_list_for_2char=replacements_list_for_2char,
                format_type=format_type
            )

        # 1차 결과에 「어두 1자 고립」 과분해(자음 1자 고립: fero->f/er/o 등)가 있으면,
        # 자동 보정을 최우선으로 merge 하여 2차 렌더링(메커니즘 차원에서 결함 클래스 제거). 고립 없으면 미처리.
        try:
            import esp_overlay_module as _ovx
            _afmode = "kanji" if selected_option in ("🈶 한자화（한자＋어근 루비）", "✂️ 한자화·순수 치환（태그 없는 텍스트）") else "ruby"  # sample_btn_marker
            _auto_strip_pure = (selected_option == "✂️ 한자화·순수 치환（태그 없는 텍스트）")
            _auto = _ovx.auto_overlay_entries(processed_text, DATA_DIR, _afmode)
            if _auto and _auto_strip_pure:
                import re as _re_af
                _auto = [[o, _re_af.sub(r"</?ruby>", "", _re_af.sub(r"<rt[^>]*>.*?</rt>", "", n, flags=_re_af.DOTALL | _re_af.IGNORECASE), flags=_re_af.IGNORECASE), ph] for o, n, ph in _auto]
            if _auto:
                _GGx = _ovx.merge_overlay(replacements_final_list, _auto)
                if use_parallel:
                    processed_text = parallel_process(
                        text=text0, num_processes=num_processes,
                        placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                        replacements_list_for_localized_string=replacements_list_for_localized_string,
                        placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                        replacements_final_list=_GGx,
                        replacements_list_for_2char=replacements_list_for_2char,
                        format_type=format_type)
                else:
                    processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                        text=text0,
                        placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                        replacements_list_for_localized_string=replacements_list_for_localized_string,
                        placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                        replacements_final_list=_GGx,
                        replacements_list_for_2char=replacements_list_for_2char,
                        format_type=format_type)
        except Exception:
            pass

        # letter_type에 따라 최종 에스페란토 문자 표기를 변환
        if letter_type == 'ĉ ĝ ĥ ĵ ŝ ŭ (표준)':
            processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
            processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
        elif letter_type == 'cx gx hx jx sx ux (x형식)':
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_x)
            processed_text = replace_esperanto_chars(processed_text, hat_to_x)
        elif letter_type == 'c^ g^ h^ j^ s^ u^ (^형식)':
            processed_text = replace_esperanto_chars(processed_text, x_to_hat)
            processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

        processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

        # 결과를 session_state 에 저장(재실행 시 사라지지 않도록＋결과를 편집 가능하게)
        st.session_state["result_html"] = processed_text
        st.session_state["edited_html"] = processed_text          # 편집용 초기값＝생성 결과
        st.session_state["result_is_html"] = ("HTML" in format_type)
        st.toast("✅ 변환 완료! 아래에 결과가 표시됩니다.")

#=================================================================
# フォーム外의 処理: 結果 미리보기・편집・다운로드
#=================================================================
def _reset_edited_html():
    # “편집 취소” 콜백(위젯 생성 후 session_state 변경은 오류가 나므로 콜백에서 생성 결과로 되돌림)
    st.session_state["edited_html"] = st.session_state.get("result_html", "")

if st.session_state.get("result_html"):
    # st.stop()経路(自作JSON未アップロード等)のwidget cleanupで edited_html が消えた場合の再シード
    if "edited_html" not in st.session_state:
        st.session_state["edited_html"] = st.session_state["result_html"]
    st.caption("「치환 결과(HTML 소스, 편집 가능)」탭에서 출력을 직접 수정할 수 있습니다. "
               "수정은 미리보기와 다운로드에 반영됩니다(다시 변환하면 생성 결과로 돌아갑니다).")

    # 편집 후 내용(없으면 생성 결과). 미리보기・다운로드 모두 이 내용을 사용.
    current_html = st.session_state.get("edited_html", st.session_state["result_html"])

    # 본문이 길면 미리보기만 일부 생략(편집과 다운로드는 항상 전체)
    MAX_PREVIEW_LINES = 250
    lines = current_html.splitlines()
    if len(lines) > MAX_PREVIEW_LINES:
        preview_text = "\n".join(lines[:247]) + "\n...\n" + "\n".join(lines[-3:])
        st.warning(
            f"텍스트가 길기 때문에(총 {len(lines)}줄), 미리보기는 일부만 표시합니다(편집・다운로드는 전체)."
        )
    else:
        preview_text = current_html

    if st.session_state.get("result_is_html"):
        tab1, tab2 = st.tabs(["HTML 미리보기", "치환 결과(HTML 소스, 편집 가능)"])
        with tab1:
            components.html(preview_text, height=500, scrolling=True)
        with tab2:
            st.text_area(
                "출력 HTML을 직접 편집할 수 있습니다(편집 후 미리보기와 다운로드에 반영됩니다)",
                key="edited_html",
                height=300
            )
            st.button("편집을 취소하고 생성 결과로 되돌리기", on_click=_reset_edited_html)
        download_name = "치환결과.html"
    else:
        tab3_list = st.tabs(["📋 복사용(오른쪽 위 아이콘으로 복사)", "✏️ 편집"])
        with tab3_list[0]:
            st.code(preview_text, language=None)
        with tab3_list[1]:
            st.text_area("출력을 직접 편집할 수 있습니다", key="edited_html", height=300)
            st.button("편집을 취소하고 생성 결과로 되돌리기", on_click=_reset_edited_html)
        download_name = "치환결과.txt"

    download_data = current_html.encode('utf-8')
    st.download_button(
        label="치환 결과 다운로드(편집 반영)",
        data=download_data,
        file_name=download_name,
        mime="text/html"
    )
    st.caption("※ 다운로드한 .html 파일은 **더블클릭하면 브라우저에서 루비가 표시된 상태로** 열립니다. Word 등에 붙여넣으려면 브라우저에서 연 뒤 복사하세요.")
    st.page_link("pages/1_🔧_어근 분해 수동 보정.py", label="🔧 잘못된 분해 발견 → 수동 보정 페이지에서 수정(즉시 반영)")


#=================================================================
# ページ下部に、アプリのGitHubリポジトリのリンクを表示
#=================================================================

st.write("---")
st.header("Ligilo-oj (URL-oj) / 言語版・语言版本・언어판")
st.markdown("""
#### 旧公開版 / Previous releases / 旧版 / 이전 버전
- **日本語版 (Japana)**: https://esperanto-radiko-cjk-annotator.streamlit.app/
- **中文版 (Ĉina)**: https://esperanto-radiko-cjk-annotator-zh.streamlit.app/
- **한국어판 (Korea)**: https://esperanto-radiko-cjk-annotator-ko.streamlit.app/

#### GitHub-deponejo (fontkodo & uzadaj instrukcioj) ⇓
https://github.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017
""")
