from __future__ import unicode_literals

import re

from markdown import Markdown


# NOTE: Any changes made here or in markdown_escape below should be
#       reflected in reviewboard/static/rb/js/utils/textUtils.js.

MARKDOWN_SPECIAL_CHARS = re.escape(r''.join(Markdown.ESCAPED_CHARS))
MARKDOWN_SPECIAL_CHARS_RE = re.compile(r'([%s])' % MARKDOWN_SPECIAL_CHARS)

# Markdown.ESCAPED_CHARS lists several characters to escape, but it's not
# that simple. We only want to escape certain things if they'll actually affect
# the markdown rendering, because otherwise it's annoying to look at the
# source.
MARKDOWN_ESCAPED_CHARS = set(Markdown.ESCAPED_CHARS)
MARKDOWN_ESCAPED_CHARS -= set(['.', '#', '-', '+'])

ESCAPE_CHARS_RE = re.compile(r"""
    (
      ^\s*(\d+\.)+    # Numeric lists start with leading whitespace, one or
                      # more digits, and then a period

    | ^\s*(\#)+       # ATX-style headers start with a hash at the beginning of
                      # the line.

    | ^\s*[-\+]+      # + and - have special meaning (lists, headers, and rules),
                      # but only if they're at the start of the line.

    | [%s]            # All other special characters
    )
    """ % re.escape(''.join(MARKDOWN_ESCAPED_CHARS)),
    re.M | re.VERBOSE)
UNESCAPE_CHARS_RE = re.compile(r'\\([%s])' % MARKDOWN_SPECIAL_CHARS)


def markdown_escape(text):
    """Escapes text for use in Markdown.

    This will escape the provided text so that none of the characters will
    be rendered specially by Markdown.
    """
    return ESCAPE_CHARS_RE.sub(
        lambda m: MARKDOWN_SPECIAL_CHARS_RE.sub(r'\\\1', m.group(0)),
        text)


def markdown_unescape(escaped_text):
    """Unescapes Markdown-escaped text.

    This will unescape the provided Markdown-formatted text so that any
    escaped characters will be unescaped.
    """
    return UNESCAPE_CHARS_RE.sub(r'\1', escaped_text)


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
