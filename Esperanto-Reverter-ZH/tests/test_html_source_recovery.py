"""Original spellings come from HTML, without consulting inverse dictionaries."""

from pathlib import Path

import pytest

from html_source_recovery import (
    MAX_HTML_BYTES, HtmlRecoveryError, decode_html_upload, recover_standard_html,
)


FIXTURES = Path(__file__).parent / "fixtures" / "html_source_recovery"
EXPECTED = ("dekdu etilo magneto sene\n"
            "semajno 再见 @literala@ <b>&amp;</b>\n"
            "Ĉapelo ĉapelo ĉapelo  fino\nFino\n")


def document(content, edition=None):
    metadata = ("<!-- assignment-edition:" + edition
                + " signature:abcdef created-utc:2026-10-18T12:00:00Z -->\n"
                if edition else "")
    return (metadata + '<!DOCTYPE html>\n<html lang="ja"><head>'
            '<meta charset="UTF-8"><title>Not the body</title>'
            '<style>body { color: red; }</style></head>\n'
            '<body>\n<p class="text-M_M">\n' + content + '</p></body></html>')


@pytest.mark.parametrize("language", ["JA", "ZH", "KO"])
@pytest.mark.parametrize("edition", ["current", "legacy"])
@pytest.mark.parametrize("mode,filename_mode", [("kanji", "kanji"), ("annotation", "ruby")])
def test_actual_standard_exports(language, edition, mode, filename_mode):
    source = decode_html_upload((FIXTURES / f"{language}_{edition}_{filename_mode}.html").read_bytes())
    result = recover_standard_html(source, mode)
    assert result["text"] == EXPECTED
    assert result["assignment_edition"] == edition
    assert result["mode"] == mode
    assert result["ruby_count"] == 11
    # The editable source panel omits download metadata.
    without_comment = source.split("\n", 1)[1]
    assert recover_standard_html(without_comment, mode) == {
        **result, "assignment_edition": "unknown",
    }


def test_layout_breaks_spaces_and_literal_characters_are_preserved():
    source = document('  <br>\n<br>\n<ruby>磁<rt>Mag<br>net</rt></ruby>o'
                      '&nbsp;&nbsp;再见 @literala@ &lt;b&gt;&amp;amp;&lt;/b&gt;'
                      '<br>\n \t  ')
    assert recover_standard_html(source, "kanji")["text"] == (
        '  \n\nMagneto  再见 @literala@ <b>&amp;</b>\n \t  ')


def test_original_leading_and_trailing_linefeeds_are_not_stripped():
    assert recover_standard_html(document('\nX\n'), "kanji")["text"] == '\nX\n'
    assert recover_standard_html(document('  '), "annotation")["text"] == '  '
    assert recover_standard_html(document(''), "kanji")["text"] == ''


def test_character_references_are_decoded_once_and_never_reparsed():
    source = document('&lt;script&gt;&amp;lt;&#x0041;&#65;&quot;&#39;&gt;')
    assert recover_standard_html(source, "kanji")["text"] == '<script>&lt;AA\"\'>'
    source = document('<ruby>X<rt>&amp;lt;b&amp;gt;</rt></ruby>')
    assert recover_standard_html(source, "kanji")["text"] == '&lt;b&gt;'


@pytest.mark.parametrize("edition", ["current", "legacy", "custom_json", None])
def test_edition_is_provenance_and_does_not_select_an_inverse_dictionary(edition):
    source = document('放 <ruby>放<rt>las</rt></ruby>is '
                      '<ruby>放ᴱ<rt>emancip</rt></ruby>o '
                      '<ruby>留<rt>las</rt></ruby>is', edition)
    result = recover_standard_html(source, "kanji")
    assert result == {"text": "放 lasis emancipo lasis",
                      "ruby_count": 3, "assignment_edition": edition or "unknown", "mode": "kanji"}


def test_identifiers_do_not_override_recorded_roots_or_decomposition():
    source = document('<ruby>丸ᵀ<rt>testik</rt></ruby><ruby>炎ᵀ<rt>it</rt></ruby>o '
                      '<ruby>丸ᴼ炎ᵀ<rt>orkidit</rt></ruby>a '
                      '<ruby>兰<rt>orkid</rt></ruby><ruby>炎ᵀ<rt>it</rt></ruby>a')
    assert recover_standard_html(source, "kanji")["text"] == 'testikito orkidita orkidita'


def test_explicit_direction_is_not_guessed_from_character_types():
    source = document('<ruby>vindoz<rt>Windows</rt></ruby>o')
    assert recover_standard_html(source, "annotation")["text"] == 'vindozo'
    # Existing exports cannot prove a choice is wrong. This is a documented limit.
    assert recover_standard_html(source, "kanji")["text"] == 'Windowso'


@pytest.mark.parametrize("content", [
    '<ruby>放</ruby>', '<ruby>放<rt></rt></ruby>', '<ruby><rt>las</rt></ruby>',
    '<ruby>放<rt> </rt></ruby>', '<ruby> <rt>las</rt></ruby>',
    '<ruby>放<rt>las</rt><rt>emancip</rt></ruby>',
    '<ruby>放<rt>las</ruby></rt>', '<ruby>放<rt>las</rt>tail</ruby>',
    '<ruby>放<ruby>留<rt>las</rt></ruby><rt>las</rt></ruby>',
    '<rt>las</rt>', '<ruby>放<br><rt>las</rt></ruby>',
    '<span>text</span>', '<script>alert(1)</script>', '<img src="x">',
    '<p>another paragraph</p>', '<ruby style="color:red">放<rt>las</rt></ruby>',
    '<ruby>放<rt class="X" class="Y">las</rt></ruby>', '<br onclick="x">',
    '&unknownentity;', '<broken', 'A&B', '&#0;', '&#xD800;', '&#x110000;',
])
def test_unsupported_or_malformed_body_fails(content):
    with pytest.raises(HtmlRecoveryError):
        recover_standard_html(document(content), "kanji")


@pytest.mark.parametrize("source", [
    '<ruby>放<rt>las</rt></ruby>is',
    document('X').replace('<!DOCTYPE html>', ''),
    document('X').replace('class="text-M_M"', 'class="other"'),
    document('X').replace('<p class="text-M_M">\n', '<p class="text-M_M">'),
    document('X').replace('</p>', ''),
    document('X').replace('</body>', ''),
    document('X').replace('</html>', ''),
    document('X').replace('</body>', '<p class="text-M_M">\nY</p></body>'),
    document('X').replace('</head>', '<script>x</script></head>'),
    document('X').replace('<meta charset="UTF-8">', '<meta charset="Shift_JIS">'),
    document('X') + document('Y'), document('X') + 'extra',
    document('X', 'invalid'),
    document('X', 'current').replace('<!DOCTYPE html>', '<!-- comment --><!DOCTYPE html>'),
    document('X').replace('<html lang="ja">', '<html lang="ja" onload="x">'),
])
def test_incomplete_or_nonstandard_document_fails(source):
    with pytest.raises(HtmlRecoveryError):
        recover_standard_html(source, "kanji")


def test_upload_decoding_is_strict_and_supports_bom():
    source = document('<ruby>放<rt>Ĉu</rt></ruby>')
    assert decode_html_upload(source.encode('utf-8')) == source
    assert decode_html_upload(source.encode('utf-8-sig')) == source
    assert recover_standard_html('\ufeff' + source, 'kanji')["text"] == 'Ĉu'
    assert recover_standard_html(source.replace('\n', '\r\n'), 'kanji')["text"] == 'Ĉu'
    for bad in (b'\xff', b'\xc3', source.encode('utf-16'), 'not bytes'):
        with pytest.raises(HtmlRecoveryError):
            decode_html_upload(bad)


@pytest.mark.parametrize("mode", ["auto", "ruby", "", None])
def test_no_implicit_mode_selection(mode):
    with pytest.raises(HtmlRecoveryError):
        recover_standard_html(document('X'), mode)


def test_exact_size_limit_is_accepted_for_upload_and_paste():
    overhead = len(document('').encode('utf-8'))
    source = document('X' * (MAX_HTML_BYTES - overhead))
    data = source.encode('utf-8')
    assert len(data) == MAX_HTML_BYTES
    assert decode_html_upload(data) == source
    assert len(recover_standard_html(source, 'kanji')['text']) == MAX_HTML_BYTES - overhead


def test_exact_multibyte_limit_is_accepted():
    remaining = MAX_HTML_BYTES - len(document('').encode('utf-8'))
    payload = 'Ĉ' * (remaining // 2) + 'X' * (remaining % 2)
    source = document(payload)
    assert len(source) < MAX_HTML_BYTES
    assert len(source.encode('utf-8')) == MAX_HTML_BYTES
    assert recover_standard_html(source, 'kanji')['text'] == payload


@pytest.mark.parametrize('byte', [b'X', b'\xff'], ids=['ascii', 'invalid-utf8'])
def test_oversized_upload_is_rejected_before_decoding(byte):
    data = byte * (MAX_HTML_BYTES + 1)
    with pytest.raises(HtmlRecoveryError, match='10 MiB'):
        decode_html_upload(data)


@pytest.mark.parametrize('char,count', [('X', MAX_HTML_BYTES + 1), ('Ĉ', MAX_HTML_BYTES // 2 + 1)],
                         ids=['ascii', 'multibyte'])
def test_oversized_paste_is_rejected_by_utf8_size(char, count):
    source = char * count
    with pytest.raises(HtmlRecoveryError, match='10 MiB'):
        recover_standard_html(source, 'kanji')


def test_surrogates_raise_the_same_public_error_type():
    with pytest.raises(HtmlRecoveryError, match='Unicode'):
        recover_standard_html(document('\ud800'), 'kanji')
