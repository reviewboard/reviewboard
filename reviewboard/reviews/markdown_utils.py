import re

from markdown import Markdown


ESCAPED_CHARS_RE = \
    re.compile(r'([%s])' % re.escape(''.join(Markdown.ESCAPED_CHARS)))
UNESCAPED_CHARS_RE = \
    re.compile(r'\\([%s])' % re.escape(''.join(Markdown.ESCAPED_CHARS)))


def markdown_escape(text):
    """Escapes text for use in Markdown.

    This will escape the provided text so that none of the characters will
    be rendered specially by Markdown.
    """
    return ESCAPED_CHARS_RE.sub(r'\\\1', text)


def markdown_unescape(escaped_text):
    """Unescapes Markdown-escaped text.

    This will unescape the provided Markdown-formatted text so that any
    escaped characters will be unescaped.
    """
    return UNESCAPED_CHARS_RE.sub(r'\1', escaped_text)


def markdown_escape_field(model, field_name):
    """Escapes Markdown text in a model's field.

    This is a convenience around markdown_escape to escape the contents of
    a particular field in a model.
    """
    setattr(model, field_name, markdown_escape(getattr(model, field_name)))


def markdown_unescape_field(model, field_name):
    """Unescapes Markdown text in a model's field.

    This is a convenience around markdown_unescape to unescape the contents of
    a particular field in a model.
    """
    setattr(model, field_name, markdown_unescape(getattr(model, field_name)))


def markdown_set_field_escaped(model, field, escaped):
    """Escapes or unescapes the specified field in a model."""
    if escaped:
        markdown_escape_field(model, field)
    else:
        markdown_unescape_field(model, field)
