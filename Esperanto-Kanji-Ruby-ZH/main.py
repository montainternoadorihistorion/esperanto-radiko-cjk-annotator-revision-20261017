# main.py
# --------------------------------------------------------------------
# 这里是 Streamlit 应用程序的主文件 (扩展功能版 202502)
# --------------------------------------------------------------------

import streamlit as st
import esp_assignment_edition as editions
import esp_input_state as input_state
import re
import io
import os
import json
import pandas as pd  # 如果需要的话使用
from typing import List, Dict, Tuple, Optional
import streamlit.components.v1 as components

# Resolve data from this file without changing Streamlit's working directory.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "app_data")
REPO_DIR = os.path.dirname(APP_DIR)

import multiprocessing
# 在使用 multiprocessing 时，为避免 PicklingError，必须在 streamlit 中显式指定 "spawn"：
# 如果已经设置过 start method，则会抛出 RuntimeError，这里直接忽略
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass

# 从 esp_text_replacement_module.py 中导入必要函数
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

# --------------------------------------------------------------------
# 通过对函数的结果进行 cache_data，可以加快读取默认的替换用 JSON 文件(可能有 50MB左右)
# (约 1.0 秒 -> 0.5 秒 的加速)
# --------------------------------------------------------------------
def load_replacements_lists(json_path: str) -> Tuple[List, List, List]:
    return editions.load_lists_path(json_path)


# 设置页面基本信息
st.set_page_config(page_title="世界语文本 注释Ruby·汉字化工具", page_icon="📖", layout="wide")

# 页面主标题
st.title("世界语文本 注释Ruby·汉字化工具")
st.caption("按词根显示中文注释Ruby / 汉字替换(带Ruby·纯文本)")
st.markdown("📘 [**项目快速指南**](https://takatakatake.github.io/kanji_assign/index.zh.html) — 一页了解词根分解·汉字分配·各应用的整体架构(可切换 日本語/中文/한국어)")

st.write("---")

# --------------------------------------------------------------------
# 第1步：读取 JSON 文件（替换规则）。
#   用户可选择“使用默认”或“上传自定义 JSON”
# --------------------------------------------------------------------
assignment_edition = editions.select_edition(DATA_DIR)
_custom_json_sha = None
_bundled_json_path = None

selected_option = input_state.persistent_radio(
    "选择转换模式:",
    ("📖 注释Ruby（词根上方显示中文注释）", "🈶 汉字化（汉字＋词根Ruby）", "✂️ 汉字化·纯替换（无标签文本）", "📤 使用自定义JSON（高级）"),
    key="_conversion_mode_widget",
)

st.caption("初次使用保持默认的 **「📖 注释Ruby」** 即可（原文不变，词根上方显示中文注释）。")

if "🈶" in selected_option or "✂️" in selected_option:
    st.caption("💡 汉字模式下，汉字右上角有时会带有小字母（如 扩ᴬᴷ、金ⱽ、员ᴬ）。这是同一汉字被多个词根共用时的**区分标记**（源自词根拼写），有助于辨别词根。")

# 在折叠框中提供一个示例 JSON 文件可下载
with st.expander("【示例 JSON 文件（替换用）】"):
    json_file_path = os.path.join(DATA_DIR, '置換リスト_ルビ.json')
    with open(json_file_path, "rb") as file_json:
        btn_json = st.download_button(
            label="下载示例 JSON（替换用）",
            data=file_json,
            file_name="示例_替换用JSON文件.json",
            mime="application/json"
        )

# 准备好这三个列表，以便之后进行替换
replacements_final_list: List[Tuple[str, str, str]] = []
replacements_list_for_localized_string: List[Tuple[str, str, str]] = []
replacements_list_for_2char: List[Tuple[str, str, str]] = []

if selected_option == "📖 注释Ruby（词根上方显示中文注释）":
    default_json_path = os.path.join(DATA_DIR, '置換リスト_ルビ.json')
    _bundled_json_path = default_json_path
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(default_json_path)
        st.success("✅ 注释Ruby模式准备就绪。")
    except Exception as e:
        st.error(f"读取默认 JSON 文件时出错: {e}")
        st.stop()
elif selected_option == "🈶 汉字化（汉字＋词根Ruby）":
    kanji_json_path = editions.resolve_path(DATA_DIR, "kanji", assignment_edition)
    _bundled_json_path = kanji_json_path
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(kanji_json_path)
        st.success("✅ 汉字化模式准备就绪（汉字正文·词根Ruby）。")
    except Exception as e:
        st.error(f"读取汉字化版 JSON 时出错: {e}")
        st.stop()
elif selected_option == "✂️ 汉字化·纯替换（无标签文本）":
    pure_json_path = editions.resolve_path(DATA_DIR, "pure", assignment_edition)
    _bundled_json_path = pure_json_path
    try:
        replacements_final_list, replacements_list_for_localized_string, replacements_list_for_2char = load_replacements_lists(pure_json_path)
        st.success("已读取纯替换版JSON。世界语文本将被转换为无标签的汉字文本(例: amikeco → 友性o)。")
    except Exception as e:
        st.error(f"读取纯替换版JSON时出错: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("请上传替换用 JSON 文件（文件名形如「○○(合并3个JSON文件).json」）", type="json")
    if uploaded_file is not None:
        try:
            combined_data = json.load(uploaded_file)
            _custom_json_sha = editions.hashlib.sha256(uploaded_file.getvalue()).hexdigest()
            st.caption({"JA": "自作JSON本体に割り当て版の選択は適用されません。自動語根補正には共通の最新注釈を使います。", "ZH": "所选分配版本不应用于自定义JSON本体。自动词根校正使用共用的最新注释。", "KO": "선택한 배정 판은 사용자 JSON 자체에 적용되지 않습니다. 자동 어근 보정에는 공통 최신 주석을 사용합니다。"}[editions.language(DATA_DIR)])
            replacements_final_list = combined_data.get(
                "全域替换用のリスト(列表)型配列(replacements_final_list)", [])
            replacements_list_for_localized_string = combined_data.get(
                "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)", [])
            replacements_list_for_2char = combined_data.get(
                "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)", [])
            st.success("已成功读取上传的 JSON 文件。")
            if not (replacements_final_list or replacements_list_for_localized_string or replacements_list_for_2char):
                st.error("在该JSON中未找到替换规则（键名可能与预期不同）。请确认是否为「合并3个JSON文件」格式。")
            _probe = next((e[1] for e in replacements_final_list[:200] if isinstance(e, (list, tuple)) and len(e) >= 2 and isinstance(e[1], str) and e[1].strip()), "")
            if "<ruby>" in _probe:
                st.caption("🔍 检测: 该JSON似为**HTML Ruby格式** → 下方输出格式请选择「HTML Ruby格式」系。")
            elif _probe:
                st.caption("🔍 检测: 该JSON似为**无标签格式** → 下方输出格式请选择「括号格式」或「纯替换」。")
        except Exception as e:
            st.error(f"读取上传 JSON 文件时出错: {e}")
            st.stop()
    else:
        st.warning("尚未上传 JSON 文件，无法继续执行。")
        st.stop()

reviewed_local_decompositions = bool(
    _bundled_json_path and editions.supports_reviewed_local_decompositions(_bundled_json_path)
)

# 1.5) 手动校正(轻量 overlay)以最高优先级应用
#   在「语根分解手动校正」页面保存的校正(app_data/user_corrections.json),
#   无需重新生成替换用JSON即可在运行时反映。
# 1.4) 读取本地 user_corrections.json 到本会话(可选)
with st.expander("📂 读取手动校正文件(user_corrections.json)(可选)"):
    st.caption("将在「词根分解的手动校正」页面下载的校正应用到本会话(不影响其他用户)。")
    _cor_up = st.file_uploader("user_corrections.json", type="json", key="main_cor_upload")
    if _cor_up is not None and st.session_state.get("main_cor_loaded") != getattr(_cor_up, "file_id", True):
        try:
            import esp_overlay_module as _ovu
            _decs = [c.get("decomp") for c in json.load(_cor_up) if isinstance(c, dict) and c.get("decomp")]
            _new = []
            for _dc in _decs:
                try: _new.append(_ovu.build_correction(_dc, DATA_DIR, assignment_edition))
                except Exception: pass
            if _new:
                _ovu.save_corrections(DATA_DIR, _new)
            else:
                st.error("有效校正为 0 条。请确认是否为在「词根分解的手动校正」页面下载的 user_corrections.json（当前校正未被更改）。")
            st.session_state["main_cor_loaded"] = getattr(_cor_up, "file_id", True)
            st.success(f"已将 {len(_new)} 条校正应用到本会话。") if _new else None
        except Exception as _e:
            st.error(f"读取失败（{_e}）。请确认是否为在「词根分解的手动校正」页面下载的 user_corrections.json。")

try:
    import esp_overlay_module as _ov
    _ov_mode = "kanji" if selected_option in ("🈶 汉字化（汉字＋词根Ruby）", "✂️ 汉字化·纯替换（无标签文本）") else "ruby"
    _ov_entries_raw = _ov.load_overlay_entries(DATA_DIR, _ov_mode, assignment_edition)
    if selected_option == "✂️ 汉字化·纯替换（无标签文本）":
        import re as _re_ov
        _ov_entries = [[o, _re_ov.sub(r"</?ruby>", "", _re_ov.sub(r"<rt[^>]*>.*?</rt>", "", n, flags=_re_ov.DOTALL | _re_ov.IGNORECASE), flags=_re_ov.IGNORECASE), ph] for o, n, ph in _ov_entries_raw]
    else:
        _ov_entries = _ov_entries_raw
    if _ov_entries and not str(selected_option).startswith("📤"):
        # 自作JSONモードは形式が不明のため補正オーバーレイ(HTML)は適用しない
        replacements_final_list = _ov.merge_overlay(replacements_final_list, _ov_entries)
        st.info(f"正在自动应用 {len(_ov.load_corrections(DATA_DIR))} 条词根分解质量校正（**无需操作**。可在「词根分解的手动校正」页面查看·编辑）。")
except Exception:
    pass

# --------------------------------------------------------------------
# 2) 读取一些与替换相关的 placeholder(占位符) 文件
# --------------------------------------------------------------------
placeholders_for_skipping_replacements: List[str] = import_placeholders(
    os.path.join(DATA_DIR, 'placeholders_skip.txt')
)
placeholders_for_localized_replacement: List[str] = import_placeholders(
    os.path.join(DATA_DIR, 'placeholders_localcapture.txt')
)

st.write("---")

# --------------------------------------------------------------------
# 给用户提供一个并行处理（multiprocessing）的配置选项
# --------------------------------------------------------------------
with st.expander("⚙️ 高级设置(并行处理·通常无需更改)"):
    st.write("""
        如果文本很大，可以通过多进程并行处理加快转换速度。
        请在此处勾选“使用并行处理”，并指定进程数。
    """)
    use_parallel = st.checkbox("使用并行处理", value=False)
    num_processes = st.number_input("并行进程数量", min_value=2, max_value=2, value=2, step=1)
    st.caption("⚠️ 并行处理会为每个进程复制替换列表(约400MB)。在 Streamlit Cloud 等内存较小的环境中，可能因内存不足导致应用停止(此功能面向本地多核电脑)。")


st.write("---")

# --------------------------------------------------------------------
# 选择“输出形式”（HTML 或者带括号等等）
# --------------------------------------------------------------------
# 输出格式: 使用内置JSON时自动选择(无需操作)。仅上传JSON时手动选择。
_FMT_CHOICES = [
    ("HTML Ruby格式·宽度调整【标准】 — 词根上方显示注释: amiko → amik(上方「友」)o", "HTML格式_Ruby文字_大小调整"),
    ("HTML Ruby格式·宽度调整【汉字替换】 — 汉字为正文·词根为Ruby: amiko → 友(上方「amik」)o", "HTML格式_Ruby文字_大小调整_汉字替换"),
    ("HTML Ruby格式·简单(无宽度调整)", "HTML格式"),
    ("HTML Ruby格式·简单【汉字替换】", "HTML格式_汉字替换"),
    ("括号格式 — 无标签: amiko → amik(友)o", "括弧(号)格式"),
    ("括号格式【汉字替换】 — 无标签: amiko → 友(amik)o", "括弧(号)格式_汉字替换"),
    ("纯替换 — 只保留注释/汉字: amiko → 友o", "替换后文字列のみ(仅)保留(简单替换)"),
]
if selected_option == "📖 注释Ruby（词根上方显示中文注释）":
    format_type = "HTML格式_Ruby文字_大小调整"
    st.info("输出格式: **HTML Ruby格式(宽度调整)** — 已根据内置注释Ruby JSON自动选择。")
elif selected_option == "🈶 汉字化（汉字＋词根Ruby）":
    format_type = "HTML格式_Ruby文字_大小调整_汉字替换"
    st.info("输出格式: **HTML Ruby格式(汉字正文+词根Ruby)** — 已根据内置汉字化JSON自动选择。")
elif selected_option == "✂️ 汉字化·纯替换（无标签文本）":
    format_type = "替换后文字列のみ(仅)保留(简单替换)"
    st.info("输出格式: **纯替换(无标签文本)** — 已根据纯替换JSON自动选择。无需HTML,可直接复制使用。")
else:
    _sel = st.selectbox(
        "选择输出格式 (须与**创建**所上传JSON时的格式一致)",
        [label for label, _v in _FMT_CHOICES],
    )
    st.caption("※ 下载的 .html 文件**双击即可在浏览器中带注音打开**。若要粘贴到 Word 等，请先在浏览器中打开再复制。")
    format_type = dict(_FMT_CHOICES)[_sel]

# 准备一个全局字符串 processed_text 来保存处理后的文本
processed_text = ""

# --------------------------------------------------------------------
# 4) 选择如何输入待转换的文本（手动输入或上传文件）
# --------------------------------------------------------------------
st.subheader("输入文本来源")
source_option = input_state.persistent_radio(
    "请选择输入文本的方式：",
    ("手动输入", "上传文件"),
    key="_source_option_widget",
)

# Source uploads are applied before the editor; invalid files never replace a draft.
_source_ready = True
_source_upload_identity = None
if source_option == '上传文件':
    text_file = st.file_uploader('上传文本文件 (UTF-8 编码)', type=["txt", "csv", "md"], key="_source_text_upload")
    if text_file is not None:
        try:
            _source_upload_identity = input_state.apply_text_upload(text_file)
            st.info('文件已读取。')
        except UnicodeDecodeError:
            _source_ready = False
            st.error('文件不是有效的 UTF-8，输入内容未被替换。请另存为 UTF-8 后重新上传。')
    else:
        _source_ready = False
        st.warning('尚未上传文本文件，请重新上传或切换为手动输入。')

_c1, _c2 = st.columns([1, 3])
with _c1:
    st.button("📝 填入示例文本", on_click=lambda: input_state.set_text('Saluton! Ĉu vi jam aŭdis, ke Esperanto estas internacia lingvo? Mi eĉ komencis lerni ĝin hodiaŭ, ĉar la komputilo kaj la telefono faciligas la lernadon. La amikeco inter la popoloj kreskas ĉiutage.'))
with _c2:
    st.caption("初次使用: 点击按钮填入示例文本,即可立即体验转换。")

# st.stop経路(自作JSON未アップロード等)で text0_value がwidget cleanupで消えた場合の復元
if "text0_value" not in st.session_state and "_text0_keep" in st.session_state:
    st.session_state["text0_value"] = st.session_state["_text0_keep"]

# 用 key="text0_value" 将 text_area 与 session_state 双向绑定。
# 旧方式(value=initial_text)会在提交时把控件重置为上一次的值，导致
# “提交后使用的是上一次输入(滞后一步)”的 bug；key= 方式可让提交时立即反映当前输入。
text0 = st.text_area(
    "请输入世界语文章",
    height=150,
    key="text0_value",
    on_change=input_state.remember_text,
)
st.session_state["_text0_keep"] = text0  # st.stop経路のwidget cleanup対策(非ウィジェットキーは生存)
st.caption("💡 帽符字母可用 **cx / c^ / ĉ** 任意一种写法输入(例: sxatas·s^atas·ŝatas)。长文(数千行)转换可能需要数十秒。")

with st.expander("🔖 调整局部转换(%与@标记)"):
    st.markdown("""
- 用 `%...%` 包裹的部分**跳过词根转换**(同一行，50字符以内；仍会统一字帽及空格格式)。
  例: `%Universala Kongreso% okazos.`
- 用 `@...@` 包裹的部分**按局部替换列表处理，并去掉两端的@**(同一行，也可指定词内的一部分)。
  例: `@semajn@tagoj` → 将 **semajn** 作为整体进行局部处理。标记外的文字仍正常转换。
- 电子邮箱地址中的@不作为标记。需要保留整段文字时，请用 `%...%`。
""")

# 让用户选择“输出字符形式”（上标形式、x 形式、^ 形式）
letter_type = input_state.persistent_radio(
    '世界语字母的书写形式(输出)',
    ('ĉ ĝ ĥ ĵ ŝ ŭ (标准)', 'cx gx hx jx sx ux (x形式)', 'c^ g^ h^ j^ s^ u^ (^形式)'),
    key="_letter_type_widget",
)

# 提交、取消按钮
_current_input_signature = input_state.input_signature(text0, source_option, _source_upload_identity)
submit_btn = st.button('🔁 开始转换', type="primary", key="convert_text", disabled=not _source_ready)


# 如果点击了“提交”
if submit_btn and not (text0 or "").strip():
    st.warning("文本为空。请输入世界语文本后再点击「开始转换」。")
    st.stop()

if submit_btn:
    # text0 已通过 key="text0_value" 与 session_state 双向绑定，
    # 此处手动赋值会在控件实例化后修改 session_state 而报错，故不再赋值。

    # 根据是否勾选并行处理，调用不同函数
    if use_parallel:
        processed_text = parallel_process(
            text=text0,
            num_processes=num_processes,
            placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
            replacements_list_for_localized_string=replacements_list_for_localized_string,
            placeholders_for_localized_replacement=placeholders_for_localized_replacement,
            replacements_final_list=replacements_final_list,
            replacements_list_for_2char=replacements_list_for_2char,
            format_type=format_type,
            reviewed_local_decompositions=reviewed_local_decompositions
        )
    else:
        processed_text = orchestrate_comprehensive_esperanto_text_replacement(
            text=text0,
            placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
            replacements_list_for_localized_string=replacements_list_for_localized_string,
            placeholders_for_localized_replacement=placeholders_for_localized_replacement,
            replacements_final_list=replacements_final_list,
            replacements_list_for_2char=replacements_list_for_2char,
            format_type=format_type,
            reviewed_local_decompositions=reviewed_local_decompositions
        )

    # 第1遍若出现「词首单字游离」过度分解(辅音单字游离: fero->f/er/o 等),
    # 以最高优先级 merge 自动校正并渲染第2遍(在机制层面清除该缺陷类)。无游离则不处理。
    try:
        import esp_overlay_module as _ovx
        _afmode = "kanji" if selected_option in ("🈶 汉字化（汉字＋词根Ruby）", "✂️ 汉字化·纯替换（无标签文本）") else "ruby"  # sample_btn_marker
        _auto_strip_pure = (selected_option == "✂️ 汉字化·纯替换（无标签文本）")
        _auto = _ovx.auto_overlay_entries(processed_text, DATA_DIR, _afmode, assignment_edition)
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
                    format_type=format_type,
                    reviewed_local_decompositions=reviewed_local_decompositions)
            else:
                processed_text = orchestrate_comprehensive_esperanto_text_replacement(
                    text=text0,
                    placeholders_for_skipping_replacements=placeholders_for_skipping_replacements,
                    replacements_list_for_localized_string=replacements_list_for_localized_string,
                    placeholders_for_localized_replacement=placeholders_for_localized_replacement,
                    replacements_final_list=_GGx,
                    replacements_list_for_2char=replacements_list_for_2char,
                    format_type=format_type,
                    reviewed_local_decompositions=reviewed_local_decompositions)
    except Exception:
        pass

    # 将上标形式等应用到结果中
    if letter_type == 'ĉ ĝ ĥ ĵ ŝ ŭ (标准)':
        processed_text = replace_esperanto_chars(processed_text, x_to_circumflex)
        processed_text = replace_esperanto_chars(processed_text, hat_to_circumflex)
    elif letter_type == 'cx gx hx jx sx ux (x形式)':
        processed_text = replace_esperanto_chars(processed_text, circumflex_to_x)
        processed_text = replace_esperanto_chars(processed_text, hat_to_x)
    elif letter_type == 'c^ g^ h^ j^ s^ u^ (^形式)':
        processed_text = replace_esperanto_chars(processed_text, x_to_hat)
        processed_text = replace_esperanto_chars(processed_text, circumflex_to_hat)

    processed_text = apply_ruby_html_header_and_footer(processed_text, format_type)

    # 将结果保存到 session_state（避免重跑时丢失，并使结果可编辑）
    st.session_state["result_html"] = processed_text
    st.session_state["result_input_signature"] = _current_input_signature
    st.session_state["_edited_html_keep"] = processed_text
    st.session_state["result_assignment_metadata"] = editions.result_metadata(DATA_DIR, assignment_edition, _custom_json_sha, {"mode": selected_option, "format": format_type, "letters": letter_type})
    st.session_state["edited_html"] = processed_text          # 编辑用初始值＝生成结果
    st.session_state["result_is_html"] = ("HTML" in format_type)
    st.toast("✅ 转换完成,结果已显示在下方。")

# --------------------------------------------------------------------
# 表单外：结果预览 / 编辑 / 下载
# --------------------------------------------------------------------
def _reset_edited_html():
    # “放弃编辑”回调（控件实例化后修改 session_state 会报错，故在回调里恢复为生成结果）
    st.session_state["edited_html"] = st.session_state.get("result_html", "")
    st.session_state["_edited_html_keep"] = st.session_state["edited_html"]

_result_meta = st.session_state.get("result_assignment_metadata")
_matching_input = _source_ready and st.session_state.get("result_input_signature") == _current_input_signature
_matching_result = editions.result_matches(_result_meta, DATA_DIR, assignment_edition, _custom_json_sha, {"mode": selected_option, "format": format_type, "letters": letter_type}) and _matching_input
if st.session_state.get("result_html") and not _matching_result:
    if not _matching_input:
        st.info('输入内容或输入方式已更改。请重新转换后再保存。')
    else:
        editions.stale_result_notice(DATA_DIR, _result_meta)

if st.session_state.get("result_html") and _matching_result:
    # st.stop()経路(自作JSON未アップロード等)のwidget cleanupで edited_html が消えた場合の再シード
    if "edited_html" not in st.session_state:
        st.session_state["edited_html"] = st.session_state.get("_edited_html_keep", st.session_state["result_html"])
    st.caption("可在「HTML 源码（可编辑）」标签页直接修改输出，修改会反映到预览与下载（重新转换则恢复生成结果）。")

    # 编辑后的内容（没有则为生成结果）。预览与下载都使用该内容。
    current_html = st.session_state.get("edited_html", st.session_state["result_html"])

    # 文本过长时仅预览省略（编辑与下载始终针对全文）
    MAX_PREVIEW_LINES = 250
    lines = current_html.splitlines()
    if len(lines) > MAX_PREVIEW_LINES:
        preview_text = "\n".join(lines[:247]) + "\n...\n" + "\n".join(lines[-3:])
        st.warning(
            f"文本行数较多（共 {len(lines)} 行），预览仅显示部分内容（编辑与下载为全文）。"
        )
    else:
        preview_text = current_html

    if st.session_state.get("result_is_html"):
        tab1, tab2 = st.tabs(["HTML 预览", "HTML 源码（可编辑）"])
        with tab1:
            components.html(preview_text, height=500, scrolling=True)
        with tab2:
            st.text_area(
                "可直接编辑输出的 HTML（编辑后会反映到预览与下载）",
                key="edited_html",
                on_change=input_state.remember_edited_text,
                height=300
            )
            st.button("放弃编辑，恢复生成结果", on_click=_reset_edited_html)
        download_name = "转换结果.html"
    else:
        tab3_list = st.tabs(["📋 复制用(点右上角图标复制)", "✏️ 编辑"])
        with tab3_list[0]:
            st.code(preview_text, language=None)
        with tab3_list[1]:
            st.text_area("可直接编辑输出", key="edited_html", on_change=input_state.remember_edited_text, height=300)
            st.button("放弃编辑，恢复生成结果", on_click=_reset_edited_html)
        download_name = "转换结果.txt"

    _extension = "html" if st.session_state.get("result_is_html") else "txt"
    download_name = editions.download_filename(os.path.splitext(download_name)[0], _result_meta, _extension)
    _download_text = (editions.html_download_metadata(_result_meta) if _extension == "html" else "") + current_html
    download_data = _download_text.encode('utf-8')
    if st.button("确认保存内容", key="confirm_download"):
        input_state.confirm_download(
            text=current_html, data=download_data, filename=download_name,
            is_html=(_extension == "html"),
            edition_label=_result_meta["edition_label"],
            title="将要保存的内容", content_label="将要保存的文本",
            download_label="下载转换结果（已反映编辑）",
        )
    st.page_link("pages/1_🔧_词根分解的手动校正.py", label="🔧 发现错误的分解 → 前往手动校正页面修正(即时生效)")

st.write("---")
st.header("Ligilo-oj (URL-oj) / 言語版・语言版本・언어판")
st.markdown("""
#### 日中韓 三言語版 ⇓ (Japana / Ĉina / Korea)
- **日本語版 (Japana)**: https://esperanto-radiko-cjk-annotator.streamlit.app/
- **中文版 (Ĉina)**: https://esperanto-radiko-cjk-annotator-zh.streamlit.app/
- **한국어판 (Korea)**: https://esperanto-radiko-cjk-annotator-ko.streamlit.app/

#### GitHub-deponejo (fontkodo & uzadaj instrukcioj) ⇓
https://github.com/montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017
""")
