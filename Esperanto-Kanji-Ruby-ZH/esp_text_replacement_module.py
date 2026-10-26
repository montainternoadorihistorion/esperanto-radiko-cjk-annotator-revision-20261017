"""
esp_text_replacement_module.py

本模块是“针对世界语文本进行字符串（汉字等）替换”的一系列工具函数。
主要功能：
1. 将各种世界语标记形式（带 x 的 cx, gx...、或带 ^ 的 c^, g^...）转换到字上符形式（ĉ, ĝ, ĥ 等）
2. 实现 %...%（跳过替换） 和 @...@（局部替换）的逻辑
3. safe_replace()：使用 placeholder（占位符）进行安全替换
4. orchestrate_comprehensive_esperanto_text_replacement()：综合替换流程的核心函数
5. parallel_process()：使用多进程来并行处理长文本

代码大体结构：
- 定义若干世界语字符转换的字典（如 x_to_circumflex 等）
- 提供若干辅助函数（unify_halfwidth_spaces, convert_to_circumflex...）
- 提供对 %...%、@...@ 的专门处理
- 提供 orchestrate_comprehensive_esperanto_text_replacement()，将多种替换整合起来
- parallel_process() / process_segment() 用于多进程并行处理长文本时的替换
"""

import re
import json
from typing import List, Tuple, Dict
import multiprocessing

# ================================
# 1) 世界语字符转换相关的字典
# ================================
x_to_circumflex = {'cx': 'ĉ', 'gx': 'ĝ', 'hx': 'ĥ', 'jx': 'ĵ', 'sx': 'ŝ', 'ux': 'ŭ',
                   'Cx': 'Ĉ', 'Gx': 'Ĝ', 'Hx': 'Ĥ', 'Jx': 'Ĵ', 'Sx': 'Ŝ', 'Ux': 'Ŭ'}
circumflex_to_x = {'ĉ': 'cx', 'ĝ': 'gx', 'ĥ': 'hx', 'ĵ': 'jx', 'ŝ': 'sx', 'ŭ': 'ux',
                   'Ĉ': 'Cx', 'Ĝ': 'Gx', 'Ĥ': 'Hx', 'Ĵ': 'Jx', 'Ŝ': 'Sx', 'Ŭ': 'Ux'}

x_to_hat = {'cx': 'c^', 'gx': 'g^', 'hx': 'h^', 'jx': 'j^', 'sx': 's^', 'ux': 'u^',
            'Cx': 'C^', 'Gx': 'G^', 'Hx': 'H^', 'Jx': 'J^', 'Sx': 'S^', 'Ux': 'U^'}
hat_to_x = {'c^': 'cx', 'g^': 'gx', 'h^': 'hx', 'j^': 'jx', 's^': 'sx', 'u^': 'ux',
            'C^': 'Cx', 'G^': 'Gx', 'H^': 'Hx', 'J^': 'Jx', 'S^': 'Sx', 'U^': 'Ux'}

hat_to_circumflex = {'c^': 'ĉ', 'g^': 'ĝ', 'h^': 'ĥ', 'j^': 'ĵ', 's^': 'ŝ', 'u^': 'ŭ',
                     'C^': 'Ĉ', 'G^': 'Ĝ', 'H^': 'Ĥ', 'J^': 'Ĵ', 'S^': 'Ŝ', 'U^': 'Ŭ'}
circumflex_to_hat = {'ĉ': 'c^', 'ĝ': 'g^', 'ĥ': 'h^', 'ĵ': 'j^', 'ŝ': 's^', 'ŭ': 'u^',
                     'Ĉ': 'C^', 'Ĝ': 'G^', 'Ĥ': 'H^', 'Ĵ': 'J^', 'Ŝ': 'S^', 'Ŭ': 'U^'}

# ================================
# 2) 基本的字符转换函数
# ================================
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str:
    """
    将文本中的若干 key 替换为对应的 value。
    例如，{'cx': 'ĉ', ...} 可以把“cx”全部替换成“ĉ”。
    """
    for original_char, converted_char in char_dict.items():
        text = text.replace(original_char, converted_char)
    return text

def convert_to_circumflex(text: str) -> str:
    """
    将给定文本中的世界语特殊字母统一转换为字上符形式（ĉ, ĝ, ĥ, ĵ, ŝ, ŭ等）。
    实际包括两步：hat_to_circumflex（将 c^转为ĉ 等），x_to_circumflex（将 cx转为ĉ 等）。
    """
    text = replace_esperanto_chars(text, hat_to_circumflex)
    text = replace_esperanto_chars(text, x_to_circumflex)
    return text

def unify_halfwidth_spaces(text: str) -> str:
    """
    将文本中的各种半角空白（如 \u00A0, \u2002 等）统一为 ASCII 标准半角空格 (U+0020)。
    不处理全角空格 (U+3000)。
    """
    pattern = r"[\u00A0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A]"
    return re.sub(pattern, " ", text)

# ================================
# 3) 占位符（placeholder）相关
# ================================

def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    """
    执行安全替换：replacements 列表中每个元素是 (old, new, placeholder)。
    先把 text 中的 old 全部替换为 placeholder，再把 placeholder 替换为 new。
    这样可避免重复替换或交叉覆盖的问题。
    """
    valid_replacements = {}
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)
    return text

def import_placeholders(filename: str) -> List[str]:
    """
    从指定文件读取 placeholder 列表。文件中每行一个 placeholder，返回一个列表。
    """
    with open(filename, 'r') as file:
        placeholders = [line.strip() for line in file if line.strip()]
    return placeholders

# -------------------------------
# 用于 %...% (跳过替换) 的逻辑
# -------------------------------
PERCENT_PATTERN = re.compile(r'(?<![0-9])%(.{1,50}?)%')  # 50% 等、数字直後の%は開きマーカーにしない
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    """
    在文本中查找形如 %foo% 的片段（1~50 字符），返回匹配部分（不含 %）。
    """
    matches = []
    used_indices = set()

    for match in PERCENT_PATTERN.finditer(text):
        start, end = match.span()
        if start not in used_indices and end-2 not in used_indices:
            matches.append(match.group(1))
            used_indices.update(range(start, end))
    return matches

def create_replacements_list_for_intact_parts(text: str, placeholders: List[str]) -> List[Tuple[str, str]]:
    """
    分析文本中的 %xxx% 段落，把它们映射到 placeholders。
    返回类似 [("%xxx%", placeholder), ...]
    """
    matches = find_percent_enclosed_strings_for_skipping_replacement(text)
    replacements_list_for_intact_parts = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replacements_list_for_intact_parts.append([f"%{match}%", placeholders[i]])
        else:
            break
    return replacements_list_for_intact_parts

# Paired @ markers may enclose part of a word or a whole single-line phrase.
# Mask email-address @ characters only while finding marker spans; keep the
# actual input untouched. A neighboring valid marker must still be recognized.
AT_PATTERN = re.compile(r'@([^@\r\n]+)@')
_EMAIL_PATTERN = re.compile(
    r"(?<![\w@.+-])[\w.!#$%&'*+/=?^`{|}~-]+@(?:(?:[\w-]+\.)+[\w-]+(?![\w-])|[\w-]+(?![\w@.-]))"
)


def _at_enclosed_matches(text):
    masked = list(text)
    for address in _EMAIL_PATTERN.finditer(text):
        masked[address.start() + address.group().index('@')] = '\x00'
    return list(AT_PATTERN.finditer(''.join(masked)))


def _escape_input_symbols(text):
    # Numeric references have no letters that could be mistaken for Esperanto
    # roots (unlike the 'am' in '&amp;'). Restore conventional entities last.
    return text.replace('&', '&#38;').replace('<', '&#60;').replace('>', '&#62;')


def _marker_tokens(placeholders, marker, source, used):
    from itertools import chain, count
    fallback = (f'{marker}{1000000000 + i}{marker}' for i in count())
    for token in chain(placeholders, fallback):
        if token and token not in source and token not in used:
            used.add(token)
            yield token


def _capture_marker_spans(text, matches, tokens, render):
    pieces, captured, end = [], [], 0
    for match in matches:
        token = next(tokens)
        payload = text[match.start(1):match.end(1)]
        pieces.extend((text[end:match.start()], token))
        captured.append((token, render(payload)))
        end = match.end()
    pieces.append(text[end:])
    return ''.join(pieces), captured


# Only these exact lowercase @ payloads were reviewed. Their renderings come
# from the selected local atoms, preserving that language's glosses and IDs.
_REVIEWED_LOCAL_DECOMPOSITIONS = {
    "greganta": ("greg", "ant", "a"),
    "preganta": ("preg", "ant", "a"),
}


# This independent root has no kanji assignment. Preserve it only for complete
# reviewed @ payloads; prefer the selected local atom when it supplies a gloss.
# Standard endings and the existing lower/title/upper spellings are explicit.
# Phrases, compounds, arbitrary prefixes and custom/default JSON are unchanged.
_REVIEWED_LOCAL_ATOMIC_FORMS = {
    form: (form[:len("stalagmit")], form[len("stalagmit"):])
    for ending in ("", "o", "oj", "on", "ojn", "a", "aj", "an", "ajn",
                   "e", "en", "i", "as", "is", "os", "us", "u")
    for word in ("stalagmit" + ending,)
    for form in (word, word.capitalize(), word.upper())
}


def _reviewed_local_atomic_renderings(payloads, local_rules, enabled=False):
    wanted = set(payloads) & _REVIEWED_LOCAL_ATOMIC_FORMS.keys() if enabled else set()
    if not wanted:
        return {}
    needed = {_REVIEWED_LOCAL_ATOMIC_FORMS[word][0] for word in wanted}
    atoms = {}
    for old, new, _ in local_rules:
        if old in needed:
            if not isinstance(new, str) or not new or (old in atoms and atoms[old] != new):
                raise ValueError("Conflicting or empty reviewed atomic root: " + old)
            atoms[old] = new
    # Existing annotated roots keep their established ending annotations too.
    return {word: atoms[root] + safe_replace(ending, local_rules) if root in atoms else word
            for word in wanted
            for root, ending in (_REVIEWED_LOCAL_ATOMIC_FORMS[word],)}


def _reviewed_local_renderings(payloads, local_rules, enabled=False):
    atomic = _reviewed_local_atomic_renderings(payloads, local_rules, enabled)
    wanted = set(payloads) & _REVIEWED_LOCAL_DECOMPOSITIONS.keys() if enabled else set()
    if not wanted:
        return atomic
    needed = {root for word in wanted for root in _REVIEWED_LOCAL_DECOMPOSITIONS[word][:-1]}
    roots = {}
    for old, new, _ in local_rules:
        if old in needed:
            if not isinstance(new, str) or not new or (old in roots and roots[old] != new):
                raise ValueError("Conflicting or empty reviewed local root: " + old)
            roots[old] = new
    if set(roots) != needed:
        raise ValueError("Missing reviewed local roots: " + repr(sorted(needed - roots.keys())))
    return {**atomic, **{word: "".join(roots[root] for root in _REVIEWED_LOCAL_DECOMPOSITIONS[word][:-1])
                  + _REVIEWED_LOCAL_DECOMPOSITIONS[word][-1] for word in wanted}}


def _render_localized_payload(payload, local_rules, finalized, reviewed, escape):
    if payload in reviewed:
        return reviewed[payload]
    if payload in finalized:
        return finalized[payload]
    return safe_replace(escape(payload), local_rules)


def _protect_input_regions(text, skip_tokens, local_tokens, local_rules,
                           global_rules, html_mode, reviewed_local_decompositions: bool = False):
    source, used = text, set()
    escape = _escape_input_symbols if html_mode else lambda value: value
    text, skipped = _capture_marker_spans(
        text, list(PERCENT_PATTERN.finditer(text)),
        _marker_tokens(skip_tokens, '%', source, used), escape,
    )
    matches = _at_enclosed_matches(text)
    payloads = [text[m.start(1):m.end(1)] for m in matches]
    finalized = _finalized_global_renderings_for_exact_matches(payloads, global_rules)

    reviewed = _reviewed_local_renderings(payloads, local_rules, reviewed_local_decompositions)

    def render_local(payload):
        return _render_localized_payload(payload, local_rules, finalized, reviewed, escape)

    text, localized = _capture_marker_spans(
        text, matches, _marker_tokens(local_tokens, '@', source, used), render_local,
    )
    return escape(text), localized, skipped

# @...@ intentionally has its own, often broader, gloss semantics (for
# example @kaj@ differs from the global word).  Exact global reuse is limited
# to this reviewed boundary-correction set; see the central review manifest.
_LOCALIZED_GLOBAL_EXACT_ROOTS = (
    'ddt', 'fortran', 'golfo', 'hiv', 'khz', 'mhz', 'pat!',
    'racionalism', 'racionalist', 'spiritism', 'spiritist',
    'hokkajdon',
)
_LOCALIZED_GLOBAL_EXACT_REVIEWED = frozenset(
    form
    for root in _LOCALIZED_GLOBAL_EXACT_ROOTS
    for form in (root, root.capitalize(), root.upper())
)

def find_at_enclosed_strings_for_localized_replacement(text: str) -> List[str]:
    """Return nonempty single-line @ payloads, including word-internal spans."""
    return [text[m.start(1):m.end(1)] for m in _at_enclosed_matches(text)]


def _finalized_global_renderings_for_exact_matches(
    matches: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
) -> Dict[str, str]:
    """Return exact @...@ words using this language's finalized global rule.

    The first global rule is the shared boundary authority.  Its already-final
    replacement keeps this language's own gloss and its final class/<br>
    calculation.  Local atom replacement remains the fallback for words that
    have no exact global rule.
    """
    wanted = set(matches) & _LOCALIZED_GLOBAL_EXACT_REVIEWED
    finalized = {}
    if not wanted or not replacements_final_list:
        return finalized
    for rule in replacements_final_list:
        if not isinstance(rule, (list, tuple)) or len(rule) < 2:
            continue
        old, new = rule[0], rule[1]
        if not isinstance(old, str) or not isinstance(new, str):
            continue
        left = len(old) - len(old.lstrip(' '))
        right = len(old) - len(old.rstrip(' '))
        end = len(old) - right if right else len(old)
        core = old[left:end]
        if not core or core not in wanted or core in finalized:
            continue
        new_left = len(new) - len(new.lstrip(' '))
        new_right = len(new) - len(new.rstrip(' '))
        if (new_left, new_right) != (left, right):
            raise ValueError(
                f"global exact rule has mismatched structural spaces: {old!r}"
            )
        new_end = len(new) - new_right if new_right else len(new)
        finalized[core] = new[new_left:new_end]
        if len(finalized) == len(wanted):
            break
    unresolved = sorted(wanted - set(finalized))
    if unresolved:
        raise ValueError(
            f"reviewed @local target lacks an exact global rule: {unresolved!r}"
        )
    return finalized

def create_replacements_list_for_localized_replacement(
    text,
    placeholders: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]],
    replacements_final_list: List[Tuple[str, str, str]] = None, reviewed_local_decompositions: bool = False,
) -> List[List[str]]:
    """
    针对文本中出现的 @xxx@，用 replacements_list_for_localized_string 对其中的内容执行 safe_replace。
    最终返回 [("@xxx@", placeholder, replaced_xxx), ...] 形式。
    """
    matches = find_at_enclosed_strings_for_localized_replacement(text)
    finalized_global = _finalized_global_renderings_for_exact_matches(
        matches, replacements_final_list or []
    )
    reviewed = _reviewed_local_renderings(
        matches, replacements_list_for_localized_string, reviewed_local_decompositions
    )
    tmp_replacements_list_for_localized_string = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replaced_match = _render_localized_payload(
                match, replacements_list_for_localized_string, finalized_global, reviewed, lambda value: value
            )
            tmp_replacements_list_for_localized_string.append([f"@{match}@", placeholders[i], replaced_match])
        else:
            break
    return tmp_replacements_list_for_localized_string

# ================================
# 4) 综合替换主函数
# ================================
def orchestrate_comprehensive_esperanto_text_replacement(
    text,
    placeholders_for_skipping_replacements: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]],
    placeholders_for_localized_replacement: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
    replacements_list_for_2char: List[Tuple[str, str, str]],
    format_type: str, reviewed_local_decompositions: bool = False
) -> str:
    """
    进行一系列替换操作：
      1) 统一半角空格
      2) 将 c^, cx 等转为 ĉ, ĝ 等
      3) 把 %...% 段落替换为占位符（跳过后续替换）
      4) 把 @...@ 段落提取、执行局部替换后再替换成占位符
      5) 对其余文本进行大范围替换（replacements_final_list）
      6) 针对 2字词根（replacements_list_for_2char）进行多次替换
      7) 恢复 placeholder
      8) 若是 HTML 形式，替换换行符为 <br>，空白处理等
    """
    text = unify_halfwidth_spaces(text)
    text = convert_to_circumflex(text)
    # 2.4) 異常入力耐性: 番兵文字chr(1)が入力に混入していた場合は除去(単語融合の防止)
    text = text.replace(chr(1), '')
    # 2.45) 改行正規化: CRLF/CR を LF へ(CR は _KEEP に含まれず、行末2字語根の発火を阻害するため)
    text = text.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))
    # Recognize original input spans before HTML escaping or replacement.
    # Percent protection takes priority; repeated text elsewhere is not a match.
    text, localized_parts, intact_parts = _protect_input_regions(
        text, placeholders_for_skipping_replacements,
        placeholders_for_localized_replacement,
        replacements_list_for_localized_string, replacements_final_list,
        "HTML" in format_type, reviewed_local_decompositions=reviewed_local_decompositions,
    )
    # 4.5) 約物パディング(v2): 約物の両側に番兵付き仮想スペースを挿入し、2字語根standalone
    # (' x 'パターン)が「両隣が非文字」の境界でも発火するようにする(出力前に除去・表示不変)。
    # ※%...%保護と@...@局所置換より後に実行する(保護窓50字と@の入力位置を維持と、約物入り
    #   局所規則をrawテキストで照合するため。プレースホルダ %1854%/@5134@ は % @ 数字が
    #   下記_KEEPに含まれるためパディングで壊れない)。
    # _KEEP(パディング除外)の設計根拠:
    #   英字26+字上符12=語の構成文字 / ラテン拡張(À-Ö,Ø-ö,ø-ɏ)=外国固有名詞(ę,ś,ü等)の内部を
    #   境界化しない(Międzygórze等の偽ルビ防止。CJK/かなは境界のまま=中kaj国は発火) /
    #   数字+%+@=プレースホルダ整合に必須(序数3anの無害性は実測済みだが整合上も除外) /
    #   ASCII/U+2019アポストロフィ=詩的語尾省略と定冠詞l'/l’に使うため
    #   基本温存(右側と閉じ引用は下で個別処理) / 空白改行番兵=構造上必須
    _BOL = chr(1)
    import re as _re
    _HAT12 = chr(264) + chr(265) + chr(284) + chr(285) + chr(292) + chr(293) + chr(308) + chr(309) + chr(348) + chr(349) + chr(364) + chr(365)
    _LATEXT = chr(192) + '-' + chr(214) + chr(216) + '-' + chr(246) + chr(248) + '-' + chr(591)
    _APOSTROPHES = chr(39) + chr(8217)
    _KEEP = 'A-Za-z0-9' + _HAT12 + _LATEXT + chr(37) + chr(64) + _APOSTROPHES + ' ' + chr(10) + chr(13) + chr(1)
    _PAD = _re.compile('([^' + _KEEP + '])')
    text = _PAD.sub(lambda _mo: ' ' + _BOL + _mo.group(1) + _BOL + ' ', text)
    # アポストロフィの右側限定パディング(直後が文字): dank'al / dank’al
    # のal・'Mi / ’Mi 引用開きが発火。記号自体は原表記のまま保つ。
    # 左側温存により省略形(l'/kor'/dank')とアポストロフィ入り辞書エントリは無傷。
    _LTR = 'A-Za-z' + _HAT12 + _LATEXT
    _APOS_R = _re.compile('[' + _APOSTROPHES + '](?=[' + _LTR + '])')
    text = _APOS_R.sub(lambda _mo: _mo.group(0) + _BOL + ' ', text)
    # 閉じ引用 mi' 型: o省略形になり得ない2字語根に限り左側もパディング(du/en/ve は duo/eno/veo の
    # 省略があり得るため対象外)。
    _APOS_L = _re.compile('(?<![' + _LTR + '])((?:[Mm]i|[Vv]i|[Nn]i|[Ll]i|[' + chr(348) + chr(349) + ']i|[' + chr(284) + chr(285) + ']i|[Aa]l|[Dd]e|[Ee]l|[' + chr(264) + chr(265) + ']e|[' + chr(264) + chr(265) + ']u|[Ss]e|[Kk]e|[Jj]e|[Dd]a|[Nn]e|[Hh]o|[Oo]k))([' + _APOSTROPHES + '])(?![' + _LTR + '])')
    text = _APOS_L.sub(lambda _mo: _mo.group(1) + ' ' + _BOL + _mo.group(2), text)
    # 行頭(文頭・改行直後)の2字語根対応: 各行頭/行末に番兵付き仮想スペースを挿入
    text = _BOL + ' ' + text.replace(chr(10), ' ' + _BOL + chr(10) + _BOL + ' ') + ' ' + _BOL
    # 大域替换
    valid_replacements = {}
    # 約物入り見出し(bandar-seri-begavano等3,500件超)は、テキスト側がパディング済みのため
    # 生キーでは一致しない。見出し側にも同じパディングを適用した照合キーを【初回のみ前計算】し
    # (リストは起動時ロードで使い回されるためid基準キャッシュ)、ループ内はO(1)辞書引きで
    # フォールバック照合する。置換の優先順序(リスト順)は完全維持。
    # 値キー(old文字列→パディング済みold)のモジュール級キャッシュ。パディングは文字列の
    # 純関数なのでstaleし得ず、サイズは約物入り見出しの異なり数(~3.5K+補正数)で有界。
    # 旧実装は id(リスト) キーだったが、st.cache_data がStreamlit再実行毎に新コピーを返し
    # merge_overlay も新リストを返すため、再実行毎に~3.3MBずつ無制限成長していた。
    _pgc = globals().setdefault('_PUNCT_GG_CACHE', {})
    _pmap = {}
    _sub = lambda _mo: ' ' + _BOL + _mo.group(1) + _BOL + ' '
    for _o, _n, _p in replacements_final_list:
        if (_PAD.search(_o) is not None or _APOS_R.search(_o) is not None
                or _APOS_L.search(_o) is not None):
            # Version the cache key because rule-key normalization now mirrors
            # all three text-side boundary transformations, not only _PAD.
            _cache_key = ('v4', _o)
            _v = _pgc.get(_cache_key)
            if _v is None:
                _v = _PAD.sub(_sub, _o)
                _v = _APOS_R.sub(lambda _mo: _mo.group(0) + _BOL + ' ', _v)
                _v = _APOS_L.sub(
                    lambda _mo: _mo.group(1) + ' ' + _BOL + _mo.group(2), _v
                )
                _pgc[_cache_key] = _v
            _pmap[_o] = _v
    def _remember_global_replacement(placeholder, new):
        # Boundary spaces are structural and may be consumed by a later
        # punctuation/component rule.  Restore the globally unique $...$ core
        # and preserve any surviving outer spaces.
        core = placeholder.strip(' ')
        replacement = new.strip(' ')
        prior = valid_replacements.get(core)
        if prior is not None and prior != replacement:
            raise ValueError(f"conflicting global placeholder core: {core!r}")
        valid_replacements[core] = replacement

    for old, new, placeholder in replacements_final_list:
        if old in text:
            text = text.replace(old, placeholder)
            # Structural edge spaces are word boundaries, not consumed text.
            # A second pass covers neighboring equal words sharing one space.
            if old.startswith(' ') and old.endswith(' ') and old not in placeholder:
                text = text.replace(old, placeholder)
            _remember_global_replacement(placeholder, new)
        else:
            _p_old = _pmap.get(old)
            if _p_old is not None and _p_old in text:
                text = text.replace(_p_old, placeholder)
                if old.startswith(' ') and old.endswith(' ') and _p_old not in placeholder:
                    text = text.replace(_p_old, placeholder)
                _remember_global_replacement(placeholder, new)

    # 2 字母词根：从「固定两遍」改为「反复到不再匹配为止(fixpoint)」。
    #   固定两遍会漏掉连续 3 个以上的 2 字母词缀(如 san/ig/ej/et)，从而产生伪词根。
    #   每一轮用 "!" 的个数唯一化；round0 与旧 pass1、round1 与旧 pass2 完全后向兼容。
    two_char_rounds = []
    _round = 0
    while _round < 12:  # 安全上限(通常 2〜3 轮收敛)
        _d = {}
        _mk = "!" * _round
        for old, new, placeholder in replacements_list_for_2char:
            if old in text:
                ph = _mk + placeholder + _mk
                text = text.replace(old, ph)
                _d[ph] = new
        if not _d:
            break
        two_char_rounds.append(_d)
        _round += 1

    # 恢复 placeholder（从后面的轮次开始＝插入逆序）
    for _d in reversed(two_char_rounds):
        for placeholder, new in reversed(_d.items()):
            text = text.replace(placeholder, new)
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)

    # Remove only the actual delimiters captured above, never literal markers
    # inside protected text or unrelated occurrences of the same payload.
    for token, rendered in localized_parts:
        text = text.replace(token, rendered)
    for token, original in intact_parts:
        text = text.replace(token, original)
    text = text.replace(' ' + _BOL, '').replace(_BOL + ' ', '').replace(_BOL, '')

    # 如果是 HTML 形式，可替换换行符为 <br> 等
    if "HTML" in format_type:
        text = text.replace('&#38;', '&amp;').replace('&#60;', '&lt;').replace('&#62;', '&gt;')
        text = text.replace("\n", "<br>\n")
        text = re.sub(r"   ", "&nbsp;&nbsp;&nbsp;", text)
        text = re.sub(r"  ", "&nbsp;&nbsp;", text)

    return text

# ================================
# 5) 多进程处理长文本
# ================================
def process_segment(
    lines: List[str],
    placeholders_for_skipping_replacements: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]],
    placeholders_for_localized_replacement: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
    replacements_list_for_2char: List[Tuple[str, str, str]],
    format_type: str, reviewed_local_decompositions: bool = False
) -> str:
    """
    用于并行处理的子函数：把若干行拼成一段，然后调用 orchestrate_comprehensive_esperanto_text_replacement。
    """
    segment = ''.join(lines)
    result = orchestrate_comprehensive_esperanto_text_replacement(
        segment,
        placeholders_for_skipping_replacements,
        replacements_list_for_localized_string,
        placeholders_for_localized_replacement,
        replacements_final_list,
        replacements_list_for_2char,
        format_type, reviewed_local_decompositions=reviewed_local_decompositions
    )
    return result

def parallel_process(
    text: str,
    num_processes: int,
    placeholders_for_skipping_replacements: List[str],
    replacements_list_for_localized_string: List[Tuple[str, str, str]],
    placeholders_for_localized_replacement: List[str],
    replacements_final_list: List[Tuple[str, str, str]],
    replacements_list_for_2char: List[Tuple[str, str, str]],
    format_type: str, reviewed_local_decompositions: bool = False
) -> str:
    """
    把文本按行拆分，分配给多个子进程并行处理（process_segment），然后再拼接结果。
    """
    if num_processes <= 1:
        return orchestrate_comprehensive_esperanto_text_replacement(
            text,
            placeholders_for_skipping_replacements,
            replacements_list_for_localized_string,
            placeholders_for_localized_replacement,
            replacements_final_list,
            replacements_list_for_2char,
            format_type, reviewed_local_decompositions=reviewed_local_decompositions
        )

    lines = re.findall(r'.*?\n|.+$', text)
    num_lines = len(lines)
    if num_lines <= 1:
        return orchestrate_comprehensive_esperanto_text_replacement(
            text,
            placeholders_for_skipping_replacements,
            replacements_list_for_localized_string,
            placeholders_for_localized_replacement,
            replacements_final_list,
            replacements_list_for_2char,
            format_type, reviewed_local_decompositions=reviewed_local_decompositions
        )

    lines_per_process = max(num_lines // num_processes, 1)
    ranges = [(i * lines_per_process, (i + 1) * lines_per_process) for i in range(num_processes)]
    ranges[-1] = (ranges[-1][0], num_lines)

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(
            process_segment,
            [
                (
                    lines[start:end],
                    placeholders_for_skipping_replacements,
                    replacements_list_for_localized_string,
                    placeholders_for_localized_replacement,
                    replacements_final_list,
                    replacements_list_for_2char,
                    format_type, reviewed_local_decompositions
                )
                for (start, end) in ranges
            ]
        )

    return ''.join(results)

def apply_ruby_html_header_and_footer(processed_text: str, format_type: str) -> str:
    """
    根据所选 format_type，为文本加上一段 HTML 头尾（主要是 <style> 设定等），
    用于在浏览器渲染时控制 Ruby 字体大小或样式。

    （如果不是 HTML 相关类型，返回原文即可）
    """
    if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换'):
        ruby_style_head = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ruby 显示</title>
<style>
html, body {
  -webkit-text-size-adjust: 100%;
  -moz-text-size-adjust: 100%;
  -ms-text-size-adjust: 100%;
  text-size-adjust: 100%;
}
:root {
  --ruby-color: blue;
  --ruby-font-size: 0.5em;
}
html {
  font-size: 100%;
}
.text-M_M {
  font-size: 1rem!important;
  font-family: Arial, sans-serif;
  line-height: 2.0 !important;
  display: block;
  position: relative;
}
ruby {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  vertical-align: top !important;
  line-height: 2.0 !important;
  margin: 0 !important;
  padding: 0 !important;
  font-size: 1rem !important;
}
rt {
  display: block !important;
  font-size: var(--ruby-font-size);
  color: var(--ruby-color);
  line-height: 1.05;
  text-align: center;
}
rt.XXXS_S {
  --ruby-font-size: 0.3em;
  margin-top: -8.3em !important;
  transform: translateY(-0em) !important;
}
rt.XXS_S {
  --ruby-font-size: 0.3em;
  margin-top: -7.2em !important;
  transform: translateY(-0em) !important;
}
rt.XS_S {
  --ruby-font-size: 0.3em;
  margin-top: -6.1em !important;
  transform: translateY(-0em) !important;
}
rt.S_S {
  --ruby-font-size: 0.4em;
  margin-top: -4.85em !important;
  transform: translateY(-0em) !important;
}
rt.M_M {
  --ruby-font-size: 0.5em;
  margin-top: -4.00em !important;
  transform: translateY(-0.0em) !important;
}
rt.L_L {
  --ruby-font-size: 0.6em;
  margin-top: -3.55em !important;
  transform: translateY(-0.0em) !important;
}
rt.XL_L {
  --ruby-font-size: 0.7em;
  margin-top: -3.20em !important;
  transform: translateY(-0.0em) !important;
}
rt.XXL_L {
  --ruby-font-size: 0.8em;
  margin-top: -2.80em !important;
  transform: translateY(-0.0em) !important;
}
</style>
</head>
<body>
<p class="text-M_M">
"""
        ruby_style_tail = "</p></body></html>"
    elif format_type in ('HTML格式','HTML格式_汉字替换'):
        ruby_style_head = """<style>
ruby rt {
    color: blue;
}
</style>
"""
        ruby_style_tail = "<br>"
    else:
        ruby_style_head = ""
        ruby_style_tail = ""
    
    return ruby_style_head + processed_text + ruby_style_tail
