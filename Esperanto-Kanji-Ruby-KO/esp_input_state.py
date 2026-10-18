"""Keep input drafts across widget cleanup and bind saved results to their input."""

import hashlib
import json

import streamlit as st
import streamlit.components.v1 as components


def _remember(widget_key, keep_key):
    st.session_state[keep_key] = st.session_state[widget_key]


def persistent_radio(label, options, *, key):
    keep_key = key + "_keep"
    if key not in st.session_state:
        remembered = st.session_state.get(keep_key, options[0])
        st.session_state[key] = remembered if remembered in options else options[0]
    value = st.radio(label, options, key=key, on_change=_remember, args=(key, keep_key))
    st.session_state[keep_key] = value
    return value


def remember_text():
    _remember("text0_value", "_text0_keep")


def set_text(text):
    st.session_state["text0_value"] = text
    st.session_state["_text0_keep"] = text


def apply_text_upload(uploaded_file):
    """Decode before replacing the draft; an empty valid upload clears the draft."""
    raw = uploaded_file.getvalue()
    text = raw.decode("utf-8-sig", errors="strict")
    identity = hashlib.sha256(
        str(getattr(uploaded_file, "file_id", "")).encode("utf-8") + b"\0" + raw
    ).hexdigest()
    if st.session_state.get("_last_text_upload") != identity:
        set_text(text)
        st.session_state["_last_text_upload"] = identity
    return identity


def input_signature(text, source, upload_identity):
    payload = json.dumps([text, source, upload_identity], ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def remember_edited_text():
    _remember("edited_html", "_edited_html_keep")


def confirm_download(*, text, data, filename, is_html, edition_label, title,
                     content_label, download_label):
    """Offer an immutable download only while the editing page is blocked.

    A native download beside an editable input can start before that input's
    blur-triggered rerun. The ordinary confirmation button first synchronizes
    widget state; its caller verifies provenance before opening this dialog.
    Dismissing the dialog reruns the page and removes its download button.
    """
    @st.dialog(title, width="large", on_dismiss="rerun")
    def show_snapshot():
        st.caption(edition_label)
        st.caption(filename)
        if is_html:
            components.html(text, height=300, scrolling=True)
        else:
            st.text_area(content_label, value=text, height=300, disabled=True)
        st.download_button(
            download_label, data=data, file_name=filename,
            mime="text/html" if is_html else "text/plain",
            on_click="ignore", key="confirmed_result_download",
        )

    show_snapshot()
