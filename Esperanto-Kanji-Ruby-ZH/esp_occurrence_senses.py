"""Select a reviewed alternative meaning for an occurrence in the original input."""
from pathlib import Path
import hashlib
import json
import re

_ENDINGS = ('', 'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'en')
_SENSE_ROOTS = {'nefrit.mineral': 'nefrit', 'ake.achaean': 'ake'}
_FORM_SENSES = {
    form: sense for sense, root in _SENSE_ROOTS.items()
    for ending in _ENDINGS for word in (root + ending,)
    for form in (word, word.capitalize(), word.upper())
}
# Forms of the originally supported mineral sense.
_FORMS = frozenset(form for form, sense in _FORM_SENSES.items() if sense == 'nefrit.mineral')
_PATTERN = re.compile(r'(?<![\w\^])(?:' + '|'.join(sorted(_FORM_SENSES, key=len, reverse=True)) + r')(?![\w\^])')


def normalize_source(text):
    from esp_text_replacement_module import unify_halfwidth_spaces, convert_to_circumflex
    return convert_to_circumflex(unify_halfwidth_spaces(text)).replace('\x01', '').replace('\r\n', '\n').replace('\r', '\n')


def source_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def find_occurrences(text):
    from esp_text_replacement_module import PERCENT_PATTERN, _EMAIL_PATTERN
    text = normalize_source(text)
    excluded = [(m.start(), m.end()) for pattern in (PERCENT_PATTERN, _EMAIL_PATTERN)
                for m in pattern.finditer(text)]
    return [dict(start=m.start(), end=m.end(), source=m.group())
            for m in _PATTERN.finditer(text)
            if not any(m.start() < end and m.end() > start for start, end in excluded)]


def load_sense(data_dir, key='nefrit.mineral'):
    data = json.loads((Path(data_dir) / 'explicit_occurrence_senses.json').read_text(encoding='utf-8-sig'))
    found = [row for row in data['senses'] if row['sense_key'] == key]
    if len(found) != 1 or found[0]['root'] != _SENSE_ROOTS.get(key):
        raise ValueError(f'Invalid occurrence sense: {key}')
    row = found[0]
    if key == 'nefrit.mineral' and (row['edition'] != 'current' or not row['display']):
        raise ValueError('Invalid mineral sense definition')
    if key == 'ake.achaean' and (row['edition'] != 'both' or row['display'] is not None):
        raise ValueError('Invalid Achaean sense definition')
    return row


def render_selections(text, selected, data_dir, format_type, *, edition, bundled):
    if not selected or edition not in ('current', 'legacy') or not bundled:
        return []
    import esp_overlay_module as overlay
    from esp_assignment_edition import language
    source = normalize_source(text)
    candidates = find_occurrences(source)
    if len(set(selected)) != len(selected) or any(type(i) is not int or not 0 <= i < len(candidates) for i in selected):
        raise ValueError('Invalid occurrence selection')
    widths = json.loads((Path(data_dir) / 'char_widths.json').read_text(encoding='utf-8'))
    helper = overlay._replacement_helper()
    result = []
    for index in sorted(selected):
        item = candidates[index]
        word = item['source']
        key = _FORM_SENSES[word]
        if edition == 'legacy' and key != 'ake.achaean':
            continue
        sense = load_sense(data_dir, key)
        length = len(sense['root'])
        root, ending = word[:length], word[length:]
        annotation = sense['annotations'][language(data_dir)]
        if sense['display'] is None and format_type in (overlay.KANJI_FMT, '替换后文字列のみ(仅)保留(简单替换)'):
            rendered = word
        elif format_type == '替换后文字列のみ(仅)保留(简单替换)':
            rendered = sense['display'] + ending
        elif format_type in (overlay.KANJI_FMT, overlay.RUBY_FMT):
            meaning = sense['display'] if format_type == overlay.KANJI_FMT else annotation
            rendered = helper.output_format(root, meaning, format_type, widths) + ending
        else:
            raise ValueError('Explicit senses require a bundled output format')
        result.append({**item, 'source_sha256': source_digest(source), 'sense_key': sense['sense_key'], 'rendered': rendered})
    return result


def capture_explicit_occurrences(text, selections, percent_pattern, tokens, escape):
    """Capture original offsets together with percent spans, before @ matching."""
    percent = list(percent_pattern.finditer(text))
    candidates = {(i['start'], i['end'], i['source']) for i in find_occurrences(text)}
    events = [(m.start(), m.end(), escape(text[m.start(1):m.end(1)])) for m in percent]
    digest = source_digest(text)
    for item in selections:
        if (item['source_sha256'] != digest or item['sense_key'] != _FORM_SENSES.get(item['source'])
                or (item['start'], item['end'], item['source']) not in candidates):
            raise ValueError('Source changed after sense selection')
        events.append((item['start'], item['end'], item['rendered']))
    pieces, captured, cursor = [], [], 0
    for start, end, rendered in sorted(events):
        if start < cursor:
            raise ValueError('Overlapping protected or selected occurrences')
        token = next(tokens)
        pieces.extend((text[cursor:start], token))
        captured.append((token, rendered))
        cursor = end
    pieces.append(text[cursor:])
    return ''.join(pieces), captured


_TEXT = {
    'JA': ('同じ綴りの語義を選ぶ：nefrit', '鉱物の「軟玉」として読む箇所',
           '選んだ箇所だけを「软玉ᴺ」にします。未選択の箇所は従来の処理を保ちます。%で保護した箇所は対象外です。',
           '原文を編集すると選択を解除します。逆変換すると原綴り nefrit に戻り、語義の選択は残りません。再変換時には再度選んでください。'),
    'ZH': ('选择同形词的含义：nefrit', '选择表示矿物「软玉」的位置',
           '只有所选位置使用「软玉ᴺ」。未选择的位置保持原有处理；%保护的文字不在候选中。',
           '修改原文后清除选择。逆转换恢复原拼写 nefrit，不保留词义选择；再次转换时请重新选择。'),
    'KO': ('같은 철자의 뜻 선택: nefrit', '광물인 연옥을 뜻하는 위치',
           '선택한 위치만 「软玉ᴺ」으로 변환합니다. 선택하지 않은 위치는 기존 처리를 유지하며 %로 보호한 부분은 제외합니다.',
           '원문을 수정하면 선택이 해제됩니다. 역변환은 원래 철자 nefrit를 복원하며 뜻 선택은 보존하지 않습니다. 다시 변환할 때 선택해 주세요.'),
}


_AKE_TEXT = {
    'JA': ('ake の動物義・民族義を選ぶ', '民族名「アカイア人」として読む箇所', '通常はナマケモノとして読みます。民族名として選ぶと、その箇所は原綴りを保ち、注釈ルビで「アカイア人」と表示します。'),
    'ZH': ('选择 ake 的动物义或族名义', '选择表示亚该亚人的位置', '默认按树懒解读。所选位置保留原拼写，在注释模式显示“亚该亚人”。'),
    'KO': ('ake의 동물 이름과 민족 이름 구분', '아카이아인을 뜻하는 위치', '기본값은 나무늘보입니다. 민족 이름으로 선택한 위치는 원래 철자를 유지하고 주석 모드에서 아카이아인으로 표시합니다.'),
}


def select_occurrences(text, data_dir, edition, bundled, format_type):
    import streamlit as st
    from esp_assignment_edition import language
    normalized = normalize_source(text)
    candidates = find_occurrences(normalized)
    lang = language(data_dir)
    raw_hash = source_digest(text)
    result = []
    for sense, labels, prefix in (
        ('nefrit.mineral', _TEXT[lang], '_nefrit_sense'),
        ('ake.achaean', _AKE_TEXT[lang], '_ake_sense'),
    ):
        state_key, widget_key = prefix + '_choice', prefix + '_widget'
        state = st.session_state.get(state_key, {})
        if state.get('source_sha256') != raw_hash:
            state = {'source_sha256': raw_hash, 'selected': []}
            st.session_state[state_key] = state
            st.session_state.pop(widget_key, None)
        if not bundled or (edition != 'current' and sense == 'nefrit.mineral'):
            continue
        indices = [i for i, item in enumerate(candidates) if _FORM_SENSES[item['source']] == sense]
        if not indices:
            continue
        # Keep widget selections local to the sense, including sessions opened before Ake was added.
        def label(local_index, indices=indices):
            item = candidates[indices[local_index]]
            start, end = item['start'], item['end']
            context = normalized[max(0, start-24):start] + '【' + item['source'] + '】' + normalized[end:end+24]
            return f'{local_index+1}: ' + context.replace('\n', ' ↵ ')
        with st.expander(labels[0]):
            st.caption(labels[2])
            if widget_key not in st.session_state:
                st.session_state[widget_key] = list(state['selected'])
            selected = st.multiselect(labels[1], range(len(indices)), format_func=label, key=widget_key)
            state['selected'] = list(selected)
            st.session_state[state_key] = state
            if len(labels) > 3:
                st.caption(labels[3])
        result.extend(indices[i] for i in selected)
    result.sort()
    return render_selections(text, result, data_dir, format_type, edition=edition, bundled=bundled), result
