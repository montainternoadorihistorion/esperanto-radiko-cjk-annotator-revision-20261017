"""Read original text from this project's complete, standard ruby HTML exports.

This is extraction, not dictionary-based reverse conversion. The caller must
choose which side contains the source. Unedited bundled exports may record it;
old, edited and custom exports still need the caller's explicit choice.
No HTML is executed, and recovered characters are never parsed a second time.
"""

from html import unescape
from html.parser import HTMLParser
import re


MAX_HTML_BYTES = 10 * 1024 * 1024


class HtmlRecoveryError(ValueError):
    """The input is not a supported, structurally complete standard export."""


class HtmlRubyModeError(HtmlRecoveryError):
    """An explicit format record is invalid or conflicts with the user's choice."""

    def __init__(self, reason, recorded_mode=None):
        self.reason = reason
        self.recorded_mode = recorded_mode
        messages = {
            "invalid": "The recorded ruby mode must be kanji or annotation.",
            "duplicate": "Duplicate or conflicting ruby-mode metadata is not supported.",
            "mismatch": "The selected ruby mode does not match the recorded ruby mode.",
        }
        super().__init__(messages[reason])


def decode_html_upload(data: bytes) -> str:
    """Decode an exported UTF-8 file, allowing a UTF-8 BOM, without replacement."""
    if not isinstance(data, bytes):
        raise HtmlRecoveryError("HTML upload must contain bytes.")
    if len(data) > MAX_HTML_BYTES:
        raise HtmlRecoveryError("The HTML source must be at most 10 MiB.")
    try:
        return data.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise HtmlRecoveryError("The HTML file must be valid UTF-8.") from exc


class _StandardExportParser(HTMLParser):
    def __init__(self, mode: str):
        super().__init__(convert_charrefs=False)
        self.mode = mode
        self.stack = []
        self.seen = set()
        self.doctype = False
        self.parts = []
        self.ruby_count = 0
        self.ruby = None
        self.wrapper_lf = False
        self.after_body_br = False
        self.assignment_edition = "unknown"
        self.metadata_seen = False
        self.recorded_ruby_mode = None

    def fail(self, message):
        raise HtmlRecoveryError(message)

    def handle_decl(self, decl):
        if decl.lower() != "doctype html" or self.doctype or self.stack or "html" in self.seen:
            self.fail("A single HTML doctype is required before the document.")
        self.doctype = True

    def unknown_decl(self, data):
        self.fail("Unsupported HTML declaration.")

    def handle_pi(self, data):
        self.fail("Processing instructions are not supported.")

    def handle_comment(self, data):
        if self.stack or "html" in self.seen or self.metadata_seen:
            self.fail("Unexpected or duplicate HTML metadata/comment.")
        match = re.fullmatch(
            r"\s*assignment-edition:(current|legacy|custom_json)"
            r"\s+signature:[0-9a-fA-F]+\s+created-utc:\S+\s*", data
        )
        if not match:
            self.fail("Unsupported HTML metadata/comment.")
        self.assignment_edition = match.group(1)
        self.metadata_seen = True

    def _attrs(self, attrs, allowed):
        keys = [name for name, _ in attrs]
        if len(keys) != len(set(keys)) or any(name not in allowed for name in keys):
            self.fail("Unsupported or duplicate HTML attributes.")
        return dict(attrs)

    def _require_wrapper_lf(self):
        if self.wrapper_lf:
            self.fail("The standard paragraph opening newline is missing.")

    def handle_starttag(self, tag, attrs):
        parent = self.stack[-1] if self.stack else None
        if parent == "p":
            self._require_wrapper_lf()
            self.after_body_br = False
        if tag == "html":
            self._attrs(attrs, {"lang"})
            if parent or "html" in self.seen or not self.doctype:
                self.fail("A complete standard HTML document is required.")
        elif tag == "head":
            self._attrs(attrs, set())
            if parent != "html" or "head" in self.seen or "body" in self.seen:
                self.fail("Unexpected HTML head.")
        elif tag in ("title", "style"):
            self._attrs(attrs, set())
            if parent != "head" or tag in self.seen:
                self.fail("Unexpected or repeated head element.")
        elif tag == "meta":
            values = self._attrs(attrs, {"charset", "name", "content"})
            if parent != "head" or not values:
                self.fail("Unexpected metadata element.")
            if "charset" in values and (values["charset"] or "").lower() != "utf-8":
                self.fail("Only UTF-8 HTML is supported.")
            # Custom JSON may contain arbitrary or mixed ruby, irrespective of
            # its output-format selector. Keep its prior generic-meta behavior.
            if (self.assignment_edition != "custom_json"
                    and (values.get("name") or "").lower() == "esperanto-ruby-mode"):
                if self.recorded_ruby_mode is not None:
                    raise HtmlRubyModeError("duplicate")
                if set(values) != {"name", "content"} or values["content"] not in ("kanji", "annotation"):
                    raise HtmlRubyModeError("invalid")
                self.recorded_ruby_mode = values["content"]
            return
        elif tag == "body":
            self._attrs(attrs, set())
            if parent != "html" or "head" not in self.seen or "body" in self.seen:
                self.fail("Unexpected HTML body.")
        elif tag == "p":
            values = self._attrs(attrs, {"class"})
            if parent != "body" or "p" in self.seen or values != {"class": "text-M_M"}:
                self.fail("Exactly one standard p.text-M_M paragraph is required.")
            self.wrapper_lf = True
        elif tag == "ruby":
            self._attrs(attrs, set())
            if parent != "p" or self.ruby is not None:
                self.fail("Nested or misplaced ruby is not supported.")
            self.ruby = {"base": [], "rt": [], "has_rt": False}
        elif tag == "rt":
            self._attrs(attrs, {"class"})
            if parent != "ruby" or self.ruby is None or self.ruby["has_rt"]:
                self.fail("Each ruby must have exactly one reading.")
            self.ruby["has_rt"] = True
        elif tag == "br":
            self._attrs(attrs, set())
            if parent == "p":
                self.parts.append("\n")
                self.after_body_br = True
            elif parent != "rt":
                self.fail("Line breaks are supported only in the text or ruby reading.")
            return
        else:
            self.fail("Unsupported HTML element: " + tag)
        self.stack.append(tag)
        self.seen.add(tag)

    def handle_startendtag(self, tag, attrs):
        if tag not in ("meta", "br"):
            self.fail("Only meta and br may be self-closing.")
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.fail("HTML elements must close in the correct order.")
        if tag == "ruby":
            if (not self.ruby["has_rt"] or not "".join(self.ruby["base"]).strip()
                    or not "".join(self.ruby["rt"]).strip()):
                self.fail("Ruby needs both visible text and a nonempty reading.")
            self.parts.extend(self.ruby["rt" if self.mode == "kanji" else "base"])
            self.ruby_count += 1
            self.ruby = None
        elif tag == "p":
            self._require_wrapper_lf()
            self.after_body_br = False
        self.stack.pop()

    def _text(self, data, from_reference=False):
        if not data:
            return
        parent = self.stack[-1] if self.stack else None
        if parent in ("title", "style"):
            return
        if not from_reference and ("<" in data or "&" in data):
            self.fail("Incomplete or unescaped HTML markup.")
        # The forward renderer uses nbsp for consecutive ordinary spaces.
        data = data.replace("\u00a0", " ")
        if parent == "p":
            if self.wrapper_lf:
                if not data.startswith("\n"):
                    self.fail("The standard paragraph opening newline is missing.")
                data = data[1:]
                self.wrapper_lf = False
            if self.after_body_br:
                if data.startswith("\n"):
                    data = data[1:]
                self.after_body_br = False
            self.parts.append(data)
        elif parent in ("ruby", "rt"):
            if parent == "ruby" and self.ruby["has_rt"]:
                self.fail("Visible ruby text must precede its reading.")
            self.ruby["rt" if parent == "rt" else "base"].append(data)
        elif data.strip():
            self.fail("Text outside the standard paragraph is not supported.")

    def handle_data(self, data):
        self._text(data)

    def handle_entityref(self, name):
        value = unescape("&" + name + ";")
        if value == "&" + name + ";":
            self.fail("Unknown HTML character reference.")
        self._text(value, from_reference=True)

    def handle_charref(self, name):
        try:
            value = int(name[1:], 16) if name.lower().startswith("x") else int(name, 10)
        except ValueError as exc:
            raise HtmlRecoveryError("Invalid numeric character reference.") from exc
        if value == 0 or value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
            self.fail("Invalid Unicode character reference.")
        self._text(unescape("&#" + name + ";"), from_reference=True)

    def result(self):
        if self.stack or self.ruby is not None or not {"html", "head", "body", "p"} <= self.seen:
            self.fail("The standard HTML document is incomplete.")
        if self.recorded_ruby_mode is not None and self.recorded_ruby_mode != self.mode:
            raise HtmlRubyModeError("mismatch", self.recorded_ruby_mode)
        result = {"text": "".join(self.parts), "ruby_count": self.ruby_count,
                  "assignment_edition": self.assignment_edition, "mode": self.mode}
        if self.recorded_ruby_mode is not None:
            result["recorded_ruby_mode"] = self.recorded_ruby_mode
        return result


def recover_standard_html(source: str, ruby_mode: str) -> dict:
    """Extract preserved spelling; never infer direction or use an inverse table.

    ruby_mode is 'kanji' for Esperanto in rt, or 'annotation' for Esperanto in
    ruby's visible base. Assignment metadata is provenance, not authentication.
    An explicit non-custom format record must match the selected mode. Missing
    records and mixed/edited readings do not justify guessing a direction.
    """
    if ruby_mode not in ("kanji", "annotation"):
        raise HtmlRecoveryError("Select kanji or annotation ruby mode.")
    if not isinstance(source, str):
        raise HtmlRecoveryError("HTML source must be text.")
    # Reject oversized pasted text before allocating its encoded representation.
    if len(source) > MAX_HTML_BYTES:
        raise HtmlRecoveryError("The HTML source must be at most 10 MiB.")
    try:
        byte_length = len(source.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise HtmlRecoveryError("The HTML source must be valid Unicode text.") from exc
    if byte_length > MAX_HTML_BYTES:
        raise HtmlRecoveryError("The HTML source must be at most 10 MiB.")
    parser = _StandardExportParser(ruby_mode)
    source = source.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    try:
        parser.feed(source)
        parser.close()
    except HtmlRecoveryError:
        raise
    except (AssertionError, ValueError) as exc:
        raise HtmlRecoveryError("The HTML document is malformed.") from exc
    return parser.result()
