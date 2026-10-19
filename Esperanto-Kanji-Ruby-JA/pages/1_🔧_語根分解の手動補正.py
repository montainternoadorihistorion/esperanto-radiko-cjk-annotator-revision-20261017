# -*- coding: utf-8 -*-
"""
ページ「語根分解の手動補正」

エスペラント単語の語根分解が誤っているとき(例: sporti → s/port/i)、GUI上で正しい分解
(例: sport/i)を入力するだけで、即座に修正できる。50MBの置換用JSONを再生成する必要はない。

仕組み(軽量オーバーレイ):
  - ここで保存した補正は【ブラウザセッション限定】(st.session_state)。app_data/user_corrections.json は
    commit済みの承認済みベースライン(読み取り専用)で、mainページはベースライン+セッション補正を最優先適用する。
  - 補正は「その単語ちょうど」にだけ効く(固定形)ので、部分文字列を共有する別語(sportisto 等)を
    壊さない。
"""
import streamlit as st
import esp_assignment_edition as editions
import json, re, os

# Resolve data from this file without changing Streamlit's working directory.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "app_data")

from esp_text_replacement_module import (
    import_placeholders,
    orchestrate_comprehensive_esperanto_text_replacement,
)
from esp_replacement_json_make_module import convert_to_circumflex
import esp_overlay_module as ov
import esp_manual_draft as drafts

DATA = DATA_DIR
RUBY_JSON = os.path.join(DATA_DIR, '置換リスト_ルビ.json')
KANJI_JSON = os.path.join(DATA_DIR, '置換リスト_漢字.json')
RUBY_FMT = "HTML格式_Ruby文字_大小调整"
KANJI_FMT = "HTML格式_Ruby文字_大小调整_汉字替换"

st.set_page_config(page_title="語根分解の手動補正", page_icon="🔧", layout="wide")
st.title("語根分解の手動補正 (GUIで簡単に直す)")
assignment_edition = editions.select_edition(DATA_DIR)
KANJI_JSON = str(editions.resolve_path(DATA_DIR, "kanji", assignment_edition))
st.page_link('pages/2_📦_最新データのダウンロード.py', label='再現に必要なアプリソース・データの保存方法を見る', icon="📦")


with st.expander("使い方", expanded=True):
    st.markdown(
        """
        1. **単語**を入力して「現在の分解を見る」を押すと、アプリが今どう分解しているかを確認できます。
        2. 分解が誤っていれば、**正しい分解**を `語根/語根/語尾` の形(スラッシュ区切り)で入力します。
           - 例: `sporti` が `s/port/i` と誤分解される → 正しくは `sport/i`
           - スラッシュを除いた文字列が元の単語と一致している必要があります。
           - cx表記(`c^`,`sx` など)や大文字混じりでもOK(自動で字上符・小文字に調整されます)。
        3. 「**この補正を保存**」を押すと、ルビ・漢字の両モードに即座に反映されます
           (置換用JSONの再生成は不要)。
        4. 保存した補正は下の一覧でいつでも削除できます。

        ※ 各語根の訳・漢字は、アプリ同梱の語根辞書(CSV)に登録されているものが使われます。
        辞書に無い語根や文法語尾(i, o, a, e, n …)は、訳なしの裸で表示されます。
        """
    )


def _load_lists(path):
    GG, GL, G2 = editions.load_lists_path(path)
    return GL, G2, GG


_PS = import_placeholders(os.path.join(DATA_DIR, 'placeholders_skip.txt'))
_PL = import_placeholders(os.path.join(DATA_DIR, 'placeholders_localcapture.txt'))


def _render_probe(word, json_path, fmt, mode):
    """Use the main page's stored overlays and optional automatic second pass."""
    GL, G2, GG = _load_lists(json_path)
    GG = ov.merge_overlay(GG, ov.load_overlay_entries(DATA, mode, assignment_edition))
    text = " " + word + " "
    h = orchestrate_comprehensive_esperanto_text_replacement(
        text, _PS, GL, _PL, GG, G2, fmt,
        reviewed_local_decompositions=editions.supports_reviewed_local_decompositions(json_path),
    )
    try:
        automatic = ov.auto_overlay_entries(h, DATA, mode, assignment_edition)
        if automatic:
            h = orchestrate_comprehensive_esperanto_text_replacement(
                text, _PS, GL, _PL, ov.merge_overlay(GG, automatic), G2, fmt,
                reviewed_local_decompositions=editions.supports_reviewed_local_decompositions(json_path),
            )
    except Exception:
        pass  # Match main.py: an optional autofix failure retains the first pass.
    return h


def _decompose(word, json_path, fmt, mode, rendered_html=None):
    """Describe the same final HTML that the preview displays."""
    h = rendered_html if rendered_html is not None else _render_probe(word, json_path, fmt, mode)
    toks, pos = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", h):
        for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:mm.start()]), re.I):
            toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:]), re.I):
        toks.append(ch)
    return "/".join(toks)


# ============ 1) 現在の分解を確認 ============
st.header("1. 現在の分解を確認")
word_in = st.text_input("単語を入力 (例: sporti)", key="word_probe").strip()
if st.button("現在の分解を見る") and word_in:
    w = convert_to_circumflex(word_in).lower()
    try:
        _probe_context = drafts.begin_diagnosis(DATA, assignment_edition)
        _hr = _render_probe(w, RUBY_JSON, RUBY_FMT, "ruby")
        _hk = _render_probe(w, KANJI_JSON, KANJI_FMT, "kanji")
        rb = _decompose(w, RUBY_JSON, RUBY_FMT, "ruby", _hr)
        kj = _decompose(w, KANJI_JSON, KANJI_FMT, "kanji", _hk)
        st.write(f"**ルビモードの分解**: `{rb}`")
        st.write(f"**漢字モードの分解**: `{kj}`")
        with st.expander("👀 実際の表示を見る(ルビ/漢字)", expanded=False):
            import streamlit.components.v1 as _components
            from esp_text_replacement_module import apply_ruby_html_header_and_footer as _hf
            st.caption("注釈ルビ")
            _components.html(_hf(_hr, RUBY_FMT), height=90, scrolling=True)
            st.caption("漢字ルビ")
            _components.html(_hf(_hk, KANJI_FMT), height=90, scrolling=True)
        st.session_state["probe_word"] = w
        st.session_state["probe_ruby"] = rb
        if not drafts.remember_diagnosis(DATA, assignment_edition, w, rb, _probe_context):
            st.info(drafts.LABELS[editions.language(DATA_DIR)]["context_changed"])
    except Exception as e:
        st.error(f"分解の確認に失敗: {e}")

# ============ 2) 正しい分解を入力して保存 ============
st.header("2. 正しい分解を入力して補正を保存")
drafts.render_import_control(DATA, assignment_edition)
decomp_in = st.text_input(
    "正しい分解 (スラッシュ区切り, 例: sport/i)", key="decomp_in", on_change=drafts.remember_draft
).strip()

if decomp_in:
    norm_decomp = convert_to_circumflex(decomp_in).lower()
    word_of_decomp = norm_decomp.replace("/", "").replace(" ", "")
    # プレビュー: 各セグメントの訳/漢字
    try:
        segs = ov.segment_glosses(norm_decomp, DATA, assignment_edition)
        rows = []
        for seg, rhtml, khtml in segs:
            rgloss = re.sub(r"<[^>]+>", "", rhtml).replace(seg, "", 1) if rhtml else "—(訳なし)"
            kgloss = re.sub(r"<[^>]+>", "", khtml).replace(seg, "", 1) if khtml else "—(漢字なし)"
            rows.append({"語根": seg, "ルビ訳": rgloss, "漢字": kgloss})
        st.table(rows)
    except Exception as e:
        st.warning(f"プレビュー生成に失敗: {e}")

    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"スラッシュ除去後の単語: `{word_of_decomp}`")
    with col2:
        if st.button("✅ この補正を保存", type="primary"):
            try:
                entry = ov.add_correction(DATA, norm_decomp, assignment_edition)
                st.success(
                    f"補正を保存しました: `{entry['word']}` → `{entry['decomp']}`  "
                    "(ルビ・漢字 両モードに即反映。メインページ(変換)で確認できます)"
                )
            except Exception as e:
                st.error(f"保存に失敗: {e}")

# ============ 3) 保存済みの補正一覧 ============
st.header("3. 保存済みの補正一覧")
st.caption('この一覧とバックアップは、同梱の補正に、このセッションでの追加・読み込み・削除を反映した現在有効な手動補正です。アプリ側の自動補正や@専用の処理は含みません。同じ結果の再現には、対応するソース版・データ・設定も必要です。')
cors = ov.load_corrections(DATA)
if not cors:
    st.info("まだ補正はありません。")
else:
    st.caption(f"{len(cors)} 件の補正が有効です(メインページ(変換)に自動適用)。")
    for c in cors:
        c1, c2, c3 = st.columns([3, 5, 2])
        c1.write(f"**{c.get('word','')}**")
        c2.write(f"→ `{c.get('decomp','')}`")
        if c3.button("削除", key="del_" + c.get("word", "")):
            ov.remove_correction(DATA, c.get("word", ""))
            st.rerun()

    st.download_button(
        "⬇ 現在有効な手動補正をバックアップ（user_corrections.json）",
        data=json.dumps([dict(ov.build_correction(c["decomp"], DATA, assignment_edition),
                             assignment_edition=assignment_edition,
                             assignment_signature=editions.edition_signature(DATA_DIR, assignment_edition))
                         if c.get("decomp") else c for c in cors], ensure_ascii=False, indent=1).encode("utf-8"),
        file_name=editions.download_filename("user_corrections", editions.result_metadata(DATA_DIR, assignment_edition), "json"),
        mime="application/json",
    )

# ============ 4) 補正ファイルの読み込み（復元・3アプリ間で移植） ============
st.header("4. 補正ファイルの読み込み（バックアップ復元 / 3アプリ間で共有）")
st.markdown(
    """
    保管している `user_corrections.json` の**読み込み場所は2つ**あり、どちらでも同じように効きます:

    | 読み込み場所 | 向いている用途 |
    |---|---|
    | **メインページ(変換)の「📂 手動補正ファイルを読み込む」** | 変換したいだけのとき(最短・おすすめ) |
    | **このページ(ここ)** | 読み込んだ補正の**一覧確認・個別削除・再ダウンロード**など管理をしたいとき |

    - **Streamlit Cloud では補正がセッション終了で消えます**。ダウンロードして保管し、次回上のどちらかで
      読み込んでください(管理者に送って commit されれば、全員向けのベースラインとして恒久化されます)。
    - 読み込み時、各語根の訳・漢字は **このアプリの辞書で作り直す**ので、日本語版で作った補正を
      中文版・한국어版へそのまま移植できます(分解だけを流用)。
    """
)
up = st.file_uploader("user_corrections.json を選択", type="json", key="cor_upload")
if up is not None:
    try:
        data = json.load(up)
        decomps = [c.get("decomp") for c in data if isinstance(c, dict) and c.get("decomp")]
        st.write(f"読み込む補正: **{len(decomps)} 件**  例: {', '.join(decomps[:8])}")
        if st.button("⬆ この内容で復元（現在の補正を置き換え）"):
            new = []
            for d in decomps:
                try:
                    new.append(ov.build_correction(d, DATA, assignment_edition))
                except Exception:
                    pass
            if not new:
                st.error("有効な補正が0件でした。ファイル形式をご確認ください（現在の補正は変更していません）。")
                st.stop()
            ov.save_corrections(DATA, new)
            st.success(f"{len(new)} 件の補正を復元しました。")
            st.rerun()
    except Exception as e:
        st.error(f"読み込み失敗: {e}")
