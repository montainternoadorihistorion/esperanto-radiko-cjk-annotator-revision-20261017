## esp_text_replacement_module.py(3つ目)

"""
このモジュールは「エスペラント文章の文字列(漢字)置換」を包括的に扱うツール集です。
主な機能：
1. エスペラント独自の文字形式（ĉ, ĝなど）への変換 → convert_to_circumflex
2. 特殊な半角スペースの統一（ASCIIスペースに） → unify_halfwidth_spaces
3. (現在不要になった) HTMLルビ付与関数 → wrap_text_with_ruby (コメントのみ)
4. %や@で囲まれたテキストのスキップ・局所変換 → (create_replacements_list_for_...)
5. 大域的なプレースホルダー置換 → safe_replace
6. それらをまとめて実行する複合置換関数 → orchestrate_comprehensive_esperanto_text_replacement
7. multiprocessing を用いた行単位の並列実行 → parallel_process / process_segment
"""

import re
import json
from typing import List, Tuple, Dict
import multiprocessing

# ================================
# 1) エスペラント文字変換用の辞書
# ================================
# それぞれ (x表記 → ĉ) や (ĉ → c^)など、様々なマッピングを辞書にしている
x_to_circumflex = {
    'cx': 'ĉ', 'gx': 'ĝ', 'hx': 'ĥ', 'jx': 'ĵ', 'sx': 'ŝ', 'ux': 'ŭ',
    'Cx': 'Ĉ', 'Gx': 'Ĝ', 'Hx': 'Ĥ', 'Jx': 'Ĵ', 'Sx': 'Ŝ', 'Ux': 'Ŭ'
}
circumflex_to_x = {
    'ĉ': 'cx', 'ĝ': 'gx', 'ĥ': 'hx', 'ĵ': 'jx', 'ŝ': 'sx', 'ŭ': 'ux',
    'Ĉ': 'Cx', 'Ĝ': 'Gx', 'Ĥ': 'Hx', 'Ĵ': 'Jx', 'Ŝ': 'Sx', 'Ŭ': 'Ux'
}
x_to_hat = {
    'cx': 'c^', 'gx': 'g^', 'hx': 'h^', 'jx': 'j^', 'sx': 's^', 'ux': 'u^',
    'Cx': 'C^', 'Gx': 'G^', 'Hx': 'H^', 'Jx': 'J^', 'Sx': 'S^', 'Ux': 'U^'
}
hat_to_x = {
    'c^': 'cx', 'g^': 'gx', 'h^': 'hx', 'j^': 'jx', 's^': 'sx', 'u^': 'ux',
    'C^': 'Cx', 'G^': 'Gx', 'H^': 'Hx', 'J^': 'Jx', 'S^': 'Sx', 'U^': 'Ux'
}
hat_to_circumflex = {
    'c^': 'ĉ', 'g^': 'ĝ', 'h^': 'ĥ', 'j^': 'ĵ', 's^': 'ŝ', 'u^': 'ŭ',
    'C^': 'Ĉ', 'G^': 'Ĝ', 'H^': 'Ĥ', 'J^': 'Ĵ', 'S^': 'Ŝ', 'U^': 'Ŭ'
}
circumflex_to_hat = {
    'ĉ': 'c^', 'ĝ': 'g^', 'ĥ': 'h^', 'ĵ': 'j^', 'ŝ': 's^', 'ŭ': 'u^',
    'Ĉ': 'C^', 'Ĝ': 'G^', 'Ĥ': 'H^', 'Ĵ': 'J^', 'Ŝ': 'S^', 'Ŭ': 'U^'
}

# ================================
# 2) 基本の文字形式変換関数
# ================================
def replace_esperanto_chars(text, char_dict: Dict[str, str]) -> str:
    # char_dict に含まれるペア (original_char, converted_char) ごとに
    # text.replace() していく
    for original_char, converted_char in char_dict.items():
        text = text.replace(original_char, converted_char)
    return text

def convert_to_circumflex(text: str) -> str:
    """
    テキストを字上符形式（ĉ, ĝ, ĥ, ĵ, ŝ, ŭなど）に統一します。
    1. hat_to_circumflex: c^ → ĉ
    2. x_to_circumflex: cx → ĉ
    """
    text = replace_esperanto_chars(text, hat_to_circumflex)
    text = replace_esperanto_chars(text, x_to_circumflex)
    return text

def unify_halfwidth_spaces(text: str) -> str:
    """
    全角スペース(U+3000)は変更せず、半角スペースと視覚的に区別がつきにくい空白文字を
    ASCII半角スペース(U+0020)に統一する。
    """
    pattern = r"[\u00A0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A]"
    return re.sub(pattern, " ", text)

# ================================
# 3) (HTMLルビタグの補助関数) 
#  (現状不要とされている)
# ================================

# ================================
# 4) 占位符(placeholder)関連
# ================================
def safe_replace(text: str, replacements: List[Tuple[str, str, str]]) -> str:
    """
    (old, new, placeholder) のリストを受け取り、
    text中の old → placeholder → new の段階置換を行う。
    """
    valid_replacements = {}

    # まず old→placeholder
    for old, new, placeholder in replacements:
        if old in text:
            text = text.replace(old, placeholder)
            valid_replacements[placeholder] = new

    # 次に placeholder→new
    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)

    return text

def import_placeholders(filename: str) -> List[str]:
    """
    プレースホルダを行単位で読み込むだけの関数
    """
    with open(filename, 'r') as file:
        placeholders = [line.strip() for line in file if line.strip()]
    return placeholders

# '%' で囲まれた箇所をスキップするための正規表現
PERCENT_PATTERN = re.compile(r'(?<![0-9])%(.{1,50}?)%')  # 50% 等、数字直後の%は開きマーカーにしない
def find_percent_enclosed_strings_for_skipping_replacement(text: str) -> List[str]:
    """'%foo%' の形を全て抽出。50文字以内に限定。"""
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
    '%xxx%' で囲まれた箇所を検出し、
    ( '%xxx%', placeholder ) という形で対応させるリストを作る
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


# These repairs are restricted to reviewed whole words and their ordinary
# endings. They do not change root tables, custom JSON, arbitrary compounds,
# or the conjunction 'ĉar'. All kanji/identifiers come from the selected data.
_REVIEWED_WORD_STEMS = {
    'anestez': ('anestez',),
    'ĉar': ('ĉaro',),
    'ĉaret': ('ĉareto',),
    'observad': ('observad',),
    'alventag': ('alven', 'tag'),
    'programaranĝ': ('program', 'aranĝ'),
    'otit': ('otit',),
}
_REVIEWED_WORD_FORMS = {
    form: (stem, ending, case)
    for stem in _REVIEWED_WORD_STEMS
    for ending in (('', 'o', 'oj', 'on', 'ojn', 'a', 'aj', 'an', 'ajn',
                    'e', 'en', 'i', 'as', 'is', 'os', 'us', 'u')
                   if stem == 'anestez' else ('o', 'oj', 'on', 'ojn'))
    for case, form in enumerate((stem + ending, (stem + ending).capitalize(),
                                 (stem + ending).upper()))
}
_REVIEWED_NORMAL_FORMS = frozenset(
    word for word, (stem, _, _) in _REVIEWED_WORD_FORMS.items()
    if stem in {'observad', 'alventag', 'programaranĝ'}
)
_REVIEWED_NORMAL_PATTERN = re.compile(
    r'(?<!\w)(' + '|'.join(sorted(map(re.escape, _REVIEWED_NORMAL_FORMS),
                                   key=len, reverse=True)) + r')(?!\w)'
)
_REVIEWED_CART_GLOSS = '수레'


def _reviewed_word_renderings(payloads, global_rules, enabled=False):
    wanted = set(payloads) & _REVIEWED_WORD_FORMS.keys() if enabled else set()
    if not wanted:
        return {}

    # merge_overlay gives explicit corrections their own $9NNNNNN$ tokens.
    # Preserve a user's exact-word decision before applying the bundled repair.
    overrides = {}
    for old, new, placeholder in global_rules:
        key = old.strip(' ')
        if key in wanted and re.fullmatch(r'\$9\d{6}\$', placeholder.strip(' ')):
            overrides.setdefault(key, new.strip(' '))
    wanted -= overrides.keys()
    if not wanted:
        return overrides

    def case_root(root, case, first):
        return root.upper() if case == 2 else root.capitalize() if case == 1 and first else root

    needed = {case_root(root, case, index == 0)
              for word in wanted
              for stem, _, case in (_REVIEWED_WORD_FORMS[word],)
              for index, root in enumerate(_REVIEWED_WORD_STEMS[stem])}
    atoms = {}
    # First matching rule is the same priority used by normal conversion.
    for old, new, _ in global_rules:
        key = old.strip(' ')
        if key in needed and key not in atoms:
            atoms[key] = new.strip(' ')
    missing = needed - atoms.keys()
    if missing:
        raise ValueError('Missing reviewed word atoms: ' + repr(sorted(missing)))

    results = dict(overrides)
    for word in wanted:
        stem, ending, case = _REVIEWED_WORD_FORMS[word]
        pieces = []
        for index, root in enumerate(_REVIEWED_WORD_STEMS[stem]):
            key = case_root(root, case, index == 0)
            piece = atoms[key]
            if root in {'ĉaro', 'ĉareto'}:
                noun_ending = 'O' if case == 2 else 'o'
                if not piece.endswith(noun_ending):
                    raise ValueError('Reviewed cart noun lacks its literal ending: ' + key)
                piece = piece[:-1]
                # Annotation mode has the Esperanto root as the ruby base.
                # Kanji ruby has the kanji base and is therefore left intact.
                piece = re.sub(
                    r'(<ruby\b[^>]*>\s*ĉar\s*<rt\b[^>]*>).*?(</rt\s*>)',
                    lambda match: match[1] + _REVIEWED_CART_GLOSS + match[2],
                    piece, flags=re.I | re.S,
                )
            pieces.append(piece)
        results[word] = ''.join(pieces) + (ending.upper() if case == 2 else ending)
    return results


# Reviewed corpus payloads only: keep normal segmentation and every root/ID
# table unchanged. Reuse selected-edition local atoms, never a new assignment.
# The last item of each tuple is a literal grammatical ending, not a root.
_REVIEWED_CORPUS_LOCAL_PARTS = {
    'metroj': ('metr', 'oj'),
    'metron': ('metr', 'on'),
    'metrojn': ('metr', 'ojn'),
    'teamanojn': ('team', 'an', 'ojn'),
    'tradukteamanojn': ('traduk', 'team', 'an', 'ojn'),
    'aperdato': ('aper', 'dat', 'o'),
    'aristokratino': ('aristokrat', 'in', 'o'),
    'koleginoj': ('koleg', 'in', 'oj'),
    'konilon': ('kon', 'il', 'on'),
    'vortuzon': ('vort', 'uz', 'on'),
    'ekstermovadaj': ('ekster', 'mov', 'ad', 'aj'),
    'Landaron': ('Land', 'ar', 'on'),
    'landaron': ('land', 'ar', 'on'),
    'dekstremuloj': ('dekstr', 'em', 'ul', 'oj'),
    'regularojn': ('regul', 'ar', 'ojn'),
    'skanaĵoj': ('skan', 'aĵ', 'oj'),
    'malfidinda': ('mal', 'fid', 'ind', 'a'),
    'Emociego': ('Emoci', 'eg', 'o'),
    'antaŭeko': ('antaŭ', 'ek', 'o'),
    'videbleco': ('vid', 'ebl', 'ec', 'o'),
    'uzeblas': ('uz', 'ebl', 'as', ''),
    'direktivoj': ('direkt', 'iv', 'oj'),
    'sendependa': ('sen', 'de', 'pend', 'a'),
    'romanigoj': ('roman', 'ig', 'oj'),
    'filozofion': ('filozofi', 'on'),
    'aŭskultoviziton': ('aŭskult', 'o', 'vizit', 'on'),
    'civilizon': ('civiliz', 'on'),
    'korelingvajn': ('kore', 'lingv', 'ajn'),
    'kronologion': ('kronologi', 'on'),
    'IJK-on': ('IJK', '-', 'on'),
    'burokratio': ('burokrat', 'io'),
    'programeroj': ('program', 'er', 'oj'),
    'ambaŭkaze': ('ambaŭ', 'kaz', 'e'),
    'radio-programeroj': ('radi', 'o-', 'program', 'er', 'oj'),
}
# Joining vowels and punctuation are literal here, as in the source word.
_REVIEWED_CORPUS_LITERALS = frozenset({'o', '-', 'o-'})
# These complete normal rules already preserve the established decomposition.
# In particular, their repaired tense annotation must not be read as ace.
_REVIEWED_CORPUS_GLOBAL_WORDS = frozenset({
    'organiziĝi', 'akvumi', 'dankegas', 'enestas', 'ricevindas',
    'sumiĝas', 'trametas', 'datumas', 'as-tempo',
    'aso', 'asoj', 'ason', 'asojn',
})
_REVIEWED_CORPUS_FORMS = frozenset(_REVIEWED_CORPUS_LOCAL_PARTS) | _REVIEWED_CORPUS_GLOBAL_WORDS


# This exact payload has two possible readings; this is a contextual gloss,
# not a new dictionary meaning or a changed kanji assignment for roman.
_REVIEWED_ROMAN_CONTEXT_RT = '<rt class="M_M">로마자;소설</rt>'


def _reviewed_corpus_renderings(payloads, local_rules, global_rules, enabled=False):
    wanted = set(payloads) & _REVIEWED_CORPUS_FORMS if enabled else set()
    if not wanted:
        return {}
    # User/session corrections have priority, including when no bundled atoms
    # are present. Never rewrite a supplied custom JSON by default.
    results = {}
    for old, new, placeholder in global_rules:
        key = old.strip(' ')
        if key in wanted and re.fullmatch(r'\$9\d{6}\$', placeholder.strip(' ')):
            results.setdefault(key, new.strip(' '))
    wanted -= results.keys()
    normal = wanted & _REVIEWED_CORPUS_GLOBAL_WORDS
    for old, new, _ in global_rules:
        key = old.strip(' ')
        if key in normal and key not in results:
            results[key] = new.strip(' ')
    # The ace noun has annotation-only whole-word entries and no kanji
    # assignment. Its four reviewed noun forms therefore stay Latin there.
    for word in (normal - results.keys()) & {'aso', 'asoj', 'ason', 'asojn'}:
        results[word] = word
    missing_normal = normal - results.keys()
    if missing_normal:
        raise ValueError('Missing reviewed corpus whole words: ' + repr(sorted(missing_normal)))
    local = wanted - normal
    needed = {piece for word in local for piece in _REVIEWED_CORPUS_LOCAL_PARTS[word][:-1]
              if piece not in _REVIEWED_CORPUS_LITERALS}
    atoms = {}
    for old, new, _ in local_rules:
        if old in needed:
            if not isinstance(new, str) or not new or (old in atoms and atoms[old] != new):
                raise ValueError('Conflicting or empty reviewed corpus atom: ' + old)
            atoms[old] = new
    # These reviewed pieces have annotation entries but no kanji allocation.
    # Preserve their original letters when the selected kanji table lacks them.
    for piece in needed & {'IJK', 'kore', 'as'}:
        atoms.setdefault(piece, piece)
    missing_atoms = needed - atoms.keys()
    if missing_atoms:
        raise ValueError('Missing reviewed corpus atoms: ' + repr(sorted(missing_atoms)))
    for word in local:
        parts = _REVIEWED_CORPUS_LOCAL_PARTS[word]
        results[word] = ''.join(piece if piece in _REVIEWED_CORPUS_LITERALS else atoms[piece]
                                for piece in parts[:-1]) + parts[-1]
        if word == 'romanigoj':
            results[word] = re.sub(
                r'(<ruby\b[^>]*>\s*roman\s*)<rt\b[^>]*>.*?</rt>',
                lambda match: match[1] + _REVIEWED_ROMAN_CONTEXT_RT,
                results[word], count=1, flags=re.I | re.S,
            )
    return results


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
    reviewed.update(_reviewed_word_renderings(payloads, global_rules, reviewed_local_decompositions))
    reviewed.update(_reviewed_corpus_renderings(payloads, local_rules, global_rules, reviewed_local_decompositions))

    def render_local(payload):
        return _render_localized_payload(payload, local_rules, finalized, reviewed, escape)

    text, localized = _capture_marker_spans(
        text, matches, _marker_tokens(local_tokens, '@', source, used), render_local,
    )
    normal_matches = list(_REVIEWED_NORMAL_PATTERN.finditer(text)) if reviewed_local_decompositions else []
    # Do not pre-empt a longer explicit correction (including a legacy phrase
    # entry) by capturing a reviewed word inside its input span.
    if normal_matches:
        for old, _, placeholder in global_rules:
            if old.strip(' ') and re.fullmatch(r'\$9\d{6}\$', placeholder.strip(' ')):
                for manual in re.finditer(re.escape(old.strip(' ')), text):
                    normal_matches = [match for match in normal_matches
                                      if match.end() <= manual.start() or match.start() >= manual.end()]
            if not normal_matches:
                break
    normal_renderings = _reviewed_word_renderings(
        [match.group(1) for match in normal_matches], global_rules, reviewed_local_decompositions
    )
    text, corrected = _capture_marker_spans(
        text, normal_matches, _marker_tokens([], '@', source, used), normal_renderings.__getitem__,
    )
    return escape(text), localized + corrected, skipped

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

def create_replacements_list_for_localized_replacement(text, placeholders: List[str],
                                                       replacements_list_for_localized_string: List[Tuple[str, str, str]],
                                                       replacements_final_list: List[Tuple[str, str, str]] = None, reviewed_local_decompositions: bool = False,
                                                       ) -> List[List[str]]:
    """
    '@xxx@' で囲まれた箇所を検出し、
    その内部文字列 'xxx' を replacements_list_for_localized_string で置換した結果を
    placeholder に置き換える。
    """
    matches = find_at_enclosed_strings_for_localized_replacement(text)
    finalized_global = _finalized_global_renderings_for_exact_matches(
        matches, replacements_final_list or []
    )
    reviewed = _reviewed_local_renderings(
        matches, replacements_list_for_localized_string, reviewed_local_decompositions
    )
    reviewed.update(_reviewed_word_renderings(
        matches, replacements_final_list or [], reviewed_local_decompositions
    ))
    reviewed.update(_reviewed_corpus_renderings(
        matches, replacements_list_for_localized_string, replacements_final_list or [],
        reviewed_local_decompositions
    ))
    tmp_list = []
    for i, match in enumerate(matches):
        if i < len(placeholders):
            replaced_match = _render_localized_payload(
                match, replacements_list_for_localized_string, finalized_global, reviewed, lambda value: value
            )
            tmp_list.append([f"@{match}@", placeholders[i], replaced_match])
        else:
            break
    return tmp_list

# ================================
# 5) メインの複合文字列(漢字)置換関数
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
    複数の変換ルールに従ってエスペラント文を文字列(漢字)置換するメイン関数。

    1) 空白の正規化 → 2) エスペラント文字(ĉ等)の字上符形式統一
    3) %で囲まれた部分をスキップ
    4) @で囲まれた部分を局所置換
    5) 大域置換
    6) 2文字語根の置換を最大12回
    7) プレースホルダ復元
    8) HTML形式が指定なら追加整形
    """
    # 1, 2) 空白の正規化 + エスペラント字上符への変換
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
    # ※%...%保護と@...@局所置換より後に実行(保護窓50字と@の入力位置を維持+約物入り局所規則のraw照合。
    #   プレースホルダ %1854%/@5134@ は % @ 数字が_KEEPに含まれるため壊れない)。
    # _KEEP: 英字26+字上符12 / ラテン拡張(ę,ś,ü等の外国名内部を境界化しない。CJKは境界のまま) /
    #   数字+%+@(プレースホルダ整合) / ASCII+U+2019アポストロフィ
    #   (詩的省略と定冠詞l'/l’を保護。右側・閉じ引用は個別処理) / 空白改行番兵。
    _BOL = chr(1)
    import re as _re
    _HAT12 = chr(264) + chr(265) + chr(284) + chr(285) + chr(292) + chr(293) + chr(308) + chr(309) + chr(348) + chr(349) + chr(364) + chr(365)
    _LATEXT = chr(192) + '-' + chr(214) + chr(216) + '-' + chr(246) + chr(248) + '-' + chr(591)
    _APOSTROPHES = chr(39) + chr(8217)
    _KEEP = 'A-Za-z0-9' + _HAT12 + _LATEXT + chr(37) + chr(64) + _APOSTROPHES + ' ' + chr(10) + chr(13) + chr(1)
    _PAD = _re.compile('([^' + _KEEP + '])')
    text = _PAD.sub(lambda _mo: ' ' + _BOL + _mo.group(1) + _BOL + ' ', text)
    # ASCIIアポストロフィの右側限定パディング(直後が文字): dank'al のal・'Mi 引用開きが発火
    _LTR = 'A-Za-z' + _HAT12 + _LATEXT
    _APOS_R = _re.compile('[' + _APOSTROPHES + '](?=[' + _LTR + '])')
    text = _APOS_R.sub(lambda _mo: _mo.group(0) + _BOL + ' ', text)
    # 閉じ引用 mi' 型: o省略形になり得ない2字語根に限り左側もパディング(du/en/veは対象外)
    _APOS_L = _re.compile('(?<![' + _LTR + '])((?:[Mm]i|[Vv]i|[Nn]i|[Ll]i|[' + chr(348) + chr(349) + ']i|[' + chr(284) + chr(285) + ']i|[Aa]l|[Dd]e|[Ee]l|[' + chr(264) + chr(265) + ']e|[' + chr(264) + chr(265) + ']u|[Ss]e|[Kk]e|[Jj]e|[Dd]a|[Nn]e|[Hh]o|[Oo]k))([' + _APOSTROPHES + '])(?![' + _LTR + '])')
    text = _APOS_L.sub(lambda _mo: _mo.group(1) + ' ' + _BOL + _mo.group(2), text)
    # 行頭(文頭・改行直後)の2字語根対応: 各行頭/行末に番兵付き仮想スペースを挿入
    text = _BOL + ' ' + text.replace(chr(10), ' ' + _BOL + chr(10) + _BOL + ' ') + ' ' + _BOL
    # 5) 大域置換 (old, new, placeholder)
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

    # 6) 2문자 어근 치환: 고정 2회 → "더 이상 매칭되지 않을 때까지 반복(fixpoint)"으로 일반화.
    #    고정 2회는 3개 이상 연속된 2문자 접사(예: san/ig/ej/et)를 놓쳐 가짜 어근을 만들었음.
    #    각 라운드는 "!" 개수로 유일화하며, round0=구 pass1, round1=구 pass2 와 완전 후방 호환.
    two_char_rounds = []
    _round = 0
    while _round < 12:  # 안전 상한(보통 2〜3 라운드로 수렴)
        _d = {}
        _mk = "!" * _round
        for old, new, placeholder in replacements_list_for_2char:
            if old in text:
                ph = (re.sub(r"(\$+)(?=\d)", lambda match: match[1] + _mk,
                             placeholder, count=1) if reviewed_local_decompositions
                      else _mk + placeholder + _mk)
                text = text.replace(old, ph)
                _d[ph] = new
        if not _d:
            break
        two_char_rounds.append(_d)
        _round += 1

    # 7) placeholder를 최종 문자열로 복원(뒤 라운드부터＝삽입 역순)
    for _d in reversed(two_char_rounds):
        for placeholder, new in reversed(_d.items()):
            text = text.replace(placeholder, new)

    for placeholder, new in valid_replacements.items():
        text = text.replace(placeholder, new)

    # 局所(@)・スキップ(%) の復元
    # Remove only the actual delimiters captured above, never literal markers
    # inside protected text or unrelated occurrences of the same payload.
    for token, rendered in localized_parts:
        text = text.replace(token, rendered)
    for token, original in intact_parts:
        text = text.replace(token, original)
    text = text.replace(' ' + _BOL, '').replace(_BOL + ' ', '').replace(_BOL, '')

    # 8) HTML形式であれば、改行を <br> に変換 + スペースを &nbsp; に置換
    if "HTML" in format_type:
        text = text.replace('&#38;', '&amp;').replace('&#60;', '&lt;').replace('&#62;', '&gt;')
        text = text.replace("\n", "<br>\n")
        # text = wrap_text_with_ruby(text, chunk_size=10) # (過去の関数/不要)
        text = re.sub(r"   ", "&nbsp;&nbsp;&nbsp;", text)  # 3つ以上の空白を変換
        text = re.sub(r"  ", "&nbsp;&nbsp;", text)  # 2つ以上の空白を変換

    return text

# ================================
# 6) multiprocessing 関連
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
    multiprocessing用の下請け関数。
    lines (文字列リスト) を結合してから orchestrate_comprehensive_esperanto_text_replacement を実行。
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
    与えられた text を行単位で分割し、process_segment を
    マルチプロセスで並列実行した結果を結合する。
    """
    if num_processes <= 1:
        # シングルコアで直接orchestrate_comprehensive_esperanto_text_replacementを呼ぶ
        return orchestrate_comprehensive_esperanto_text_replacement(
            text,
            placeholders_for_skipping_replacements,
            replacements_list_for_localized_string,
            placeholders_for_localized_replacement,
            replacements_final_list,
            replacements_list_for_2char,
            format_type, reviewed_local_decompositions=reviewed_local_decompositions
        )

    # 行ごとに分割 (改行込み)
    lines = re.findall(r'.*?\n|.+$', text)
    num_lines = len(lines)
    if num_lines <= 1:
        # 行数が1以下なら並列化しても意味ないのでシングルで
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
    # 最後のプロセスに残りを全部割り当てる
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
    指定された出力形式に応じて、processed_text に対するHTMLヘッダーとフッターを適用する。
    例: ルビサイズ調整用の<style> を挿入するなど。
    """
    if format_type in ('HTML格式_Ruby文字_大小调整','HTML格式_Ruby文字_大小调整_汉字替换'):
        # html形式におけるルビサイズの変更形式
        ruby_style_head="""<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>에스페란토 어근 분해 루비 주석 텍스트</title>
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
        font-size: 100%; /* 多くのブラウザは16px相当が標準 */
      }

      .text-M_M {
        font-size: 1rem!important; 
        font-family: Arial, sans-serif;
        line-height: 2.0 !important;  /* text-M_Mのline-heightとrubyのline-heightは一致させる必要がある。 */
        display: block; /* ブロック要素として扱う */
        position: relative;
      }
  
      /* ▼ ルビ（フレックスでルビを上に表示） */
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
  
      /* ▼ 追加マイナス余白（ルビサイズ別に上書き） */
      rt {
        display: block !important;
        font-size: var(--ruby-font-size);
        color: var(--ruby-color);
        line-height: 1.05;/*ルビを改行するケースにおけるルビの行間*/
        text-align: center;
        /* margin-top: 0.2em !important;   
        transform: translateY(0.4em) !important; */
      }
      rt.XXXS_S {
        --ruby-font-size: 0.3em;
        margin-top: -8.3em !important;/* ルビの高さ位置はここで調節する。 */
        transform: translateY(-0em) !important;
      }    
      rt.XXS_S {
        --ruby-font-size: 0.3em;
        margin-top: -7.2em !important;/* ルビの高さ位置はここで調節する。 */
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
