"""Two assignment editions; conversion engine and learning annotations are shared."""
from pathlib import Path
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
import subprocess
from urllib.parse import quote

import streamlit as st

EDITIONS = ("current", "legacy")
LABELS = {
    "JA": {"current": "新版（更新中）", "legacy": "旧版（固定）"},
    "ZH": {"current": "新版（更新中）", "legacy": "旧版（固定）"},
    "KO": {"current": "신판（갱신 중）", "legacy": "구판（고정）"},
}
GLOBAL = "全域替换用のリスト(列表)型配列(replacements_final_list)"
LOCAL = "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"
TWO = "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"
KANJI_CSV = "世界语词根-汉字对应列表_参照2新割当_7791.csv"
RUBY_CSV = {"JA": "エスペラント語根-日本語訳ルビ対応リスト.csv", "ZH": "世界语词根-中文注释对应列表.csv", "KO": "에스페란토 어근-한국어 번역 루비 대응 목록.csv"}

# Only these lowercase surfaces were reviewed against the existing kanji-ruby
# correction. Pure text has no ruby spelling from which the generic stranded-
# letter detector can recover them. Do not broaden this to all auto-corrections
# (for example, sene must retain its existing pure-mode behavior).
REVIEWED_PURE_DECOMPOSITIONS = (
    "ksen/as", "ksen/o", "ksen/oj", "ksen/ojn",
    "ksen/os", "ksen/u", "ksen/ul/o", "ksen/us",
)


def _is_bundled_pure_path(path):
    root = Path(__file__).resolve().parent.parent
    return Path(path).resolve() in (
        root / "Esperanto-Kanji-Ruby-JA" / "app_data" / "置換リスト_漢字_純粋置換.json",
        root / "assignment_editions" / "legacy" / "JA" / "pure.json.gz",
    )


def _with_reviewed_pure_corrections(global_rules, local_rules):
    """Add boundary-only rules, using this edition's existing @ root glyphs.

    The frozen JSON, root assignments and @ rules remain untouched. No bare
    rule is added or shadowed, so an unreviewed compound cannot be caught by a
    substring replacement. Longer existing entries keep their precedence;
    later user/session overlays can still shadow these exact-word rules.
    """
    roots = {}
    for old, new, _ in local_rules:
        if old in ("ksen", "ul"):
            if old in roots and roots[old] != new:
                raise ValueError("Conflicting reviewed pure root: " + old)
            roots[old] = new
    if set(roots) != {"ksen", "ul"}:
        raise ValueError("Reviewed pure correction requires ksen and ul roots")

    corrections = []
    used = {rule[2].strip() for rule in global_rules}
    for index, decomp in enumerate(REVIEWED_PURE_DECOMPOSITIONS):
        word = decomp.replace("/", "")
        rendered = "".join(roots.get(part, part) for part in decomp.split("/"))
        token = f"${9120000 + index}$"
        if token in used:
            raise ValueError("Reviewed pure placeholder is already in use: " + token)
        corrections.append((word, [" " + word + " ", " " + rendered + " ", " " + token + " "]))

    # Compute positions against the original ordering, then insert together.
    # This mirrors the longer-entry precedence used by manual corrections,
    # without their broad shadowing of any existing bare-word entry.
    positions = [0] * len(corrections)
    for index, rule in enumerate(global_rules):
        candidate = rule[0].strip()
        for correction_index, (word, _) in enumerate(corrections):
            if len(candidate) > len(word) and word in candidate:
                positions[correction_index] = index + 1
    additions = {}
    for position, (_, rule) in zip(positions, corrections):
        additions.setdefault(position, []).append(rule)
    output = []
    for index, rule in enumerate(global_rules):
        output.extend(additions.get(index, ()))
        output.append(rule)
    output.extend(additions.get(len(global_rules), ()))
    return output


def checked_edition(edition):
    if edition not in EDITIONS:
        raise ValueError("Unknown assignment edition: " + repr(edition))
    return edition


def language(data_dir):
    name = Path(data_dir).resolve().parent.name
    for lang in LABELS:
        if name.endswith("-" + lang):
            return lang
    raise ValueError("Unknown app language: " + name)


def root_dir(data_dir):
    return Path(data_dir).resolve().parents[1]


def resolve_path(data_dir, role, edition="current"):
    checked_edition(edition)
    data = Path(data_dir).resolve()
    if role == "ruby":
        return data / "置換リスト_ルビ.json"
    if role == "ruby_csv":
        return data / RUBY_CSV[language(data)]
    if edition == "legacy":
        owner = "JA" if role == "pure" else language(data)
        filename = {"kanji": "kanji.json.gz", "pure": "pure.json.gz", "kanji_csv": "kanji.csv"}[role]
        return root_dir(data) / "assignment_editions" / "legacy" / owner / filename
    if role == "pure":
        return root_dir(data) / "Esperanto-Kanji-Ruby-JA" / "app_data" / "置換リスト_漢字_純粋置換.json"
    return data / {"kanji": "置換リスト_漢字.json", "kanji_csv": KANJI_CSV}[role]


def _stamp(path):
    stat = Path(path).stat()
    return stat.st_mtime_ns, stat.st_size


@st.cache_data(max_entries=64, show_spinner=False)
def _file_hash(path, stamp):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_hash(path):
    return _file_hash(str(Path(path).resolve()), _stamp(path))


@st.cache_data(max_entries=1, show_spinner=False)
def _load_lists_cached(path, stamp):
    # Only the requested edition/mode is decoded. Do not retain a second full
    # table per edition, or independent copies for the main and manual pages.
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        payload = json.load(f)
    global_rules = payload.get(GLOBAL, [])
    local_rules = payload.get(LOCAL, [])
    if _is_bundled_pure_path(path):
        global_rules = _with_reviewed_pure_corrections(global_rules, local_rules)
    return global_rules, local_rules, payload.get(TWO, [])


def load_lists_path(path):
    path = str(Path(path).resolve())
    return _load_lists_cached(path, _stamp(path))


def load_lists(data_dir, mode, edition="current"):
    return load_lists_path(resolve_path(data_dir, mode, edition))


def edition_signature(data_dir, edition="current"):
    """Content-derived, so every later data-only revision changes the signature."""
    checked_edition(edition)
    roles = ("kanji", "pure", "kanji_csv", "ruby", "ruby_csv")
    content = {role: file_hash(resolve_path(data_dir, role, edition)) for role in roles}
    data = Path(data_dir).resolve()
    for name in ("char_widths.json", "user_corrections.json"):
        content[name] = file_hash(data / name)
    for name in ("esp_text_replacement_module.py", "esp_overlay_module.py", "esp_replacement_json_make_module.py", "esp_assignment_edition.py"):
        content[name] = file_hash(data.parent / name)
    serialized = json.dumps({"edition_id": edition, "files": content}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def result_metadata(data_dir, edition, custom_json_sha=None, render_options=None):
    lang = language(data_dir)
    assignment = edition_signature(data_dir, edition)
    session = [{k: c.get(k) for k in ("word", "decomp", "_disabled")}
               for c in st.session_state.get("user_corrections_session", [])]
    corrections = hashlib.sha256(json.dumps(session, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    signature = hashlib.sha256(json.dumps([assignment, corrections, custom_json_sha, render_options], sort_keys=True).encode("utf-8")).hexdigest()
    custom_label = {"JA": "自作JSON（割り当て版の選択対象外）", "ZH": "自定义JSON（不使用所选分配版本）", "KO": "사용자 JSON（선택한 배정 판 적용 안 함）"}[lang]
    return {"schema_version": 1, "edition_id": None if custom_json_sha else checked_edition(edition),
            "requested_edition": edition, "source_id": "custom_json" if custom_json_sha else edition,
            "edition_label": custom_label if custom_json_sha else LABELS[lang][edition],
            "signature": signature, "assignment_signature": assignment,
            "corrections_sha256": corrections, "custom_json_sha256": custom_json_sha,
            "render_options": render_options, "automatic_correction": "shared_current_annotations" if custom_json_sha else "selected_edition",
            "created_utc": datetime.now(timezone.utc).isoformat()}


def result_matches(metadata, data_dir, edition, custom_json_sha=None, render_options=None):
    expected = result_metadata(data_dir, edition, custom_json_sha, render_options)
    return bool(metadata and metadata.get("source_id") == expected["source_id"] and
                metadata.get("signature") == expected["signature"])


def download_filename(base, metadata, extension):
    return f"{base}_{metadata['source_id']}_{metadata['signature'][:12]}.{extension}"


def _remember_selection():
    st.session_state["assignment_edition"] = st.session_state["_assignment_edition_widget"]


def select_edition(data_dir):
    lang = language(data_dir)
    value = st.session_state.get("assignment_edition", "current")
    checked_edition(value)
    # A permanent non-widget key survives Streamlit page/widget cleanup.
    st.session_state["_assignment_edition_widget"] = value
    title = {"JA": "漢字割り当ての版", "ZH": "汉字分配版本", "KO": "한자 배정 판"}[lang]
    selected = st.selectbox(title, EDITIONS, format_func=LABELS[lang].__getitem__,
                            key="_assignment_edition_widget", on_change=_remember_selection)
    st.session_state["assignment_edition"] = selected
    captions = {
        "JA": "旧版は今回の見直し前の割り当てで固定、新版は更新を続けます。注釈は両版で共通の最新データを使います。",
        "ZH": "旧版固定为本轮修订前的分配，新版继续更新。两版共用最新注释。",
        "KO": "구판은 이번 검토 전의 배정으로 고정되며 신판은 계속 갱신됩니다. 두 판은 최신 주석을 공유합니다。",
    }
    st.caption(captions[lang])
    return selected


def stale_result_notice(data_dir, metadata):
    lang = language(data_dir)
    label = (metadata or {}).get("edition_label", "?")
    messages = {
        "JA": f"前の結果は「{label}」で作成されています。版・モード・データ・補正のいずれかが変わったため、もう一度「変換する」を押してください。",
        "ZH": f"上次结果使用“{label}”。版本、模式、数据或校正已更改，请重新转换。",
        "KO": f"이전 결과는 ‘{label}’로 작성되었습니다. 판·모드·데이터·보정이 변경되었으므로 다시 변환해 주세요。",
    }
    st.info(messages[lang])


def html_download_metadata(metadata):
    return ("<!-- assignment-edition:" + metadata["source_id"] +
            " signature:" + metadata["signature"] +
            " created-utc:" + metadata["created_utc"] + " -->\n")


@st.cache_data(max_entries=32, show_spinner=False)
def _pinned_asset_url(root, relative, digest, commit):
    """Only publish links to exact committed bytes in this public repository."""
    repository = "montainternoadorihistorion/esperanto-radiko-cjk-annotator-revision-20261017"
    try:
        origin = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=root,
                                         text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
        if repository.lower() not in origin.lower():
            return None
        top = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root,
                                          text=True, stderr=subprocess.DEVNULL, timeout=5).strip())
        path = Path(root) / relative
        git_path = path.resolve().relative_to(top.resolve()).as_posix()
        expected = subprocess.check_output(["git", "rev-parse", commit + ":" + git_path], cwd=root,
                                          text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
        actual = subprocess.check_output(["git", "hash-object", "--no-filters", str(path)], cwd=root,
                                        text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
        if actual != expected:
            return None
        return "https://raw.githubusercontent.com/" + repository + "/" + commit + "/" + quote(relative)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def pinned_asset_url(data_dir, path):
    root = root_dir(data_dir)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                         text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            return None
        relative = Path(path).resolve().relative_to(root).as_posix()
        return _pinned_asset_url(str(root), relative, file_hash(path), commit)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
