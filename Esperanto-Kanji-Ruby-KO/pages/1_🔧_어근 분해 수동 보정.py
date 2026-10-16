# -*- coding: utf-8 -*-
"""
페이지「어근 분해 수동 보정」

어떤 에스페란토 단어의 어근 분해가 잘못되었을 때(예: sporti → s/port/i), GUI에서 올바른
분해(예: sport/i)를 입력하기만 하면 즉시 수정할 수 있다. 50MB의 치환용 JSON을 재생성할
필요가 없다.

원리(경량 overlay):
  - 여기서 저장한 보정은 app_data/user_corrections.json 에 누적된다.
  - 메인 페이지(변환)는 시작 시 이 파일을 읽어, 루비(ruby)·한자 두 모드 모두에서 최우선으로 적용한다.
  - 보정은 「그 단어 정확히」에만 적용(고정형)되므로, 부분 문자열을 공유하는 다른 단어
    (예: sportisto)를 깨뜨리지 않는다.
"""
import streamlit as st
import json, re, os

# CWD가 저장소 루트여도 './app_data/...'를 해석할 수 있도록 앱(pages의 상위) 디렉터리로 고정.
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from esp_text_replacement_module import (
    import_placeholders,
    orchestrate_comprehensive_esperanto_text_replacement,
)
from esp_replacement_json_make_module import convert_to_circumflex
import esp_overlay_module as ov

DATA = "./app_data"
RUBY_JSON = DATA + "/置換リスト_ルビ.json"
KANJI_JSON = DATA + "/置換リスト_漢字.json"
RUBY_FMT = "HTML格式_Ruby文字_大小调整"
KANJI_FMT = "HTML格式_Ruby文字_大小调整_汉字替换"

st.set_page_config(page_title="어근 분해 수동 보정", page_icon="🔧", layout="wide")
st.title("어근 분해 수동 보정 (GUI에서 간단히 수정)")

with st.expander("사용 방법", expanded=True):
    st.markdown(
        """
        1. **단어**를 입력하고 「현재 분해 보기」를 누르면, 앱이 지금 어떻게 분해하는지 확인할 수 있습니다.
        2. 분해가 잘못되었으면 `어근/어근/어미` 형식(슬래시 구분)으로 **올바른 분해**를 입력합니다.
           - 예: `sporti` 가 `s/port/i` 로 잘못 분해됨 → 올바르게는 `sport/i`
           - 슬래시를 제거한 문자열이 원래 단어와 일치해야 합니다.
           - cx 표기(`c^`, `sx` 등)나 대문자가 섞여 있어도 됩니다(자동으로 곡절 문자와 소문자로 변환됩니다).
        3. 「**이 보정 저장**」을 누르면, 루비·한자 두 모드에 즉시 반영됩니다
           (치환용 JSON 재생성 불필요).
        4. 저장한 보정은 아래 목록에서 언제든지 삭제할 수 있습니다.

        ※ 각 어근의 번역/한자는 앱에 내장된 어근 사전(CSV)에 등록된 것이 사용됩니다.
        사전에 없는 어근이나 문법 어미(i, o, a, e, n …)는 번역 없이 그대로 표시됩니다.
        """
    )


@st.cache_data(show_spinner="치환 리스트를 읽는 중…")
def _load_lists(path):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return (
        d.get("局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", []),
        d.get("二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", []),
        d.get("全域替换用のリスト(列表)型配列(replacements_final_list)", []),
    )


_PS = import_placeholders(DATA + "/placeholders_skip.txt")
_PL = import_placeholders(DATA + "/placeholders_localcapture.txt")


def _decompose(word, json_path, fmt, mode):
    GL, G2, GG = _load_lists(json_path)
    GG = ov.merge_overlay(GG, ov.load_overlay_entries(DATA, mode))
    h = orchestrate_comprehensive_esperanto_text_replacement(" " + word + " ", _PS, GL, _PL, GG, G2, fmt)
    toks, pos = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", h):
        for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:mm.start()]), re.I):
            toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:]), re.I):
        toks.append(ch)
    return "/".join(toks)


# ============ 1) 현재 분해 확인 ============
st.header("1. 현재 분해 확인")
word_in = st.text_input("단어 입력 (예: sporti)", key="word_probe").strip()
if st.button("현재 분해 보기") and word_in:
    w = convert_to_circumflex(word_in).lower()
    try:
        rb = _decompose(w, RUBY_JSON, RUBY_FMT, "ruby")
        kj = _decompose(w, KANJI_JSON, KANJI_FMT, "kanji")
        st.write(f"**루비(ruby) 모드 분해**: `{rb}`")
        st.write(f"**한자 모드 분해**: `{kj}`")
        with st.expander("👀 실제 표시 보기(루비/한자)", expanded=False):
            import streamlit.components.v1 as _components
            _GLr, _G2r, _GGr = _load_lists(RUBY_JSON)
            _GGr = ov.merge_overlay(_GGr, ov.load_overlay_entries(DATA, "ruby"))
            _hr = orchestrate_comprehensive_esperanto_text_replacement(" " + w + " ", _PS, _GLr, _PL, _GGr, _G2r, RUBY_FMT)
            from esp_text_replacement_module import apply_ruby_html_header_and_footer as _hf
            _components.html(_hf(_hr, RUBY_FMT), height=90, scrolling=True)
        st.session_state["probe_word"] = w
        st.session_state["probe_ruby"] = rb
    except Exception as e:
        st.error(f"분해 확인 실패: {e}")

# ============ 2) 올바른 분해 입력 후 저장 ============
st.header("2. 올바른 분해를 입력하여 보정 저장")
default_decomp = st.session_state.get("probe_ruby", "")
decomp_in = st.text_input(
    "올바른 분해 (슬래시 구분, 예: sport/i)", value=default_decomp, key="decomp_in"
).strip()

if decomp_in:
    norm_decomp = convert_to_circumflex(decomp_in).lower()
    word_of_decomp = norm_decomp.replace("/", "").replace(" ", "")
    try:
        segs = ov.segment_glosses(norm_decomp, DATA)
        rows = []
        for seg, rhtml, khtml in segs:
            rgloss = re.sub(r"<[^>]+>", "", rhtml).replace(seg, "", 1) if rhtml else "—(번역 없음)"
            kgloss = re.sub(r"<[^>]+>", "", khtml).replace(seg, "", 1) if khtml else "—(한자 없음)"
            rows.append({"어근": seg, "번역": rgloss, "한자": kgloss})
        st.table(rows)
    except Exception as e:
        st.warning(f"미리보기 생성 실패: {e}")

    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"슬래시 제거 후 단어: `{word_of_decomp}`")
    with col2:
        if st.button("✅ 이 보정 저장", type="primary"):
            try:
                entry = ov.add_correction(DATA, norm_decomp)
                _load_lists.clear()
                st.success(
                    f"보정을 저장했습니다: `{entry['word']}` → `{entry['decomp']}`  "
                    "(루비·한자 두 모드에 즉시 반영. 메인 페이지(변환)에서 확인 가능)"
                )
            except Exception as e:
                st.error(f"저장 실패: {e}")

# ============ 3) 저장된 보정 목록 ============
st.header("3. 저장된 보정 목록")
cors = ov.load_corrections(DATA)
if not cors:
    st.info("아직 보정이 없습니다.")
else:
    st.caption(f"{len(cors)}건의 보정이 적용 중입니다(메인 페이지(변환)에 자동 적용).")
    for c in cors:
        c1, c2, c3 = st.columns([3, 5, 2])
        c1.write(f"**{c.get('word','')}**")
        c2.write(f"→ `{c.get('decomp','')}`")
        if c3.button("삭제", key="del_" + c.get("word", "")):
            ov.remove_correction(DATA, c.get("word", ""))
            st.rerun()

    st.download_button(
        "⬇ 보정 목록(user_corrections.json) 다운로드",
        data=json.dumps(cors, ensure_ascii=False, indent=1).encode("utf-8"),
        file_name="user_corrections.json",
        mime="application/json",
    )

# ============ 4) 보정 파일 불러오기（복원 / 3개 앱 간 이식） ============
st.header("4. 보정 파일 불러오기（백업 복원 / 3개 앱 간 공유）")
st.markdown(
    """
    보관 중인 `user_corrections.json` 의 **읽기 입구는 2곳**이며, 어느 쪽이든 동일하게 적용됩니다:

    | 읽기 입구 | 적합한 용도 |
    |---|---|
    | **메인 페이지(변환)의 「📂 수동 보정 파일 불러오기」** | 변환만 하고 싶을 때(최단·추천) |
    | **이 페이지(여기)** | 불러온 보정의 **목록 확인·개별 삭제·재다운로드** 등 관리할 때 |

    - **Streamlit Cloud 에서는 보정이 세션 종료 시 사라집니다**. 다운로드해 보관하고 다음에 위 두 곳
      중 한 곳에서 불러오세요(관리자에게 보내 commit 되면 모두를 위한 베이스라인으로 영구화됩니다).
    - 불러올 때 각 어근의 번역/한자는 **이 앱의 사전으로 다시 생성**하므로, 일본어판에서 만든
      보정을 중문판・한국어판으로 그대로 이식할 수 있습니다(분해 방식만 활용).
    """
)
up = st.file_uploader("user_corrections.json 선택", type="json", key="cor_upload")
if up is not None:
    try:
        data = json.load(up)
        decomps = [c.get("decomp") for c in data if isinstance(c, dict) and c.get("decomp")]
        st.write(f"불러올 보정: **{len(decomps)}건**  예: {', '.join(decomps[:8])}")
        if st.button("⬆ 이 내용으로 복원（현재 보정을 교체）"):
            new = []
            for d in decomps:
                try:
                    new.append(ov.build_correction(d, DATA))
                except Exception:
                    pass
            if not new:
                st.error("유효한 보정이 0건이었습니다. 파일 형식을 확인해 주세요(현재 보정은 변경되지 않았습니다).")
                st.stop()
            ov.save_corrections(DATA, new)
            st.success(f"{len(new)}건의 보정을 복원했습니다.")
            st.rerun()
    except Exception as e:
        st.error(f"불러오기 실패: {e}")
