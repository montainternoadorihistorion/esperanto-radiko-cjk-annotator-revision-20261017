# -*- coding: utf-8 -*-
import streamlit as st
import os
from urllib.parse import quote

# Resolve data from this file without changing Streamlit's working directory.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "app_data")
REPO_DIR = os.path.dirname(APP_DIR)
st.set_page_config(page_title="最新データのダウンロード", page_icon="📦", layout="wide")
st.title("最新データのダウンロード")
st.markdown("""このアプリが**いま実際に使っている最新データ**を入手できます(古い標本はありません)。大容量JSONはGitHub(main)の直リンクです。""")


def _mb(rel):
    try:
        path = os.path.join(REPO_DIR, rel)
        if os.path.exists(path):
            return f" ({os.path.getsize(path)/1e6:.0f}MB)"
    except Exception:
        pass
    return ""

RAW = "https://raw.githubusercontent.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017/main/"

st.header("① 置換用 大JSON(最新)")
rows = ["| 種類 | ダウンロード |", "|---|---|"]
for label, rel in [('注釈ルビJSON(日本語)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_ルビ.json'), ('注釈ルビJSON(中文)', 'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_ルビ.json'), ('注釈ルビJSON(한국어)', 'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_ルビ.json'), ('漢字化JSON(HTMLルビ形式・3言語共通)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字.json'), ('漢字化JSON(純粋置換・タグなし)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字_純粋置換.json')]:
    rows.append("| " + label + " | [" + rel.split("/")[-1] + "](" + RAW + quote(rel) + ")" + _mb(rel) + " |")
st.markdown("\n".join(rows))

st.header("② このアプリの辞書・設定(最新)")
for rel in ["app_data/エスペラント語根-日本語訳ルビ対応リスト.csv", "app_data/分解設定.json", "app_data/word_anno.json", "app_data/E_stem.json"]:
    path = os.path.join(APP_DIR, rel)
    if os.path.exists(path):
        with open(path, "rb") as f:
            st.download_button("⬇ " + os.path.basename(rel), f.read(), file_name=os.path.basename(rel))

st.header("③ 承認済み手動補正ベースライン")
p = os.path.join(DATA_DIR, "user_corrections.json")
if os.path.exists(p):
    with open(p, "rb") as f:
        st.download_button("⬇ user_corrections.json", f.read(), file_name="user_corrections.json")
else:
    st.info("(ベースラインなし)")

st.markdown("""※ 漢字化JSONは3言語で同一(漢字割り当てはマスター共有、ルビはエスペラント語根)のため1本です。純粋置換版はHTMLタグを含まないテキスト→テキスト置換で、独自スクリプトから使えます。""")
