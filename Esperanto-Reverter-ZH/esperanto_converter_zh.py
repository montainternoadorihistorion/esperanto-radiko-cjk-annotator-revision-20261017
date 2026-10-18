"""汉字化世界语 → 字母转换器（中文版）

基于日语版 kanjized-esperanto-reverter（r33, monaco 151bf3c 追随）移植，
仅将界面文字改为中文；转换逻辑与词典完全一致。2026-08-22 全面更新。
"""
from __future__ import annotations

import string
import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
LEGACY_CSV = ROOT / "エスペラント語根-漢字対応表_スニペット用最小限.csv"
PEJVO_PIV_20260620_CSV = ROOT / "data" / "pejvo_piv_20260620_reverter.csv"
PRE_LAS_20261017_CSV = ROOT / "data" / "pejvo_piv_pre_las_20261017.csv"
PRE_MIRROR_20261017_CSV = ROOT / "data" / "pejvo_piv_pre_mirror_20261017.csv"
PRE_SATIR_20261017_CSV = ROOT / "data" / "pejvo_piv_pre_satir_20261017.csv"
PRE_SPERM_DISTINCTION_20261018_CSV = ROOT / "data" / "pejvo_piv_pre_sperm_distinction_20261018.csv"
PRE_DOT_GREFT_20261018_CSV = ROOT / "data" / "pejvo_piv_pre_dot_greft_20261018.csv"
PRE_DOT_GREFT_SNIPPET_20261018_CSV = ROOT / "data" / "snippet_pre_dot_greft_20261018.csv"
PRE_SPERM_DISTINCTION_SNIPPET_20261018_CSV = ROOT / "data" / "snippet_pre_sperm_distinction_20261018.csv"
PRE_SATIR_SNIPPET_20261017_CSV = ROOT / "data" / "snippet_pre_satir_20261017.csv"
PRE_THREE_SHORT_20261017_CSV = ROOT / "data" / "pejvo_piv_pre_three_short_20261017.csv"
PRE_THREE_SHORT_SNIPPET_20261017_CSV = ROOT / "data" / "snippet_pre_three_short_20261017.csv"

DICTIONARY_SOURCES = {
    "pejvo-piv-20260620": {
        "label": "新版（更新中）",
        "path": PEJVO_PIV_20260620_CSV,
        "description": "新版包含评审期间已采用的修改。今后的分配修改继续反映到此版本。",
    },
    # ID は後方互換（セッションキー）のため "legacy-minimal" のまま。中身は
    # 現行の漢字割当（全語根）を2列スニペット形式で再生成済み。
    "legacy-minimal": {
        "label": "代码片段用两列CSV（现行分配）",
        "path": LEGACY_CSV,
        "description": "以两列（世界语词根,汉字）收录现行汉字分配的CSV。转换结果与「现行分配」相同。",
    },
    "pre-three-short-20261017": {
        "label": "三个词根缩写前（簧=anĉ，2026-10-17）",
        "path": PRE_THREE_SHORT_20261017_CSV,
        "description": "这是修改前一刻的词典：risort=弹簧、anĉ=簧、lantern=灯笼、lubrik=润滑。适用于按这些写法保存的文章。无标识符的簧在现行词典还原为risort，在这里还原为anĉ。不自动判断版本。",
    },
    "pre-dot-greft-20261018": {
        "label": "移植与妆分配修改前（2026-10-18）",
        "path": PRE_DOT_GREFT_20261018_CSV,
        "description": "这是greft=嫁接、dot=嫁妆、tualet=妆修改前一刻的完整词典。用于将旧文中的妆还原为tualet，或将移＋植分别还原为translaci＋plant。包含已采用的精子系列分配。不自动判断版本。",
    },
    "pre-sperm-distinction-20261018": {
        "label": "精子与精液区分修改前（2026-10-18）",
        "path": PRE_SPERM_DISTINCTION_20261018_CSV,
        "description": "这是spermat=精ˢ、spermati=精ˢᴵ修改前一刻的完整词典。请用于以修改前的字形保存的文章，不包含spermatozo的新分配。不自动判断版本。",
    },
    "pre-satir-20261017": {
        "label": "satir修改前（2026-10-17）",
        "path": PRE_SATIR_20261017_CSV,
        "description": "这是satir=讽刺、karikatur=讽、sarkasm=讽ˢ修改前一刻的完整词典。无标识符的讽在现行词典还原为satir，在这里还原为karikatur。不自动判断版本。",
    },
    "pre-mirror-20261017": {
        "label": "复合词标识符修正前（2026-10-17）",
        "path": PRE_MIRROR_20261017_CSV,
        "description": "保留 testikit=丸炎ᵀ、orkidit=丸炎 时的词典，同时包含截至当时的 las=放、ananas=菠、strut=鸵 等修改。用于修正前保存的文章。",
    },
    "pre-las-20261017": {
        "label": "旧版（固定）",
        "path": PRE_LAS_20261017_CSV,
        "description": "这是本轮汉字分配修改开始前的固定旧版（las=留、emancip=放）。此版的分配不再更新。",
    },
}
# Only these two editions are user-facing; archived source IDs remain API-compatible.
EDITION_POLICY = json.loads((ROOT / "data" / "two_editions_policy.json").read_text(encoding="utf-8"))
VISIBLE_EDITION_IDS = tuple(EDITION_POLICY["visible_edition_ids"])
CONVERTED_PROVENANCE_KEY = "converted_dictionary_provenance"
DEFAULT_DICTIONARY_ID = "pejvo-piv-20260620"
CONVERTED_TEXT_KEY = "converted_text"
CONVERTED_INPUT_KEY = "converted_input_text"
CONVERTED_SOURCE_KEY = "converted_source_signature"

# Fold ONLY ASCII A-Z. The 20 correlative keys (何a/全o/无u/某e/那o …) store their suffix
# vowel in lowercase, so an uppercased vowel in the input (sentence-start / auto-capitalize)
# would otherwise fail to match. Verified that no dictionary key contains uppercase ASCII,
# so this never breaks a match; kanji and superscript identifiers (ᴬᴰ…) are left untouched.
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)

# Defensive cap for user-uploaded custom dictionaries (the bundled dict is ~0.17 MB).
# Streamlit's default maxUploadSize is 200 MB; a few-MB CSV can still hold millions of rows
# and freeze the worker, so reject oversized uploads before parsing.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class MappingEntry:
    kanji: str
    esperanto: str
    priority: int
    source_order: int


@dataclass(frozen=True)
class MappingIndex:
    by_length: Dict[int, Dict[str, str]]
    lengths_desc: List[int]
    entry_count: int

    @property
    def max_length(self) -> int:
        return self.lengths_desc[0] if self.lengths_desc else 0


def read_assignment_csv(source) -> pd.DataFrame:
    raw = pd.read_csv(source, header=None, dtype=str, keep_default_na=False)
    if raw.shape[1] < 2:
        raise ValueError("CSV must have at least two columns: esperanto, kanji")

    first_row = [str(value).strip().lower() for value in raw.iloc[0].tolist()]
    esperanto_headers = {"esperanto", "エスペラント語根", "語根", "世界语词根", "词根"}
    kanji_headers = {"kanji", "漢字", "漢字表記", "汉字", "汉字表记"}
    priority_headers = {"priority", "優先順位", "漢字化優先順位", "优先级"}
    has_header = any(value in esperanto_headers for value in first_row) and any(
        value in kanji_headers for value in first_row
    )
    if has_header:
        header = first_row
        raw = raw.iloc[1:].reset_index(drop=True)
        esperanto_col = next(index for index, value in enumerate(header) if value in esperanto_headers)
        kanji_col = next(index for index, value in enumerate(header) if value in kanji_headers)
        priority_col = next(
            (index for index, value in enumerate(header) if value in priority_headers),
            None,
        )
    else:
        esperanto_col = 0
        kanji_col = 1
        priority_col = 2 if raw.shape[1] >= 3 else None

    data = {
        "esperanto": raw.iloc[:, esperanto_col],
        "kanji": raw.iloc[:, kanji_col],
    }
    if priority_col is not None:
        data["priority"] = raw.iloc[:, priority_col]
    else:
        data["priority"] = range(len(raw))
    return pd.DataFrame(data)


@st.cache_data(show_spinner=False)
def read_assignment_csv_from_path(path_text: str, mtime_ns: int) -> pd.DataFrame:
    return read_assignment_csv(Path(path_text))


def load_dictionary_source(source_id: str) -> pd.DataFrame:
    source = DICTIONARY_SOURCES[source_id]
    path = source["path"]
    if not path.exists():
        raise FileNotFoundError(f"未找到字典文件: {path}")
    return read_assignment_csv_from_path(str(path), path.stat().st_mtime_ns)


def _priority(value, fallback: int) -> int:
    try:
        # Parse via float() so a custom CSV that writes priorities as '1.0' is honoured
        # rather than silently dropped to source order.
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return fallback


def create_mapping_entries(df: pd.DataFrame) -> List[MappingEntry]:
    entries: List[MappingEntry] = []
    for source_order, row in df.iterrows():
        esperanto = str(row.get("esperanto", "")).strip().lower()
        kanji = str(row.get("kanji", "")).strip()
        if not esperanto or not kanji or kanji.lower() == "nan":
            continue
        entries.append(
            MappingEntry(
                kanji=kanji,
                esperanto=esperanto,
                priority=_priority(row.get("priority"), int(source_order)),
                source_order=int(source_order),
            )
        )
    return entries


def build_mapping_index(df: pd.DataFrame) -> MappingIndex:
    entries = create_mapping_entries(df)
    entries.sort(key=lambda entry: (-len(entry.kanji), entry.priority, entry.source_order))

    by_length: Dict[int, Dict[str, str]] = {}
    for entry in entries:
        bucket = by_length.setdefault(len(entry.kanji), {})
        if entry.kanji not in bucket:
            bucket[entry.kanji] = entry.esperanto

    return MappingIndex(
        by_length=by_length,
        lengths_desc=sorted(by_length.keys(), reverse=True),
        entry_count=sum(len(bucket) for bucket in by_length.values()),
    )


def dataframe_to_mapping_records(df: pd.DataFrame) -> tuple[tuple[str, str, str], ...]:
    # Vectorized column extraction instead of df.iterrows() (which materialises a Series per
    # row). This builds the cache key on every Streamlit rerun, so it must be cheap; the
    # tuple output is byte-identical to the previous per-row construction.
    def column(name: str) -> list[str]:
        if name in df.columns:
            return [str(value) for value in df[name].tolist()]
        return [""] * len(df)

    return tuple(zip(column("esperanto"), column("kanji"), column("priority")))


@st.cache_data(show_spinner=False)
def build_mapping_index_cached(records: tuple[tuple[str, str, str], ...]) -> MappingIndex:
    df = pd.DataFrame(records, columns=["esperanto", "kanji", "priority"])
    return build_mapping_index(df)


def convert_kanji_esperanto_to_alphabet(text: str, mapping: MappingIndex) -> str:
    # Make the ASCII portion case-insensitive so uppercased correlative suffix vowels still
    # match (e.g. 全O -> ĉio, not the base 全 -> integro). The output is fully lowercased anyway.
    text = text.translate(_ASCII_LOWER)
    result: List[str] = []
    i = 0
    while i < len(text):
        matched = False
        for length in mapping.lengths_desc:
            if length > len(text) - i:
                continue
            substring = text[i : i + length]
            replacement = mapping.by_length[length].get(substring)
            if replacement is None:
                continue
            result.append(replacement)
            i += length
            matched = True
            break

        if not matched:
            result.append(text[i])
            i += 1

    return "".join(result).lower()


def load_selected_dataframe(source_id: str, uploaded_file) -> pd.DataFrame | None:
    try:
        if source_id == "custom":
            if uploaded_file is None:
                return None
            size = getattr(uploaded_file, "size", 0) or 0
            if size > MAX_UPLOAD_BYTES:
                st.error(
                    f"上传的CSV文件过大（{size / 1024 / 1024:.1f} MB）。"
                    f"请控制在 {MAX_UPLOAD_BYTES // 1024 // 1024} MB 以内。"
                )
                return None
            return read_assignment_csv(uploaded_file)
        return load_dictionary_source(source_id)
    except Exception as exc:
        st.error(f"对照表读取失败: {exc}")
        return None


def dictionary_options() -> List[str]:
    return list(VISIBLE_EDITION_IDS)

def dictionary_label(source_id: str) -> str:
    if source_id == "custom":
        return "自定义 CSV"
    return DICTIONARY_SOURCES[source_id]["label"]


def selected_source_signature(source_id: str, uploaded_file) -> str:
    if source_id != "custom":
        # Fold the file mtime into the signature so an on-disk dictionary change invalidates a
        # previously-converted result (otherwise it would still show as "current").
        path = DICTIONARY_SOURCES.get(source_id, {}).get("path")
        try:
            return f"{source_id}:{path.stat().st_mtime_ns}" if path is not None else source_id
        except OSError:
            return source_id
    if uploaded_file is None:
        return "custom:none"
    size = getattr(uploaded_file, "size", "")
    name = getattr(uploaded_file, "name", "uploaded.csv")
    return f"custom:{name}:{size}"



def source_provenance(source_id: str, uploaded_file=None) -> dict:
    """Pin the actual dictionary identity, separately from its visible edition name."""
    if source_id == "custom":
        raw = uploaded_file.getvalue() if uploaded_file is not None else b""
        digest = hashlib.sha256(raw).hexdigest()
        edition, revision = "custom", "uploaded"
    else:
        raw = DICTIONARY_SOURCES[source_id]["path"].read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if source_id == "pre-las-20261017":
            edition, revision = "old", EDITION_POLICY["baseline_commit"][:12]
            if digest != EDITION_POLICY["fixed_csv_sha256"]:
                raise ValueError("The fixed pre-assignment dictionary has changed")
        elif source_id in ("pejvo-piv-20260620", "legacy-minimal"):
            metadata = json.loads((ROOT / "data" / "current_dictionary_source.json").read_text(encoding="utf-8"))
            edition, revision = "new", metadata["revision"]
        else:
            edition, revision = "archive", source_id
    safe_revision = re.sub(r"[^A-Za-z0-9._-]", "-", revision)
    stamp = f"{edition}_{safe_revision}_{digest[:12]}"
    return {
        "source_id": source_id, "edition": edition, "revision": revision,
        "edition_id": {"new": "current", "old": "legacy"}.get(edition, edition),
        "dictionary_sha256": digest, "identity": f"{source_id}:{revision}:{digest}",
        "label": f"{dictionary_label(source_id)} / {revision} / {digest[:12]}",
        "result_filename": f"esperanto_{stamp}.txt",
        "dictionary_filename": f"dictionary_{stamp}.csv",
        "snippet_filename": f"dictionary_{stamp}_2col.csv",
    }


def edition_download_data(source_id: str) -> tuple[bytes, bytes]:
    """Offer a format choice within one edition, without creating another edition."""
    raw = DICTIONARY_SOURCES[source_id]["path"].read_bytes()
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerows((row["esperanto"], row["kanji"]) for row in rows)
    return raw, output.getvalue().encode("utf-8")

def render_sidebar() -> tuple[str, object | None]:
    with st.sidebar:
        st.header("使用版本")
        source_id = st.selectbox(
            "选择新版或旧版", dictionary_options(),
            index=dictionary_options().index(DEFAULT_DICTIONARY_ID),
            format_func=dictionary_label,
            disabled=bool(st.session_state.get("use_custom_csv", False)),
        )
        uploaded_file = None
        with st.expander("高级：自定义CSV"):
            use_custom = st.checkbox("使用自定义CSV", key="use_custom_csv")
            if use_custom:
                uploaded_file = st.file_uploader("上传对照表 CSV", type=["csv"], help="CSV格式：esperanto,kanji 或 esperanto,kanji,priority")
        if use_custom:
            source_id = "custom"
            st.caption("正在使用自定义CSV。上方的新版、旧版选择不参与本次转换。")
        else:
            st.caption(DICTIONARY_SOURCES[source_id]["description"])
            provenance = source_provenance(source_id)
            st.caption(provenance["label"])
            full_csv, two_column_csv = edition_download_data(source_id)
            st.download_button("下载所选版本的完整词典（CSV）", full_csv, file_name=provenance["dictionary_filename"], mime="text/csv")
            st.download_button("下载所选版本的两列CSV", two_column_csv, file_name=provenance["snippet_filename"], mime="text/csv")
        st.caption("不自动判断新版、旧版。使用中间版本写成或混合新旧分配的文本，可能无法仅凭这两个版本准确还原。请核对创建时的版本记录和上下文。")
        st.markdown("1. 选择文本创建时使用的版本。\n2. 输入汉字化世界语文本。\n3. 转换后核对结果标示的版本和修订编号。")
    return source_id, uploaded_file

def sample_text() -> str:
    return (
        "何时 西o 遇as 东on 和ᴷ 上置as 东an 衣on, 一 唯a 语o 获as 二 显ojn "
        "— 两 美ajn —, 和ᴷ 生成as 新a 解o."
    )


def main() -> None:
    st.set_page_config(
        page_title="汉字化世界语 → 字母转换器",
        page_icon="🔤",
        layout="wide",
    )

    st.title("🔤 汉字化世界语 → 字母转换器")
    st.caption(
        "📖 项目指南: "
        "[中文](https://takatakatake.github.io/kanji_assign/index.zh.html) / "
        "[日本語](https://takatakatake.github.io/kanji_assign/index.html) / "
        "[한국어](https://takatakatake.github.io/kanji_assign/index.ko.html)"
    )
    st.markdown("---")

    source_id, uploaded_file = render_sidebar()
    df = load_selected_dataframe(source_id, uploaded_file)
    source_signature = selected_source_signature(source_id, uploaded_file)
    provenance = source_provenance(source_id, uploaded_file)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📝 输入（汉字化世界语）")
        input_text = st.text_area(
            "汉字化世界语文本",
            value=sample_text(),
            height=320,
            help="请输入汉字与字母混合的文本。",
        )

    with col2:
        st.subheader("✅ 输出（字母世界语）")
        if df is None:
            st.info("请选择或上传对照表。")
            return

        mapping = build_mapping_index_cached(dataframe_to_mapping_records(df))
        st.success(f"已加载 {dictionary_label(source_id)}")

        if st.button("🔄 转换", type="primary", use_container_width=True):
            converted_text = convert_kanji_esperanto_to_alphabet(input_text, mapping)
            st.session_state[CONVERTED_TEXT_KEY] = converted_text
            st.session_state[CONVERTED_INPUT_KEY] = input_text
            st.session_state[CONVERTED_SOURCE_KEY] = source_signature
            st.session_state[CONVERTED_PROVENANCE_KEY] = dict(provenance)

        converted_text = st.session_state.get(CONVERTED_TEXT_KEY, "")
        result_provenance = st.session_state.get(CONVERTED_PROVENANCE_KEY) or {}
        result_is_current = (
            st.session_state.get(CONVERTED_INPUT_KEY) == input_text
            and st.session_state.get(CONVERTED_SOURCE_KEY) == source_signature
            and result_provenance.get("identity") == provenance["identity"]
        )

        if converted_text:
            st.caption("转换结果使用的版本: " + result_provenance["label"] if result_provenance else "这是没有版本记录的旧结果，请重新转换。")
            if not result_is_current:
                st.warning("输入或分配方案已更改，请重新转换。")
            st.text_area(
                "转换结果",
                value=converted_text,
                height=320,
                help="输出为全小写的世界语词根。",
            )
            st.download_button(
                label="📥 下载文本",
                data=converted_text,
                file_name=result_provenance.get("result_filename", "esperanto_unversioned_reconvert.txt"),
                mime="text/plain",
                disabled=not result_is_current,
                use_container_width=True,
            )

            if result_is_current:
                st.markdown("---")
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                col_stat1.metric("输入字符数", len(input_text))
                col_stat2.metric("输出字符数", len(converted_text))
                col_stat3.metric("字典条目数", mapping.entry_count)
                col_stat4.metric("最长条目", f"{mapping.max_length}字符")
        else:
            st.info("请点击转换按钮。")

    st.markdown("---")
    with st.expander("ℹ️ 关于本应用"):
        st.markdown("常规版本选项只有持续更新的新版和固定旧版。新版继续反映已采用的修改；旧版保留本轮分配修改前的10,636行。中间快照仍在内部保存。\n\n结果标示和下载文件名包含转换时的版本、修订编号及词典哈希。版本或词典变化后必须重新转换。两列CSV是所选版本的另一种格式；自定义CSV作为独立高级功能保留。\n\n不自动推测中间版本或混合文本。例如，放is 精ˢo在最初旧版中还原为emancipis spermato，在当前新版中为lasis silfo，但中间版本可能表示lasis spermato。需要创建时的记录和上下文。\n\n仍按最长匹配、同长度时priority顺序转换。相邻词根连写可能匹配另一个长键（如酸乳、移植），因此即使版本匹配也不保证所有文本都能唯一还原。")


if __name__ == "__main__":
    main()
