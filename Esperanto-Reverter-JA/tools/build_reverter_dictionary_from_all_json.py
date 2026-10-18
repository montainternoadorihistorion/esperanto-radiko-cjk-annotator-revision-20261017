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
    for root, current_body, old_body in (("ananas", "菠", "菠萝"), ("jakv", "菠蜜", "菠萝蜜"), ("strut", "鸵", "鸵鸟"), ("sinergi", "协同", "协同作用"), ("oliv", "榄", "橄榄"), ("stafilokok", "葡球菌", "葡萄球菌"), ("psitak", "鹦ᴾˢ", "鹦鹉"), ("uv", "葡ᵁ", "葡萄"), ("limon", "柠", "柠檬"), ("limonad", "柠水", "柠檬水"), ("uve", "葡膜", "葡萄膜"), ("uveit", "葡膜炎ᵀ", "葡萄膜炎ᵀ"), ("observatori", "观台", "天文台"), ("risort", "簧", "弹簧"), ("lantern", "灯ᴸᴺ", "灯笼"), ("lubrik", "滑ᴸ", "润滑"), ("protez", "假体", "假肢"), ("ranc", "酸败", "哈喇"), ("krep", "皱布", "皱绸"), ("difrakt", "绕射", "衍射"), ("mortez", "卯", "卯眼"), ("meger", "恶女", "悍妇"), ("sutur", "缝ˢᴿ", "缝合"), ("fraj", "卵ᶠ", "鱼卵"), ("nostalgi", "怀ᴺ", "怀旧"), ("onk", "瘤ᴼ", "肿瘤"), ("fortres", "堡ᶠᴿ", "堡垒"), ("onkogen", "瘤ᴼ生ᴳ", "肿瘤生ᴳ"), ("onkologi", "瘤ᴼ学ᴸᴳ", "肿瘤学ᴸᴳ"), ("satir", "讽", "讽刺"), ("sarkasm", "讽ˢᴿ", "讽ˢ"), ("spermati", "精子ˢᴵ", "精ˢᴵ"), ("silf", "精ˢ", "精ˢᴸ"), ("spermatocit", "精子胞ᶜᴵ", "精ˢ胞ᶜᴵ"), ("spermatofit", "精子植ᶠ", "精ˢ植ᶠ"), ("spermatogenez", "精子源ᴳ", "精ˢ源ᴳ"), ("greft", "移植", "嫁接"), ("dot", "妆", "嫁妆")):
        current = [row for row in rows if row["source_root"] == root and row["kanji"] == current_body]
        if not current:
            continue
        if len(current) != 1:
            raise ValueError(f"Expected one current reverse mapping for {root}")
        existing = [row for row in rows if row["kanji"] == old_body]
        if any(row["esperanto"] != root for row in existing):
            raise ValueError(f"Historical alias {old_body} conflicts with another root")
        if not existing:
            rows.append({**current[0], "kanji": old_body, "source_line": "reverse-alias:20261018" if root in {'dot', 'greft', 'spermati', 'silf', 'spermatofit', 'spermatogenez', 'spermatocit'} else "reverse-alias:20261017"})

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
    rows = rows_from_all_json(data)
    write_rows(rows, out_path)

    print(f"wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
