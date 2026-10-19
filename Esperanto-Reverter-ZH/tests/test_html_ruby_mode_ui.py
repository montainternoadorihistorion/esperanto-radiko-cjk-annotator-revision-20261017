"""A conflicting format record clears only the result, not the user's input."""
from unittest.mock import patch
import pytest
from streamlit.testing.v1 import AppTest
from test_html_recovery_ui import app, fixture, convert, save_available, upload_file, EXPECTED
from test_html_ruby_mode_metadata import with_mode


@pytest.mark.parametrize('edition', ['current', 'legacy'])
@pytest.mark.parametrize('direction', ['kanji', 'annotation'])
def test_wrong_recorded_mode_keeps_paste_and_plain_edition_but_blocks_stale_save(edition, direction):
    at = AppTest.from_file(app.__file__, default_timeout=30).run()
    at.sidebar.selectbox[0].set_value(app.LEGACY_INVERSE_SOURCE_ID).run()
    at.radio(key='reverter_input_mode').set_value('html').run()
    convert(at, fixture(direction, edition), direction)
    assert save_available(at)
    source = with_mode(fixture(direction, edition), direction)
    other = 'annotation' if direction == 'kanji' else 'kanji'
    at.radio(key='html_recovery_direction').set_value(other).run()
    at.text_area(key='html_recovery_paste').set_value(source)
    at.button(key='html_recovery_submit').click().run()
    assert not at.exception and at.error
    assert at.text_area(key='html_recovery_paste').value == source
    assert at.radio(key='html_recovery_direction').value == other
    assert not save_available(at) and not at.get('download_button')
    assert 'html_recovery_result' not in at.session_state
    at.radio(key='html_recovery_direction').set_value(direction).run()
    assert not save_available(at)
    at.button(key='html_recovery_submit').click().run()
    assert at.session_state['html_recovery_result']['text'] == EXPECTED
    assert at.session_state['html_recovery_result']['recorded_ruby_mode'] == direction
    at.radio(key='reverter_input_mode').set_value('plain').run()
    assert at.sidebar.selectbox[0].value == app.LEGACY_INVERSE_SOURCE_ID
    at.radio(key='reverter_input_mode').set_value('html').run()
    assert at.text_area(key='html_recovery_paste').value == source
    assert not save_available(at)


def test_wrong_recorded_mode_keeps_uploaded_file_for_explicit_retry():
    at = AppTest.from_file(app.__file__, default_timeout=30).run()
    at.radio(key='reverter_input_mode').set_value('html').run()
    at.radio(key='html_recovery_source_kind').set_value('upload').run()
    source = with_mode(fixture('annotation', 'legacy'), 'annotation')
    with patch.object(app.st, 'file_uploader', return_value=upload_file(source.encode('utf8'))):
        at.run()
        at.button(key='html_recovery_submit').click().run()
    assert not at.exception and at.error and not save_available(at)
    assert at.session_state['saved_html_recovery_file']['source'] == source
    at.radio(key='html_recovery_direction').set_value('annotation').run()
    at.button(key='html_recovery_submit').click().run()
    assert not at.exception
    assert at.session_state['html_recovery_result']['text'] == EXPECTED
    assert save_available(at)


@pytest.mark.parametrize('modes', [('unknown',), ('',), ('kanji', 'annotation')])
def test_invalid_record_explains_failure_without_old_result_or_lost_input(modes):
    at = AppTest.from_file(app.__file__, default_timeout=30).run()
    at.radio(key='reverter_input_mode').set_value('html').run()
    convert(at, fixture())
    source = fixture()
    for mode in modes:
        source = with_mode(source, mode)
    at.text_area(key='html_recovery_paste').set_value(source)
    at.button(key='html_recovery_submit').click().run()
    assert not at.exception and at.error
    assert at.text_area(key='html_recovery_paste').value == source
    assert not save_available(at) and not at.get('download_button')
