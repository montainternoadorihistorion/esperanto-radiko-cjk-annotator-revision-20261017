"""Explicitly copy a current diagnosis into an empty, unsaved manual draft."""
import hashlib
import json
from pathlib import Path
import re

import streamlit as st

import esp_assignment_edition as editions
import esp_overlay_module as overlay
from esp_replacement_json_make_module import convert_to_circumflex


SNAPSHOT_KEY = "_manual_draft_diagnosis"
NOTICE_KEY = "_manual_draft_notice"
DRAFT_KEEP_KEY = "_manual_draft_text"
_WORD = re.compile(r"[a-zĉĝĥĵŝŭ]+")
LABELS = {
    "JA": {
        "button": "この診断を空の下書きに取り込む",
        "ready": "下書きにコピーします。補正としての保存は、下の保存ボタンで行います。",
        "no_diagnosis": "取り込むには、上で単語を診断してください。",
        "draft_not_empty": "入力済みの下書きを保持しています。取り込みは空欄のときだけ使えます。",
        "single_word": "取り込みは単語だけの診断に対応します。@・%を含む入力や複数の単語は対象外です。",
        "target_changed": "診断後に対象語が変わりました。現在の単語をもう一度診断してください。",
        "context_changed": "診断時と版・データ・補正が一致しません。もう一度診断してください。",
        "invalid_decomposition": "診断の分解と対象語が一致しないため取り込めません。もう一度確認してください。",
        "copied": "診断を下書きに取り込みました。まだ補正として保存していません。",
    },
    "ZH": {
        "button": "将此诊断填入空白草稿",
        "ready": "仅复制到草稿。要将其保存为校正，请使用下方的保存按钮。",
        "no_diagnosis": "请先在上方诊断一个单词。",
        "draft_not_empty": "已保留现有草稿。只有草稿为空时才能填入诊断。",
        "single_word": "仅支持单个单词的诊断；含@、%或多个单词的输入不能填入。",
        "target_changed": "诊断后目标词已改变，请重新诊断当前单词。",
        "context_changed": "版本、数据或校正与诊断时不一致，请重新诊断。",
        "invalid_decomposition": "诊断分解与目标词不一致，无法填入，请重新确认。",
        "copied": "诊断已填入草稿，尚未保存为校正。",
    },
    "KO": {
        "button": "이 진단을 빈 초안에 넣기",
        "ready": "초안에만 복사합니다. 보정으로 저장하려면 아래 저장 버튼을 사용하세요.",
        "no_diagnosis": "먼저 위에서 단어를 진단해 주세요.",
        "draft_not_empty": "입력한 초안을 유지합니다. 초안이 비어 있을 때만 진단을 넣을 수 있습니다.",
        "single_word": "단일 단어의 진단만 가져올 수 있습니다. @·%가 포함된 입력이나 여러 단어는 제외됩니다.",
        "target_changed": "진단 후 대상 단어가 바뀌었습니다. 현재 단어를 다시 진단해 주세요.",
        "context_changed": "판·데이터·보정이 진단 당시와 다릅니다. 다시 진단해 주세요.",
        "invalid_decomposition": "진단된 분해와 대상 단어가 일치하지 않아 가져올 수 없습니다. 다시 확인해 주세요.",
        "copied": "진단을 초안에 넣었습니다. 아직 보정으로 저장하지 않았습니다.",
    },
}


def _normalize_word(value):
    return convert_to_circumflex(value.strip()).lower() if isinstance(value, str) else ""


def context_signature(data_dir, edition):
    """Bind the candidate to the real selected data and effective corrections."""
    payload = {
        "data_dir": str(Path(data_dir).resolve()),
        "edition": edition,
        "data_signature": editions.edition_signature(data_dir, edition),
        "placeholders": {name: editions.file_hash(Path(data_dir) / name)
                         for name in ("placeholders_skip.txt", "placeholders_localcapture.txt")},
        # Include complete effective entries, including compatibility entries
        # without a decomposition, rather than only their word/decomp fields.
        "corrections": overlay.load_corrections(data_dir),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def begin_diagnosis(data_dir, edition):
    """A failed new diagnosis must not leave an earlier import candidate active."""
    st.session_state.pop(SNAPSHOT_KEY, None)
    st.session_state.pop(NOTICE_KEY, None)
    try:
        return context_signature(data_dir, edition)
    except (OSError, ValueError, TypeError):
        return None  # Fingerprint failure disables import, not the existing diagnosis.


def remember_diagnosis(data_dir, edition, word, decomposition, before_signature):
    """Do not retain a candidate if its data changed while it was rendered."""
    try:
        after_signature = context_signature(data_dir, edition)
    except (OSError, ValueError, TypeError):
        after_signature = None
    if before_signature is None or after_signature is None or before_signature != after_signature:
        st.session_state.pop(SNAPSHOT_KEY, None)
        return False
    st.session_state[SNAPSHOT_KEY] = {
        "word": _normalize_word(word), "decomposition": decomposition,
        "edition": edition, "context_signature": after_signature,
    }
    return True


def availability(data_dir, edition):
    # Only the truly empty widget may be changed. Preserve even a whitespace draft.
    if st.session_state.get("decomp_in", "") != "":
        return "draft_not_empty"
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if not isinstance(snapshot, dict):
        return "no_diagnosis"
    word = _normalize_word(st.session_state.get("word_probe", ""))
    if not _WORD.fullmatch(word):
        return "single_word"
    if snapshot.get("word") != word:
        return "target_changed"
    if snapshot.get("edition") != edition:
        return "context_changed"
    decomposition = snapshot.get("decomposition")
    if not isinstance(decomposition, str):
        return "invalid_decomposition"
    pieces = decomposition.split("/")
    if not all(_WORD.fullmatch(piece) for piece in pieces) or "".join(pieces) != word:
        return "invalid_decomposition"
    try:
        if snapshot.get("context_signature") != context_signature(data_dir, edition):
            return "context_changed"
    except (OSError, ValueError, TypeError):
        return "context_changed"
    return "ready"


def remember_draft():
    """Retain only the actual draft when Streamlit cleans up page widgets."""
    st.session_state[DRAFT_KEEP_KEY] = st.session_state.get("decomp_in", "")


def prepare_draft():
    if "decomp_in" not in st.session_state:
        st.session_state["decomp_in"] = st.session_state.get(DRAFT_KEEP_KEY, "")
    remember_draft()


def import_diagnosis(data_dir):
    """Button callback: validate again before updating only the draft widget."""
    edition = st.session_state.get("_assignment_edition_widget",
                                   st.session_state.get("assignment_edition"))
    status = availability(data_dir, edition)
    if status == "ready":
        st.session_state["decomp_in"] = st.session_state[SNAPSHOT_KEY]["decomposition"]
        remember_draft()
        status = "copied"
    st.session_state[NOTICE_KEY] = status


def render_import_control(data_dir, edition):
    """Render before the draft widget; clicking never saves a correction."""
    prepare_draft()
    words = LABELS[editions.language(data_dir)]
    notice = st.session_state.pop(NOTICE_KEY, None)
    if notice in words:
        (st.success if notice == "copied" else st.info)(words[notice])
    status = availability(data_dir, edition)
    st.button(words["button"], key="import_diagnosis_to_draft",
              disabled=(status != "ready"), on_click=import_diagnosis,
              args=(data_dir,))
    st.caption(words[status])
