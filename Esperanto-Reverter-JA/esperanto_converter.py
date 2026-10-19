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
        "description": "検討期間中の採用済み変更を反映する新版です。今後の割当修正もこの版へ反映します。",
    },
    # ID は後方互換（セッションキー）のため "legacy-minimal" のまま。中身は
    # 2026-07-04 に現行の漢字割当（全語根）を2列スニペット形式で再生成済み。
    "legacy-minimal": {
        "label": "スニペット用2列CSV（現行割当）",
        "path": LEGACY_CSV,
        "description": "現行の漢字割当を2列（語根,漢字）で収めたスニペット用CSVです。変換結果は「現行割当」と同じになります。",
    },
    "pre-three-short-20261017": {
        "label": "3語根の短縮前（簧=anĉ、2026-10-17）",
        "path": PRE_THREE_SHORT_20261017_CSV,
        "description": "risort=弹簧、anĉ=簧、lantern=灯笼、lubrik=润滑だった直前の辞書です。その表記で保存した文章に使ってください。無印の簧は現行辞書ではrisort、ここではanĉに戻ります。自動判定はしません。",
    },
    "pre-dot-greft-20261018": {
        "label": "移植・妆の割当変更前（2026-10-18）",
        "path": PRE_DOT_GREFT_20261018_CSV,
        "description": "greft=嫁接、dot=嫁妆、tualet=妆だった変更直前の完全な辞書です。旧文の妆をtualetへ復元し、移＋植をtranslaci＋plantとして読む場合に使います。精子系列の承認済み表記を含みます。版を自動判定しません。",
    },
    "pre-sperm-distinction-20261018": {
        "label": "精子・精液の区別変更前（2026-10-18）",
        "path": PRE_SPERM_DISTINCTION_20261018_CSV,
        "description": "spermat=精ˢ、spermati=精ˢᴵ だった変更直前の完全な辞書です。今回より前の表記で保存した文章に使ってください。spermatozoの新規割当は含みません。版を自動判定しません。",
    },
    "pre-satir-20261017": {
        "label": "satir変更前（2026-10-17）",
        "path": PRE_SATIR_20261017_CSV,
        "description": "satir=讽刺、karikatur=讽、sarkasm=讽ˢ だった変更直前の辞書です。無印の讽は現行辞書ではsatir、ここではkarikaturに戻ります。自動判定はしません。",
    },
    "pre-mirror-20261017": {
        "label": "構成語根の識別子修正前（2026-10-17）",
        "path": PRE_MIRROR_20261017_CSV,
        "description": "testikit=丸炎ᵀ、orkidit=丸炎だった時点の辞書です。las=放、ananas=菠、strut=鸵など、その時点までの変更は含みます。修正前に保存した文章に使ってください。",
    },
    "pre-las-20261017": {
        "label": "旧版（固定）",
        "path": PRE_LAS_20261017_CSV,
        "description": "一連の漢字割当変更を始める前の固定旧版です（las=留、emancip=放）。この版の割当は更新しません。",
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

# A displayed kanji identifier is one complete run: e.g. ᴷˢ, ᴷᴹ, ᶜ̂, ᵁ̆.
# These are the modifier letters used by the assignment alphabet plus its two
# combining marks. Do not treat unrelated punctuation as part of an identifier.
_IDENTIFIER_CONTINUATION_CHARS = frozenset("ᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿˢᵀᵁⱽᶻ\u0302\u0306")


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
    esperanto_headers = {"esperanto", "エスペラント語根", "語根"}
    kanji_headers = {"kanji", "漢字", "漢字表記"}
    priority_headers = {"priority", "優先順位", "漢字化優先順位"}
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
        raise FileNotFoundError(f"Dictionary file was not found: {path}")
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


CURRENT_INVERSE_SOURCE_ID = "pejvo-piv-20260620"
CURRENT_INVERSE_ALIAS_PAIRS = {
    '兰炎ᵀ': 'orkidit',
    '盐ᴬ': 'at',
    '盐ᴵ': 'it',
    '炎ᵀ': 'it',
    '兄ᶠᴿ': 'fra',
    '父ᴾᴬ': 'pa',
    '插ᴾ': 'pol',
    '白ᴸᴱ': 'leŭk',
    '远复ᴷ': 'telekopi',
}


def load_current_inverse_aliases() -> tuple[dict, str]:
    """Require a reviewed current dictionary before enabling the closed alias set."""
    raw = (ROOT / "data" / "current_inverse_aliases.json").read_bytes()
    manifest = json.loads(raw)
    aliases = manifest.get("aliases", [])
    pairs = {row["kanji"]: row["esperanto"] for row in aliases}
    if (manifest.get("schema_version") != 1
            or manifest.get("source_id") != CURRENT_INVERSE_SOURCE_ID
            or len(aliases) != len(CURRENT_INVERSE_ALIAS_PAIRS) or pairs != CURRENT_INVERSE_ALIAS_PAIRS
            or manifest.get("required_canonical_owner") != {"kanji": "丸ᴼ炎ᵀ", "esperanto": "orkidit"}
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", manifest.get("revision", ""))):
        raise ValueError("Invalid current inverse alias supplement")
    metadata = json.loads((ROOT / "data" / "current_dictionary_source.json").read_bytes())
    actual = hashlib.sha256(DICTIONARY_SOURCES[CURRENT_INVERSE_SOURCE_ID]["path"].read_bytes()).hexdigest()
    if (actual != manifest.get("current_csv_sha256")
            or actual != metadata.get("current_csv_sha256")
            or metadata.get("revision") != manifest.get("dictionary_revision")):
        raise ValueError("Current inverse supplement requires re-audit: dictionary revision or SHA256 changed")
    return manifest, hashlib.sha256(raw).hexdigest()


def current_inverse_mapping_records(records: tuple[tuple[str, str, str], ...]) -> tuple[tuple[str, str, str], ...]:
    manifest, _ = load_current_inverse_aliases()
    owners = {}
    for root, key, _priority_value in records:
        owners.setdefault(key.strip(), set()).add(root.strip().lower())
    owner = manifest["required_canonical_owner"]
    if owners.get(owner["kanji"]) != {owner["esperanto"]}:
        raise ValueError("Current inverse supplement requires re-audit: canonical orkidit owner changed")
    additions = []
    for row in manifest["aliases"]:
        key, root = row["kanji"], row["esperanto"]
        if key in owners:
            if owners[key] != {root}:
                raise ValueError(f"Current inverse alias conflicts with an existing root: {key}")
        else:
            additions.append((root, key, "0"))
    return records + tuple(additions)


def current_effective_download_data(source_id: str) -> bytes:
    """Export the current UI records without changing the canonical CSV exports."""
    if source_id != CURRENT_INVERSE_SOURCE_ID:
        raise ValueError("The current inverse supplement belongs only to the primary current edition")
    records = effective_mapping_records(source_id, load_dictionary_source(source_id))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(("esperanto", "kanji", "priority"))
    writer.writerows(records)
    return output.getvalue().encode("utf-8")


LEGACY_INVERSE_SOURCE_ID = "pre-las-20261017"
LEGACY_INVERSE_ALIAS_PAIRS = {
    '丸ᵀ炎ᵀ': 'testikit',
    '丸ᴼ炎ᵀ': 'orkidit',
    '兰炎ᵀ': 'orkidit',
    '盐ᴬ': 'at',
    '盐ᴵ': 'it',
    '炎ᵀ': 'it',
    '兄ᶠᴿ': 'fra',
    '父ᴾᴬ': 'pa',
    '插ᴾ': 'pol',
    '白ᴸᴱ': 'leŭk',
    '两ᴴ': 'herm',
    '名ᴺᴵ': 'nim',
    '远声ᶠᴼ': 'telefon',
    '微镜ˢᴷ': 'mikroskop',
    '氧生ᴳ': 'oksigen',
    '间学ᴸᴺ': 'interlingvistik',
    '越形具ᴬ': 'transformator',
    '单色ᴷᴿ': 'monokromat',
    '醋盐ᴬ': 'acetat',
    '气血ᴱ': 'aeremi',
    '锐名ᴼ': 'akronim',
    '醇盐ᴬ': 'alkoholat',
    '醇血ᴱ': 'alkoholemi',
    '替具ᴬ': 'alternator',
    '铝盐ᴬ': 'aluminiat',
    '担子菌ᴹᶜ': 'bazidimicet',
    '担子菌ᴹᴵ': 'bazidimikot',
    '青盐ᴬ': 'cianat',
    '青植ᶠ': 'cianfit',
    '青化ᴵᴰ': 'cianid',
    '三角洲似ᴼ': 'deltoid',
    '从氧糖ᴼ': 'deoksioz',
    '节学ᴵ': 'dietik',
    '二ᴰᴵ氯化ᴵᴰ': 'diklorid',
    '膨具ᴬ': 'dilatator',
    '二ᴰᴵ硫化ᴵᴰ': 'disulfid',
    '甘苦ᴬ': 'dolĉamar',
    '胚植ᶠ': 'embrifit',
    '胚源ᴳ': 'embrigenez',
    '胚切ᵀᴹ': 'embritomi',
    '骨端炎ᵀ': 'epifizit',
    '咽炎ᵀ': 'faringit',
    '磷盐ᴬ': 'fosfat',
    '磷盐ᴬ血ᴱ': 'fosfatemi',
    '磷化ᴵᴰ': 'fosfid',
    '磷盐ᴵ': 'fosfit',
    '果糖ᴼ': 'fruktoz',
    '牙肉炎ᵀ': 'gingivit',
    '土源ᴳ': 'grundgenez',
    '卤化ᴵᴰ': 'halogenid',
    '半盲ᴬ': 'hemianopsi',
    '半瘫ᴾᴸ': 'hemiplegi',
    '半球ˢ': 'hemisfer',
    '肝炎ᵀ': 'hepatit',
    '超血ᴱ': 'hiperemi',
    '超感ᴱ': 'hiperestez',
    '超名ᴼ': 'hiperonim',
    '超压ᵀ': 'hipertensi',
    '超养ᵀ': 'hipertrofi',
    '亚皮ᴰ': 'hipoderm',
    '亚感ᴱ': 'hipoestez',
    '亚胃ᴳ': 'hipogastr',
    '亚舌ᴳ': 'hipoglos',
    '亚软骨ᴷᴺ': 'hipokondr',
    '亚名ᴺᴵ': 'hiponim',
    '亚滞ˢᶻ': 'hipostaz',
    '亚压ᵀ': 'hipotensi',
    '亚题ᵀᶻ': 'hipotez',
    '间声ᶠᴼ': 'interfon',
    '等ᴵ青盐ᴬ': 'izocianat',
    '隔计ᴹ': 'izolmetr',
    '碘化ᴵᴰ': 'jodid',
    '碘基ᴵ': 'jodil',
    '算计ᴹ': 'kalkulmetr',
    '炭化ᴵᴰ': 'karbid',
    '碳盐ᴬ': 'karbonat',
    '碳化ᴵᴰ': 'karbonid',
    '碳基ᴵ': 'karbonil',
    '阴蒂除ᴱᴷ': 'klitorektomi',
    '氯盐ᴬ': 'klorat',
    '氯血ᴱ': 'kloremi',
    '氯化ᴵᴰ': 'klorid',
    '氯化ᴵᴰ血ᴱ': 'kloridemi',
    '氯盐ᴵ': 'klorit',
    '股痛ᴬ': 'koksalgi',
    '股炎ᵀ': 'koksit',
    '色计ᴹ': 'kolormetr',
    '色测ᴹᵀ': 'kolormetri',
    '换具ᴬ': 'komutator',
    '弦炎ᵀ': 'kordit',
    '冻测ᴹᵀ': 'kriometri',
    '栽具ᴬ': 'kultivator',
    '乳糖ᴼ': 'laktoz',
    '举具ᴬ': 'levator',
    '脾除ᴱᴷ': 'lienektomi',
    '脾炎ᵀ': 'lienit',
    '蜗牛': 'limak',
    '纵隔炎ᵀ': 'mediastinit',
    '米学ᴵ': 'metrik',
    '肌炎ᵀ': 'miit',
    '微影ᶠ': 'mikrofilm',
    '微声ᶠᴼ': 'mikrofon',
    '微粒ᴳ': 'mikrograjn',
    '微槽ᴷ': 'mikrokanel',
    '微菌ᴷᴷ': 'mikrokok',
    '微石ᴸᵀ': 'mikrolit',
    '微切ᵀᴼ': 'mikrotom',
    '万足ᴾᴼ': 'miriapod',
    '髓炎ᵀ': 'mjelit',
    '单配ᴳ': 'monogami',
    '单志ᴳ': 'monografi',
    '单字ᴳᴹ': 'monogram',
    '单石ᴸᵀ': 'monolit',
    '单话ᴸ': 'monolog',
    '单形ᴹᴵ': 'monomorfi',
    '单瓣ᴾ': 'monopetal',
    '单体ˢᴹ': 'monosom',
    '粘症ᴼ': 'mukoz',
    '筋症ᴼ': 'muskoloz',
    '氮化ᴵᴰ': 'nitrid',
    '号具ᴬ': 'numerator',
    '渗计ᴹ': 'osmozmetr',
    '骨痛ᴬ': 'ostalgi',
    '骨除ᴱᴷ': 'ostektomi',
    '骨炎ᵀ': 'ostit',
    '胰除ᴱᴷ': 'pankreatektomi',
    '胰炎ᵀ': 'pankreatit',
    '雨计ᴹ': 'pluvmetr',
    '谓能ᴵ': 'predikativ',
    '肺炎ᵀ': 'pulmit',
    '瓤炎ᵀ': 'pulpit',
    '刨具ᴬ': 'rabotator',
    '规具ᴬ': 'regulator',
    '蔗盐ᴬ': 'sakarat',
    '蔗糖ᴼ': 'sakaroz',
    '柳盐ᴬ': 'salikat',
    '无感ᴱ': 'senestez',
    '巩膜炎ᵀ': 'sklerotit',
    '刮具ᴬ': 'skrapator',
    '声计ᴹ': 'sonmetr',
    '水苏糖ᴼ': 'stakioz',
    '胃炎ᵀ': 'stomakit',
    '硫盐ᴬ': 'sulfat',
    '硫青盐ᴬ': 'sulfcianat',
    '硫化ᴵᴰ': 'sulfid',
    '硫盐ᴵ': 'sulfit',
    '远影ᶠ': 'telefilm',
    '远动ᴷᶻ': 'telekinez',
    '远令ᴷ': 'telekomand',
    '远复ᴷ': 'telekopi',
    '远计ᴹ': 'telemetr',
    '疹似ᴼ': 'tifoid',
    '三体ˢᴹ': 'trisom',
    '篡员ᴬᵀ': 'uzurpator',
    '汽计ᴹ': 'vapormetr',
    '精丘炎ᵀ': 'verumontanit',
    '振具ᴬ': 'vibrator',
    '载具ᴬ': 'ŝarĝator',
}


def load_legacy_inverse_aliases() -> tuple[dict, str]:
    """Validate the bounded inverse-only supplement against the fixed CSV."""
    raw = (ROOT / "data" / "legacy_inverse_aliases.json").read_bytes()
    manifest = json.loads(raw)
    aliases = manifest.get("aliases", [])
    pairs = {row["kanji"]: row["esperanto"] for row in aliases}
    if (manifest.get("schema_version") != 1
            or manifest.get("source_id") != LEGACY_INVERSE_SOURCE_ID
            or len(aliases) != len(LEGACY_INVERSE_ALIAS_PAIRS) or pairs != LEGACY_INVERSE_ALIAS_PAIRS
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", manifest.get("revision", ""))):
        raise ValueError("Invalid fixed-old inverse alias supplement")
    expected = EDITION_POLICY["fixed_csv_sha256"]
    actual = hashlib.sha256(DICTIONARY_SOURCES[LEGACY_INVERSE_SOURCE_ID]["path"].read_bytes()).hexdigest()
    if manifest.get("fixed_csv_sha256") != expected or actual != expected:
        raise ValueError("The fixed pre-assignment dictionary has changed")
    return manifest, hashlib.sha256(raw).hexdigest()


def effective_mapping_records(source_id: str, df: pd.DataFrame) -> tuple[tuple[str, str, str], ...]:
    """Keep generic loaders intact; apply only the explicitly selected edition supplement."""
    records = dataframe_to_mapping_records(df)
    if source_id == CURRENT_INVERSE_SOURCE_ID:
        return current_inverse_mapping_records(records)
    if source_id != LEGACY_INVERSE_SOURCE_ID:
        return records
    manifest, _ = load_legacy_inverse_aliases()
    owners = {}
    for root, key, _priority_value in records:
        owners.setdefault(key.strip(), set()).add(root.strip().lower())
    additions = []
    for row in manifest["aliases"]:
        key, root = row["kanji"], row["esperanto"]
        if key in owners:
            if owners[key] != {root}:
                raise ValueError(f"Fixed-old inverse alias conflicts with an existing root: {key}")
        else:
            additions.append((root, key, "0"))
    return records + tuple(additions)


def legacy_effective_download_data(source_id: str) -> bytes:
    """Export the same three-column records used by the fixed-old UI converter."""
    if source_id != LEGACY_INVERSE_SOURCE_ID:
        raise ValueError("The inverse supplement belongs only to the fixed old edition")
    records = effective_mapping_records(source_id, load_dictionary_source(source_id))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(("esperanto", "kanji", "priority"))
    writer.writerows(records)
    return output.getvalue().encode("utf-8")


@st.cache_data(show_spinner=False)
def _build_mapping_index_payload_cached(
    records: tuple[tuple[str, str, str], ...],
) -> tuple[Dict[int, Dict[str, str]], List[int], int]:
    df = pd.DataFrame(records, columns=["esperanto", "kanji", "priority"])
    mapping = build_mapping_index(df)
    return mapping.by_length, mapping.lengths_desc, mapping.entry_count


def build_mapping_index_cached(records: tuple[tuple[str, str, str], ...]) -> MappingIndex:
    # Streamlit replaces __main__ between runs/sessions. Cache only builtins,
    # then reconstruct the class belonging to this invocation.
    by_length, lengths_desc, entry_count = _build_mapping_index_payload_cached(records)
    return MappingIndex(
        by_length=by_length,
        lengths_desc=lengths_desc,
        entry_count=entry_count,
    )


# Preserve the public cache-clearing API, including per-record invalidation.
build_mapping_index_cached.clear = _build_mapping_index_payload_cached.clear


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
            end = i + length
            # This applies to every key, including older whole-word keys. Merely
            # rejecting an added alias could fall back to the same truncated ID.
            if end < len(text) and text[end] in _IDENTIFIER_CONTINUATION_CHARS:
                continue
            substring = text[i:end]
            replacement = mapping.by_length[length].get(substring)
            if replacement is None:
                continue
            result.append(replacement)
            i += length
            matched = True
            break

        if not matched:
            end = i + 1
            if text[i] in _IDENTIFIER_CONTINUATION_CHARS:
                # Preserve an unknown run together; do not restart matching in
                # its middle and accidentally consume a recognized short suffix.
                while end < len(text) and text[end] in _IDENTIFIER_CONTINUATION_CHARS:
                    end += 1
            result.append(text[i:end])
            i = end

    return "".join(result).lower()


def load_selected_dataframe(source_id: str, uploaded_file) -> pd.DataFrame | None:
    try:
        if source_id == "custom":
            if uploaded_file is None:
                return None
            size = getattr(uploaded_file, "size", 0) or 0
            if size > MAX_UPLOAD_BYTES:
                st.error(
                    f"アップロードされたCSVが大きすぎます（{size / 1024 / 1024:.1f} MB）。"
                    f"{MAX_UPLOAD_BYTES // 1024 // 1024} MB 以下にしてください。"
                )
                return None
            return read_assignment_csv(uploaded_file)
        return load_dictionary_source(source_id)
    except Exception as exc:
        st.error(f"対応表の読み込みに失敗しました: {exc}")
        return None


def dictionary_options() -> List[str]:
    return list(VISIBLE_EDITION_IDS)

def dictionary_label(source_id: str) -> str:
    if source_id == "custom":
        return "カスタム CSV"
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
    result = {
        "source_id": source_id, "edition": edition, "revision": revision,
        "edition_id": {"new": "current", "old": "legacy"}.get(edition, edition),
        "dictionary_sha256": digest, "identity": f"{source_id}:{revision}:{digest}",
        "label": f"{dictionary_label(source_id)} / {revision} / {digest[:12]}",
        "result_filename": f"esperanto_{stamp}.txt",
        "dictionary_filename": f"dictionary_{stamp}.csv",
        "snippet_filename": f"dictionary_{stamp}_2col.csv",
    }
    if source_id == LEGACY_INVERSE_SOURCE_ID:
        supplement, supplement_sha = load_legacy_inverse_aliases()
        supplement_revision = supplement["revision"]
        supplement_stamp = f"inverse_{supplement_revision}_{supplement_sha[:12]}"
        result.update({
            "inverse_compatibility_revision": supplement_revision,
            "inverse_compatibility_sha256": supplement_sha,
            "identity": result["identity"] + f":{supplement_revision}:{supplement_sha}",
            "label": result["label"] + f" / inverse: {supplement_revision} / {supplement_sha[:12]}",
            "result_filename": f"esperanto_{stamp}_{supplement_stamp}.txt",
            "effective_dictionary_filename": f"dictionary_{stamp}_{supplement_stamp}.csv",
        })
    elif source_id == CURRENT_INVERSE_SOURCE_ID:
        supplement, supplement_sha = load_current_inverse_aliases()
        supplement_revision = supplement["revision"]
        supplement_stamp = f"inverse_{supplement_revision}_{supplement_sha[:12]}"
        result.update({
            "inverse_compatibility_revision": supplement_revision,
            "inverse_compatibility_sha256": supplement_sha,
            "identity": result["identity"] + f":{supplement_revision}:{supplement_sha}",
            "label": result["label"] + f" / inverse: {supplement_revision} / {supplement_sha[:12]}",
            "result_filename": f"esperanto_{stamp}_{supplement_stamp}.txt",
            "effective_dictionary_filename": f"dictionary_{stamp}_{supplement_stamp}.csv",
        })
    return result



def edition_download_data(source_id: str) -> tuple[bytes, bytes]:
    """Offer a format choice within one edition, without creating another edition."""
    raw = DICTIONARY_SOURCES[source_id]["path"].read_bytes()
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerows((row["esperanto"], row["kanji"]) for row in rows)
    return raw, output.getvalue().encode("utf-8")

def _restore_input_widget(key: str, default) -> None:
    # Hidden widgets are cleaned up by Streamlit. Keep user input separately
    # from widget state, without treating a restored input as a fresh result.
    if key not in st.session_state:
        st.session_state[key] = st.session_state.get("saved_" + key, default)


def _remember_input_widget(key: str, clear_html: bool = False) -> None:
    st.session_state["saved_" + key] = st.session_state[key]
    if clear_html:
        _clear_html_recovery_result()


def render_sidebar() -> tuple[str, object | None]:
    _restore_input_widget("plain_edition", DEFAULT_DICTIONARY_ID)
    _restore_input_widget("use_custom_csv", False)
    with st.sidebar:
        st.header("使用する版")
        source_id = st.selectbox(
            "新版・旧版を選択", dictionary_options(),
            index=dictionary_options().index(DEFAULT_DICTIONARY_ID),
            format_func=dictionary_label,
            disabled=bool(st.session_state.get("use_custom_csv", False)),
            key="plain_edition", on_change=_remember_input_widget,
            args=("plain_edition",),
        )
        uploaded_file = None
        with st.expander("上級：カスタムCSV"):
            use_custom = st.checkbox("カスタムCSVを使用する", key="use_custom_csv",
                                     on_change=_remember_input_widget, args=("use_custom_csv",))
            if use_custom:
                uploaded_file = st.file_uploader("対応表 CSV をアップロード", type=["csv"], help="CSV形式: esperanto,kanji または esperanto,kanji,priority")
        if use_custom:
            source_id = "custom"
            st.caption("カスタムCSVを使用中です。上の新版・旧版の選択は変換に使いません。")
        else:
            st.caption(DICTIONARY_SOURCES[source_id]["description"])
            provenance = source_provenance(source_id)
            st.caption(provenance["label"])
            full_csv, two_column_csv = edition_download_data(source_id)
            st.download_button("選択した版の辞書をダウンロード（CSV）", full_csv, file_name=provenance["dictionary_filename"], mime="text/csv")
            st.download_button("選択した版の2列CSVをダウンロード", two_column_csv, file_name=provenance["snippet_filename"], mime="text/csv")
            if source_id == LEGACY_INVERSE_SOURCE_ID:
                st.caption(f"上の2つのCSVは固定旧版の原本で、{len(LEGACY_INVERSE_ALIAS_PAIRS)}件の復元補助を含みません。このアプリと同じ逆変換には、下の補助込みCSVを使えます。")
                st.download_button("旧版の逆変換辞書（復元補助込み）をダウンロード", legacy_effective_download_data(source_id), file_name=provenance["effective_dictionary_filename"], mime="text/csv")
            elif source_id == CURRENT_INVERSE_SOURCE_ID:
                st.caption(f"上の2つのCSVは新版の正本で、{len(CURRENT_INVERSE_ALIAS_PAIRS)}件の復元補助を含みません。このアプリと同じ逆変換には、下の補助込みCSVを使えます。")
                st.download_button("新版の逆変換辞書（復元補助込み）をダウンロード", current_effective_download_data(source_id), file_name=provenance["effective_dictionary_filename"], mime="text/csv")
        st.caption("新版・旧版を自動判定しません。変更途中の版で書いた文章や新旧が混在する文章は、この2版だけでは意図どおりに戻らない場合があります。作成時の版情報と文脈を確認してください。")
        st.markdown("1. 文章を作成した版を選びます。\n2. 漢字化エスペラント文を入力します。\n3. 変換し、結果に表示された版・改訂番号を確認します。")
    return source_id, uploaded_file

def sample_text() -> str:
    return (
        "何时 西o 遇as 东on 和ᴷ 上置as 东an 衣on, 一 唯a 语o 获as 二 显ojn "
        "— 两 美ajn —, 和ᴷ 生成as 新a 解o."
    )


def _clear_html_recovery_result() -> None:
    st.session_state.pop("html_recovery_result", None)


def _change_recovery_input_mode() -> None:
    _clear_html_recovery_result()
    # Preserve inputs, but require a fresh conversion after changing workflows.
    st.session_state.pop(CONVERTED_INPUT_KEY, None)


def _forget_html_upload() -> None:
    # Also runs when the user removes/replaces a file: never fall back to it.
    st.session_state.pop("saved_html_recovery_file", None)
    _clear_html_recovery_result()


@st.dialog("保存内容の確認", width="large", on_dismiss="rerun")
def show_result_save_dialog(text: str, filename: str, label: str, key: str) -> None:
    # Immutable arguments are the server-validated snapshot. The modal blocks
    # background edits; downloading itself must not rerun an input workflow.
    st.caption(filename)
    st.text_area("保存する本文", value=text, height=320, disabled=True,
                 key="result_save_preview")
    st.download_button(label, data=text.encode("utf-8"), file_name=filename,
                       mime="text/plain", on_click="ignore", key=key)
    if st.button("閉じる", key="close_result_save_dialog"):
        st.rerun()


def render_html_recovery() -> None:
    # This path reads recorded Esperanto, without loading or applying a dictionary.
    from html_source_recovery import (
        HtmlRecoveryError, HtmlRubyModeError, decode_html_upload, recover_standard_html,
    )
    _restore_input_widget("html_recovery_direction", "kanji")
    _restore_input_widget("html_recovery_source_kind", "paste")

    st.subheader("標準HTMLから原語を復元")
    st.caption("このプロジェクトの標準HTMLに残っているエスペラントを読み取ります。漢字の逆引きをしないため、辞書の新版・旧版を選ぶ必要はありません。")
    st.caption("作成時のルビ形式を選んでください。HTMLに形式の記録があれば選択と照合します。記録のない旧HTML・編集済みHTML・自作JSONの形式は自動判別しません。変換時に使い終えた @・% の目印や、統一前の文字表記は復元しません。")
    st.caption("ファイル・貼り付けとも、UTF-8で10 MiBまでの標準HTMLに対応します。")
    direction = st.radio(
        "HTML作成時のルビ形式", ("kanji", "annotation"),
        format_func={"kanji": "漢字ルビ（漢字の上にエスペラント）", "annotation": "注釈ルビ（エスペラントの上に訳）"}.__getitem__,
        key="html_recovery_direction", on_change=_remember_input_widget,
        args=("html_recovery_direction", True),
    )
    source_kind = st.radio(
        "HTMLの入力方法", ("paste", "upload"),
        format_func={"paste": "HTMLソースを貼り付ける", "upload": "HTMLファイルをアップロードする"}.__getitem__,
        key="html_recovery_source_kind", on_change=_remember_input_widget,
        args=("html_recovery_source_kind", True),
        horizontal=True,
    )
    source = None
    if source_kind == "paste":
        _restore_input_widget("html_recovery_paste", "")
        source = st.text_area(
            "HTMLソース", height=280, key="html_recovery_paste",
            help="ブラウザに表示された文章ではなく、アプリのHTMLソースを貼り付けてください。",
            on_change=_remember_input_widget, args=("html_recovery_paste", True),
        )
    else:
        uploaded_html = st.file_uploader(
            "標準HTMLファイル（UTF-8）", type=["html", "htm"],
            key="html_recovery_upload", on_change=_forget_html_upload,
        )
        if uploaded_html is not None:
            try:
                source = decode_html_upload(uploaded_html.getvalue())
                st.session_state["saved_html_recovery_file"] = {
                    "source": source, "name": uploaded_html.name,
                }
            except HtmlRecoveryError as exc:
                _forget_html_upload()
                st.error(f"HTMLファイルを読み込めません: {exc}")
        elif st.session_state.get("saved_html_recovery_file"):
            saved = st.session_state["saved_html_recovery_file"]
            source = saved["source"]
            st.caption("保持中のファイル: " + saved["name"])
            st.button("保持中のファイルを解除", key="html_recovery_forget_upload",
                      on_click=_forget_html_upload)
    identity = hashlib.sha256(json.dumps(
        [source_kind, direction, source], ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    if st.button("HTMLから復元する", type="primary", disabled=not source,
                 key="html_recovery_submit"):
        _clear_html_recovery_result()
        try:
            result = recover_standard_html(source, direction)
            st.session_state["html_recovery_result"] = {**result, "identity": identity}
        except HtmlRubyModeError as exc:
            if exc.reason == "mismatch":
                recorded = {"kanji": "漢字ルビ", "annotation": "注釈ルビ"}[exc.recorded_mode]
                st.error(f"HTMLに記録された形式は「{recorded}」です。選択した形式と異なるため復元を止めました。入力は保持しています。上のルビ形式を選び直してください。")
            elif exc.reason == "duplicate":
                st.error("HTMLのルビ形式が重複して記録されています（異なる形式の混在も含みます）。形式を確定できないため復元を止めました。入力は保持しています。")
            else:
                st.error("HTMLに記録されたルビ形式が空か、対応していない値です。復元を止めました。入力は保持しています。")
        except HtmlRecoveryError as exc:
            st.error(f"HTMLを復元できません: {exc}")

    result = st.session_state.get("html_recovery_result")
    if result and result.get("identity") != identity:
        _clear_html_recovery_result()
        result = None
    if result:
        edition = result.get("assignment_edition", "unknown")
        edition_label = {"current": "新版", "legacy": "旧版", "custom_json": "自作JSON", "unknown": "不明（版情報なし）"}.get(edition, "不明")
        st.caption(f"HTMLに記録された版: {edition_label} ／ 読み取ったルビ: {result['ruby_count']}個")
        if result.get("recorded_ruby_mode"):
            st.caption("HTMLに記録されたルビ形式と選択が一致しています。")
        st.text_area("復元した原語", value=result["text"], height=280, disabled=True,
                     help="HTMLに残る大文字・空白を保持した結果です。")
        if st.button("保存内容を確認", key="html_recovery_prepare_save") and result.get("identity") == identity:
            show_result_save_dialog(
                result["text"], f"esperanto_html_{edition}_{direction}_{identity[:12]}.txt",
                "復元した原語をダウンロード", "html_recovery_download",
            )


def main() -> None:
    st.set_page_config(
        page_title="漢字化エスペラント → アルファベット変換",
        page_icon="🔤",
        layout="wide",
    )

    st.title("漢字化エスペラント → アルファベット変換")
    st.caption(
        "📖 プロジェクトガイド: "
        "[日本語](https://takatakatake.github.io/kanji_assign/index.html) / "
        "[한국어](https://takatakatake.github.io/kanji_assign/index.ko.html) / "
        "[中文](https://takatakatake.github.io/kanji_assign/index.zh.html)"
    )
    st.markdown("---")

    input_mode = st.radio(
        "入力形式", ("plain", "html"),
        format_func={"plain": "漢字化された平文を逆変換", "html": "標準HTMLから原語を復元"}.__getitem__,
        key="reverter_input_mode", horizontal=True,
        on_change=_change_recovery_input_mode,
    )
    if input_mode == "html":
        render_html_recovery()
        return

    source_id, uploaded_file = render_sidebar()
    df = load_selected_dataframe(source_id, uploaded_file)
    source_signature = selected_source_signature(source_id, uploaded_file)
    provenance = source_provenance(source_id, uploaded_file)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("入力（漢字化エスペラント）")
        _restore_input_widget("plain_input_text", sample_text())
        input_text = st.text_area(
            "漢字化エスペラント文",
            height=320,
            help="漢字とアルファベットが混在した文章を入力してください。",
            key="plain_input_text", on_change=_remember_input_widget,
            args=("plain_input_text",),
        )

    with col2:
        st.subheader("出力（アルファベット）")
        if df is None:
            st.info("対応表を選択またはアップロードしてください。")
            return

        mapping = build_mapping_index_cached(effective_mapping_records(source_id, df))
        st.success(f"{dictionary_label(source_id)} を読み込みました")

        if st.button("変換する", type="primary", use_container_width=True):
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
            st.caption("変換結果の版: " + result_provenance["label"] if result_provenance else "版情報のない以前の結果です。再変換してください。")
            if not result_is_current:
                st.warning("入力または割当案が変わっています。再変換してください。")
            st.text_area(
                "変換結果",
                value=converted_text,
                height=320,
                disabled=True,
                help="すべて小文字のエスペラント語根として出力します。",
            )
            if st.button("保存内容を確認", key="plain_prepare_save",
                         disabled=not result_is_current, use_container_width=True) and result_is_current:
                show_result_save_dialog(
                    converted_text, result_provenance.get("result_filename", "esperanto_unversioned_reconvert.txt"),
                    "テキストをダウンロード", "plain_confirmed_download",
                )

            if result_is_current:
                st.markdown("---")
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                col_stat1.metric("入力文字数", len(input_text))
                col_stat2.metric("出力文字数", len(converted_text))
                col_stat3.metric("辞書エントリ数", mapping.entry_count)
                col_stat4.metric("最長エントリ", f"{mapping.max_length}文字")
        else:
            st.info("変換ボタンをクリックしてください。")

    st.markdown("---")
    with st.expander("このアプリについて"):
        st.markdown("通常の版選択は、新版と固定旧版の2つです。新版は今後の採用済み変更を反映し、旧版は一連の割当変更前の10,636行を保持します。中間スナップショットは内部に保存しています。\n\n結果の表示とダウンロードファイル名には、変換時の版・改訂番号・辞書ハッシュを付けます。版や辞書が変わった場合は再変換が必要です。2列CSVは選択した版の形式違いで、カスタムCSVは独立した上級機能です。\n\n中間版や混在文を新旧どちらかへ自動推定しません。たとえば「放is 精ˢo」は初期旧版ではemancipis spermato、現時点の新版ではlasis silfoですが、途中版でlasis spermatoを表した可能性もあります。作成時の記録と文脈が必要です。\n\n変換は従来どおり最長一致、同長ではpriority順です。隣接する語根の連結が別の長いキーと一致する場合（酸乳、移植など）は、版を合わせても一意に復元できるとは限りません。")


if __name__ == "__main__":
    main()
