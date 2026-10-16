# -*- coding: utf-8 -*-
import streamlit as st
import os
from urllib.parse import quote

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
st.set_page_config(page_title="最新数据下载", page_icon="📦", layout="wide")
st.title("最新数据下载")
st.markdown("""可获取本应用**当前实际使用的最新数据**(无旧样本)。大型JSON为GitHub(main)直链。""")


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

st.header("① 替换用大JSON(最新)")
rows = ["| 类型 | 下载 |", "|---|---|"]
for label, rel in [('注释Ruby JSON(日语)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_ルビ.json'), ('注释Ruby JSON(中文)', 'Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_ルビ.json'), ('注释Ruby JSON(韩语)', 'Esperanto-Kanji-Ruby-KO/app_data/置換リスト_ルビ.json'), ('汉字化JSON(HTML Ruby格式·三语共用)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字.json'), ('汉字化JSON(纯替换·无标签)', 'Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字_純粋置換.json')]:
    rows.append("| " + label + " | [" + rel.split("/")[-1] + "](" + RAW + quote(rel) + ")" + _mb(os.path.join("..", rel)) + " |")
st.markdown("\n".join(rows))

st.header("② 本应用的词典·设置(最新)")
for rel in ["app_data/世界语词根-中文注释对应列表.csv", "app_data/分解設定.json", "app_data/word_anno.json", "app_data/E_stem.json"]:
    if os.path.exists(rel):
        with open(rel, "rb") as f:
            st.download_button("⬇ " + os.path.basename(rel), f.read(), file_name=os.path.basename(rel))

st.header("③ 已批准的手动校正基线")
p = "app_data/user_corrections.json"
if os.path.exists(p):
    with open(p, "rb") as f:
        st.download_button("⬇ user_corrections.json", f.read(), file_name="user_corrections.json")
else:
    st.info("(暂无已批准的基线文件)")

st.markdown("""※ 汉字化JSON三语相同(汉字分配共用主表)故只有1份。纯替换版不含HTML标签,可用于自定义脚本。""")
