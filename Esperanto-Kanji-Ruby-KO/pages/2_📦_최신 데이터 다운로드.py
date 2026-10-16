# -*- coding: utf-8 -*-
import streamlit as st
import os
from urllib.parse import quote

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
st.set_page_config(page_title="최신 데이터 다운로드", page_icon="📦", layout="wide")
st.title("최신 데이터 다운로드")
st.markdown("""이 앱이 **현재 실제로 사용 중인 최신 데이터**를 받을 수 있습니다(오래된 샘플 없음). 대용량 JSON은 GitHub(main) 직링크입니다.""")


def _mb(rel):
    try:
        for base in (".", ".."):
            pp = os.path.join(base, rel) if base == ".." else rel
            if os.path.exists(pp):
                return f" ({os.path.getsize(pp)/1e6:.0f}MB)"
    except Exception:
        pass
    return ""

RAW = "https://raw.githubusercontent.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017/main/"

st.header("① 치환용 대형 JSON(최신)")
rows = ["| 종류 | 다운로드 |", "|---|---|"]
for label, rel in [('주석 루비 JSON(일본어)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_ルビ.json'), ('주석 루비 JSON(중국어)', 'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_ルビ.json'), ('주석 루비 JSON(한국어)', 'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_ルビ.json'), ('한자화 JSON(HTML 루비 형식·3개 언어 공통)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字.json'), ('한자화 JSON(순수 치환·태그 없음)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字_純粋置換.json')]:
    rows.append("| " + label + " | [" + rel.split("/")[-1] + "](" + RAW + quote(rel) + ")" + _mb(os.path.join("..", rel)) + " |")
st.markdown("\n".join(rows))

st.header("② 이 앱의 사전·설정(최신)")
for rel in ["app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv", "app_data/分解設定.json", "app_data/word_anno.json", "app_data/E_stem.json"]:
    if os.path.exists(rel):
        with open(rel, "rb") as f:
            st.download_button("⬇ " + os.path.basename(rel), f.read(), file_name=os.path.basename(rel))

st.header("③ 승인된 수동 보정 베이스라인")
p = "app_data/user_corrections.json"
if os.path.exists(p):
    with open(p, "rb") as f:
        st.download_button("⬇ user_corrections.json", f.read(), file_name="user_corrections.json")
else:
    st.info("(베이스라인 없음)")

st.markdown("""※ 한자화 JSON은 3개 언어 동일(한자 배정 마스터 공유)이므로 1개입니다. 순수 치환판은 HTML 태그 없이 텍스트→텍스트 치환으로, 자체 스크립트에서 사용할 수 있습니다.""")
