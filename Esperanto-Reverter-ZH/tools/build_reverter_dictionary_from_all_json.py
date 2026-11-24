#!/usr/bin/env python3
"""Build a reverter CSV from kanji-esperanto-monaco all.json."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from dictionary_source import CURRENT_CSV, default_monaco_source, validate_current_source


# Esperanto diacritic letters written as a base letter + a marker. Monaco's sourceRoot
# uses BOTH the h-system caret form (g^ -> ĝ) and the x-system form (gx -> ĝ); we must
# restore both to real Unicode so the reverter's roots are valid Esperanto (e.g. the root
# "igx" is iĝ, not a literal "igx"). Esperanto has no native letter x, so an x right after
# c/g/h/j/s/u is always an x-system marker.
ESPERANTO_DIGRAPH_MAP = {
    "c": "ĉ",
    "g": "ĝ",
    "h": "ĥ",
    "j": "ĵ",
    "s": "ŝ",
    "u": "ŭ",
}


def to_unicode_esperanto_root(value: str, fallback: str = "") -> str:
    root = (value or fallback or "").strip().strip(",")
    if "," in root:
        parts = [part.strip() for part in root.split(",") if part.strip()]
        root = parts[0] if parts else root

    out = []
    i = 0
    while i < len(root):
        ch = root[i]
        nxt = root[i + 1] if i + 1 < len(root) else ""
        # Scan left-to-right: a marker (^ or x) modifies the single letter before it.
        if nxt in ("^", "x", "X"):
            mapped = ESPERANTO_DIGRAPH_MAP.get(ch.lower())
            if mapped:
                out.append(mapped)
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out).lower()


def rows_from_all_json(data: dict) -> list[dict[str, object]]:
    rows = []
    for index, item in enumerate(data.get("items", [])):
        kanji = str(item.get("body", "")).strip()
        if not kanji:
            continue
        esperanto = to_unicode_esperanto_root(
            str(item.get("sourceRoot", "")),
            str(item.get("prefix", "")),
        )
        if not esperanto:
            continue
        priority = item.get("priority", index)
        try:
            priority = int(priority)
        except (TypeError, ValueError):
            priority = index
        rows.append(
            {
                "esperanto": esperanto,
                "kanji": kanji,
                "priority": priority,
                "source_root": str(item.get("sourceRoot", "")).strip(),
                "source_line": item.get("sourceLine", ""),
            }
        )

    # Reverse-only aliases preserve texts written before the approved assignment updates.
    # Add them only when the input contains the corresponding current assignment;
    # historical/custom sources keep their own mapping. They never become Monaco
    # forward-completion entries. Longest matching handles 菠萝蜜 before 菠萝/菠.
    aliases = (
        ("ananas", "菠", "菠萝", "20261017"),
        ("jakv", "菠蜜", "菠萝蜜", "20261017"),
        ("strut", "鸵", "鸵鸟", "20261017"),
        ("sinergi", "协同", "协同作用", "20261017"),
        ("oliv", "榄", "橄榄", "20261017"),
        ("stafilokok", "葡球菌", "葡萄球菌", "20261017"),
        ("psitak", "鹦ᴾˢ", "鹦鹉", "20261017"),
        ("uv", "葡ᵁ", "葡萄", "20261017"),
        ("limon", "柠", "柠檬", "20261017"),
        ("limonad", "柠水", "柠檬水", "20261017"),
        ("uve", "葡膜", "葡萄膜", "20261017"),
        ("uveit", "葡膜炎ᵀ", "葡萄膜炎ᵀ", "20261017"),
        ("observatori", "观台", "天文台", "20261017"),
        ("risort", "簧", "弹簧", "20261017"),
        ("lantern", "灯ᴸᴺ", "灯笼", "20261017"),
        ("lubrik", "滑ᴸ", "润滑", "20261017"),
        ("protez", "假体", "假肢", "20261017"),
        ("ranc", "酸败", "哈喇", "20261017"),
        ("krep", "皱布", "皱绸", "20261017"),
        ("difrakt", "绕射", "衍射", "20261017"),
        ("mortez", "卯", "卯眼", "20261017"),
        ("meger", "恶女", "悍妇", "20261017"),
        ("sutur", "缝ˢᴿ", "缝合", "20261017"),
        ("fraj", "卵ᶠ", "鱼卵", "20261017"),
        ("nostalgi", "怀ᴺ", "怀旧", "20261017"),
        ("onk", "瘤ᴼ", "肿瘤", "20261017"),
        ("fortres", "堡ᶠᴿ", "堡垒", "20261017"),
        ("onkogen", "瘤ᴼ生ᴳ", "肿瘤生ᴳ", "20261017"),
        ("onkologi", "瘤ᴼ学ᴸᴳ", "肿瘤学ᴸᴳ", "20261017"),
        ("satir", "讽", "讽刺", "20261017"),
        ("sarkasm", "讽ˢᴿ", "讽ˢ", "20261017"),
        ("spermati", "精子ˢᴵ", "精ˢᴵ", "20261018"),
        ("silf", "精ˢ", "精ˢᴸ", "20261018"),
        ("spermatocit", "精子胞ᶜᴵ", "精ˢ胞ᶜᴵ", "20261018"),
        ("spermatofit", "精子植ᶠ", "精ˢ植ᶠ", "20261018"),
        ("spermatogenez", "精子源ᴳ", "精ˢ源ᴳ", "20261018"),
        ("greft", "移植", "嫁接", "20261018"),
        ("dot", "妆", "嫁妆", "20261018"),
        ("frog", "轨叉", "辙叉", "20261107"),
        ("mitoz", "丝分", "等分", "20261108"),
        ("kariokinez", "丝分ᴷ", "等分ᴷ", "20261108"),
        ("ambl", "对侧步", "踱", "20261108"),
        ("spekulativ", "思辨", "猜ˢ", "20261108"),
        ("invit", "招", "邀", "20261111"),
        ("vermic^el", "细面", "粉丝", "20261112"),
        ("piruet", "旋ᴾ", "旋ᴾᴿ", "20261112"),
        ("admir", "赏", "佩", "20261113"),
        ("inteligent", "智ᴵᴳ", "聪", "20261113"),
        ("inund", "洪", "淹", "20261113"),
        ("masaĝ", "揉ᴹ", "摩", "20261114"),
        ("paŭz", "停ᴾ", "歇", "20261114"),
        ("gajn", "获ᴳ", "赢", "20261114"),
        ("sor", "升ˢ", "腾", "20261114"),
        ("sakristi", "圣器室", "圣器", "20261114"),
        ("sambuk", "接骨木", "接骨", "20261114"),
        ("svarm", "群ˢ", "拥", "20261114"),
        ("beton", "混凝土", "混凝", "20261114"),
        ("ego", "我ᴱ", "吾", "20261115"),
        ("egoist", "我ᴱ家", "己ᴱ", "20261115"),
        ("rekrut", "新兵", "征募", "20261115"),
        ("grenat", "榴石", "石榴", "20261115"),
        ("ŝaŭm", "泡", "沫", "20261115"),
        ("kvorum", "够数", "足数", "20261115"),
        ("piktur", "绘", "描ᴾᴷ", "20261116"),
        ("flan", "饼ᶠ", "蛋奶", "20261118"),
        ("aline", "段ᴬ", "换行", "20261118"),
        ("ekvator", "赤道", "赤", "20261118"),
        ("halofit", "盐ᴴ植ᶠ", "草ᴴᶠ", "20261120"),
        ("deodar", "雪松ᴰ", "木ᴰᴰ", "20261120"),
        ("duk", "爵ᴰ", "公爵", "20261120"),
        ("izatis", "狐ᴵ", "兽ᴵ", "20261120"),
        ("mug", "松ᴹ", "木ᴹᵁ", "20261120"),
        ("dig", "堤", "拦", "20261120"),
        ("klementin", "橘ᴷ", "木ᴷᴸᴱ", "20261120"),
        ("hektar", "百亩ᴴ", "公顷", "20261120"),
        ("korsak", "狐ᴷ", "兽ᴷˢ", "20261121"),
        ("hematit", "赤铁矿", "矿ᴴ", "20261121"),
        ("kolokazi", "芋", "草ᴷᶻ", "20261121"),
        ("kolokasi", "芋ᴷˢ", "草ᴷᴼᴸ", "20261121"),
        ("orcin", "虎鲸ᴼᶜ", "兽ᴼᴿ", "20261121"),
        ("grosulari", "醋栗ᴳᴸ", "木ᴳˢ", "20261121"),
        ("unci", "豹ᵁ", "兽ᵁᶜ", "20261123"),
        ("fenikopter", "火烈鸟ᶠᴱ", "鸟ᶠᴾ", "20261123"),
        ("polen", "花粉ᴾᴸ", "粉ᴾᴺ", "20261123"),
        ("otari", "海狮ᴼ", "兽ᴼ", "20261123"),
        ("pakiderm", "厚皮ᴾᴷ", "兽ᴾᴷ", "20261123"),
        ("polenolog", "花粉ᴾᴸ学家", "粉ᴾᴺ学家", "20261123"),
        ("polenologi", "花粉ᴾᴸ学ᴸᴳ", "粉ᴾᴺ学ᴸᴳ", "20261123"),
        ("polenoz", "花粉ᴾᴸ症ᴼ", "粉ᴾᴺ症ᴼ", "20261123"),
        ("hektar", "百亩", "公顷", "20261123"),
        ("polen", "花粉", "粉ᴾᴺ", "20261123"),
        ("otari", "海狮", "兽ᴼ", "20261123"),
        ("pakiderm", "厚皮", "兽ᴾᴷ", "20261123"),
        ("polenolog", "花粉学家", "粉ᴾᴺ学家", "20261123"),
        ("polenologi", "花粉学ᴸᴳ", "粉ᴾᴺ学ᴸᴳ", "20261123"),
        ("polenoz", "花粉症ᴼ", "粉ᴾᴺ症ᴼ", "20261123"),
        ("otari", "海狮", "海狮ᴼ", "20261123"),
        ("pakiderm", "厚皮", "厚皮ᴾᴷ", "20261123"),
        ("polen", "花粉", "花粉ᴾᴸ", "20261123"),
        ("hektar", "百亩", "百亩ᴴ", "20261123"),
        ("tripanosom", "原兽", "原兽ᵀ", "20261123"),
        ("deism", "神主义", "神主义ᴰ", "20261123"),
        ("deist", "神家", "神家ᴰ", "20261123"),
        ("dodekaedr", "十二面ᴱ", "十二面ᴱᴰ", "20261123"),
        ("kseroftalmi", "干ᴷ目ᴼᶠ", "干ᴷ目ᴼᶠᴷ", "20261123"),
        ("metapsiki", "超ᴹ心ᴾˢ", "超ᴹ心ᴾˢᴹ", "20261123"),
        ("pedofili", "童ᴾ爱ᶠ", "童ᴾ爱ᶠᴾ", "20261123"),
        ("polifoni", "多ᴾ声ᶠᴼ", "多ᴾ声ᶠᴼᴾ", "20261123"),
        ("polipodi", "多ᴾ足ᴾᴼ", "多ᴾ足ᴾᴼᴾ", "20261123"),
        ("polenolog", "花粉学家", "花粉ᴾᴸ学家", "20261123"),
        ("polenologi", "花粉学ᴸᴳ", "花粉ᴾᴸ学ᴸᴳ", "20261123"),
        ("polenoz", "花粉症ᴼ", "花粉ᴾᴸ症ᴼ", "20261123"),
        ("impertinent", "无礼", "放肆", "20261123"),
        ("supermarkt", "超市", "市ˢ", "20261123"),
        ("manat", "海牛", "兽ᴹᴬ", "20261123"),
        ("dugong", "海牛ᴰ", "兽ᴰᴳ", "20261123"),
        ("rosmar", "海象", "海豹ᴿ", "20261123"),
        ("universitat", "大学", "学ᵁ", "20261123"),
        ("boac", "驯鹿ᴮ", "鹿ᴮ", "20261123"),
        ("karibu", "驯鹿ᴷ", "兽ᴷᴿ", "20261123"),
        ("apotek", "药店", "药ᴬ", "20261124"),
    )
    for root, current_body, old_body, date in aliases:
        current = [row for row in rows if row["source_root"] == root and row["kanji"] == current_body]
        if not current:
            continue
        if len(current) != 1:
            raise ValueError(f"Expected one current reverse mapping for {root}")
        existing = [row for row in rows if row["kanji"] == old_body]
        if any(row["esperanto"] != to_unicode_esperanto_root(root) for row in existing):
            raise ValueError(f"Historical alias {old_body} conflicts with another root")
        if not existing:
            rows.append({**current[0], "kanji": old_body, "source_line": f"reverse-alias:{date}"})

    rows.sort(key=lambda row: (-len(row["kanji"]), row["priority"], row["kanji"], row["esperanto"]))
    return rows


def current_rows_from_all_json(data: dict) -> list[dict[str, object]]:
    """Add the separately approved current-edition senses, never to custom input.

    The ordinary Monaco completion keeps its existing one-spelling owner. Only
    the current reverter receives this explicitly selected sense's extra key.
    Both the source data and the sense projection are pinned by the manifest.
    """
    import hashlib

    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "data/current_dictionary_source.json").read_bytes())
    bundled_path = root / "data/monaco_source_20261017.json"
    bundled = bundled_path.read_bytes()
    if hashlib.sha256(bundled).hexdigest() != manifest["monaco_all_sha256"]:
        raise ValueError("Current source bytes do not match the approved manifest")
    if data != json.loads(bundled):
        raise ValueError("Current sense assignments require the exact approved source")
    sense_path = root / "data/explicit_sense_assignments_20261111.json"
    raw = sense_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["explicit_sense_assignments_sha256"]:
        raise ValueError("Current sense assignments do not match the approved manifest")
    senses = json.loads(raw)
    if senses.get("schema_version") != 1:
        raise ValueError("Unsupported explicit-sense assignment data")
    rows = rows_from_all_json(data)
    # Some normal learner forms retain a literal linking i from their decomposition.
    # Record only the spellings produced by the reviewed forward data in the bundled edition.
    owners = {row["kanji"]: row for row in rows}
    for root_name, body, retained_vowels in (
        ("metapsiki", "超ᴹ心ᴾˢ", ("i",)),
        ("polipodi", "多ᴾ足ᴾᴼ", ("i",)),
        ("kseroftalmi", "干ᴷ目ᴼᶠ", ("io",)),
        ("pedofili", "童ᴾ爱ᶠ", ("io",)),
        ("polifoni", "多ᴾ声ᶠᴼ", ("io", "ia")),
    ):
        base = owners[body]
        if base["esperanto"] != root_name:
            raise ValueError(f"Unexpected single-root owner for {body}")
        for vowels in retained_vowels:
            key = body + vowels
            if key in owners:
                raise ValueError(f"Conflicting normal-form key {key}")
            rows.append({**base, "kanji": key, "esperanto": root_name + vowels[1:],
                         "source_line": "learner-form:20261123"})
    for sense in senses["senses"]:
        if sense.get("edition") != "current" or sense.get("selection") != "explicit_occurrence":
            raise ValueError("Only explicitly selected current-edition senses are supported")
        owner = sense["root"]
        body = sense["display"]
        if not owner or not body or body == sense["reserved_bare"]:
            raise ValueError("Explicit sense needs a distinct nonempty identifier")
        base = [row for row in rows
                if row["source_root"] == owner
                and row["kanji"] == sense["default_display"]]
        if len(base) != 1 or base[0]["esperanto"] != owner:
            raise ValueError("Explicit sense's established base owner has changed")
        if any(row["kanji"] == body for row in rows):
            raise ValueError("Explicit sense key conflicts with an existing key")
        rows.append({**base[0], "kanji": body,
                     "source_line": "explicit-sense:" + sense["sense_key"] + ":20261111"})
    rows.sort(key=lambda row: (-len(row["kanji"]), row["priority"], row["kanji"], row["esperanto"]))
    return rows


def write_rows(rows: list[dict[str, object]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["esperanto", "kanji", "priority", "source_root", "source_line"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if len(sys.argv) == 1:
        in_path = default_monaco_source()
        out_path = CURRENT_CSV
    elif len(sys.argv) == 3:
        in_path = Path(sys.argv[1])
        out_path = Path(sys.argv[2])
    else:
        print(
            "Usage: tools/build_reverter_dictionary_from_all_json.py [<all.json> <out.csv>]",
            file=sys.stderr,
        )
        return 2

    if out_path.resolve() == CURRENT_CSV.resolve():
        try:
            validate_current_source(in_path)
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    data = json.loads(in_path.read_text(encoding="utf-8"))
    rows = (current_rows_from_all_json(data) if out_path.resolve() == CURRENT_CSV.resolve()
            else rows_from_all_json(data))
    write_rows(rows, out_path)

    print(f"wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
