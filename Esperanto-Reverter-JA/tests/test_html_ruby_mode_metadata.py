"""Recorded direction guards new bundled exports without guessing old/custom HTML."""
import pytest
from html_source_recovery import HtmlRubyModeError, recover_standard_html
from test_html_source_recovery import document, FIXTURES, EXPECTED


def with_mode(source, mode):
    return source.replace('</head>', f'<meta name="esperanto-ruby-mode" content="{mode}"></head>', 1)


@pytest.mark.parametrize('language', ['JA', 'ZH', 'KO'])
@pytest.mark.parametrize('edition', ['current', 'legacy'])
@pytest.mark.parametrize('mode,file_mode', [('kanji', 'kanji'), ('annotation', 'ruby')])
def test_recorded_standard_exports_keep_spelling_layout_and_protected_characters(language, edition, mode, file_mode):
    old = (FIXTURES / f'{language}_{edition}_{file_mode}.html').read_text(encoding='utf8')
    source = with_mode(old, mode)
    result = recover_standard_html(source, mode)
    assert result['text'] == EXPECTED
    assert result['assignment_edition'] == edition
    assert result['recorded_ruby_mode'] == mode
    assert result == {**recover_standard_html(old, mode), 'recorded_ruby_mode': mode}
    other = 'annotation' if mode == 'kanji' else 'kanji'
    with pytest.raises(HtmlRubyModeError) as failure:
        recover_standard_html(source, other)
    assert failure.value.reason == 'mismatch'
    assert failure.value.recorded_mode == mode


@pytest.mark.parametrize('meta', [
    '<meta name="esperanto-ruby-mode">',
    '<meta name="esperanto-ruby-mode" content>',
    '<meta name="esperanto-ruby-mode" content="">',
    '<meta name="esperanto-ruby-mode" content="unknown">',
    '<meta name="esperanto-ruby-mode" content="KANJI">',
    '<meta name="esperanto-ruby-mode" content="kanji" charset="UTF-8">',
])
def test_invalid_dedicated_mode_is_reported(meta):
    source = document('X').replace('</head>', meta+'</head>')
    with pytest.raises(HtmlRubyModeError) as failure:
        recover_standard_html(source, 'kanji')
    assert failure.value.reason == 'invalid'


@pytest.mark.parametrize('second', ['kanji', 'annotation'])
def test_duplicate_and_conflicting_mode_are_reported(second):
    source = with_mode(with_mode(document('X'), 'kanji'), second)
    with pytest.raises(HtmlRubyModeError) as failure:
        recover_standard_html(source, 'kanji')
    assert failure.value.reason == 'duplicate'


def test_generic_meta_and_comment_contract_stay_compatible():
    old = document('<ruby>放<rt>las</rt></ruby>is')
    source = old.replace('</head>', '<meta name="viewport" content="width=device-width"><meta name="arbitrary" content="annotation"></head>')
    assert recover_standard_html(source, 'kanji') == recover_standard_html(old, 'kanji')
    # The leading edition comment is optional; an explicit head record is still usable.
    assert recover_standard_html(with_mode(source, 'kanji'), 'kanji')['assignment_edition'] == 'unknown'


@pytest.mark.parametrize('meta_modes', [('kanji',), ('unknown',), ('',), ('kanji', 'annotation')])
def test_custom_json_keeps_existing_explicit_direction_and_generic_meta_behavior(meta_modes):
    old = document('<ruby>放<rt>las</rt></ruby>is <ruby>semajn<rt>週</rt></ruby>o', 'custom_json')
    source = old
    for mode in meta_modes:
        source = with_mode(source, mode)
    for direction in ('kanji', 'annotation'):
        assert recover_standard_html(source, direction) == recover_standard_html(old, direction)
    assert recover_standard_html(source, 'kanji')['text'] == 'lasis 週o'
    assert recover_standard_html(source, 'annotation')['text'] == '放is semajno'
