from __future__ import unicode_literals

import re
from xml.dom.minidom import parseString

from django.utils import six
from django.utils.six.moves import cStringIO as StringIO
from markdown import Markdown, markdown, markdownFromFile


# NOTE: Any changes made here or in markdown_escape below should be
#       reflected in reviewboard/static/rb/js/utils/textUtils.js.

MARKDOWN_SPECIAL_CHARS = re.escape(r''.join(Markdown.ESCAPED_CHARS))
MARKDOWN_SPECIAL_CHARS_RE = re.compile(r'([%s])' % MARKDOWN_SPECIAL_CHARS)

# Markdown.ESCAPED_CHARS lists several characters to escape, but it's not
# that simple. We only want to escape certain things if they'll actually affect
# the markdown rendering, because otherwise it's annoying to look at the
# source.
MARKDOWN_ESCAPED_CHARS = set(Markdown.ESCAPED_CHARS)
MARKDOWN_ESCAPED_CHARS -= set(['.', '#', '-', '+', '_', '(', ')', '*'])

ESCAPE_CHARS_RE = re.compile(r"""
    (
    # Numeric lists start with leading whitespace, one or more digits,
    # and then a period
      ^\s*(\d+\.)+

    # ATX-style headers start with a hash at the beginning of the line.
    | ^\s*(\#)+

    # + and - have special meaning (lists, headers, and rules), but only if
    # they're at the start of the line.
    | ^\s*[-\+]+

    # _ indicates italic, and __ indicates bold, but not when in the middle
    # of a word.
    #
    # Ideally, we'd go ahead and prevent escaping there, but marked.js doesn't
    # handle this very well. For now, we have to escape it no matter where
    # it is. Until that's fixed, we can't use these rules:
    #
    #    | (?<!\w|_)(__?)
    #    | (__?)(?!\w|_)
    #
    # but must instead use this:
    | _

    # This is an alternate format for italic and bold, using * instead of _.
    | (?<!\w|\*)(\*\*?)
    | (\*\*?)(?!\w|\*)

    # Named links are in the form of [name](url).
    | (\[) [^\]]* (\]) (\() [^\)]* (\))

    # All other special characters
    | [%s]
    )
    """ % re.escape(''.join(MARKDOWN_ESCAPED_CHARS)),
    re.M | re.VERBOSE)
UNESCAPE_CHARS_RE = re.compile(r'\\([%s])' % MARKDOWN_SPECIAL_CHARS)

# Keyword arguments used when calling a Markdown renderer function.
MARKDOWN_KWARGS = {
    'safe_mode': 'escape',
    'output_format': 'xhtml1',
    'extensions': [
        'fenced_code', 'codehilite', 'sane_lists', 'smart_strong'
    ],
}


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


def iter_markdown_lines(markdown_html):
    """Iterates over lines of Markdown, normalizing for individual display.

    Generated Markdown HTML cannot by itself be handled on a per-line-basis.
    Code blocks, for example, will consist of multiple lines of content
    contained within a <pre> tag. Likewise, lists will be a bunch of
    <li> tags inside a <ul> tag, and individually do not form valid lists.

    This function iterates through the Markdown tree and generates
    self-contained lines of HTML that can be rendered individually.
    """
    nodes = get_markdown_element_tree(markdown_html)

    for node in nodes:
        if node.nodeType == node.ELEMENT_NODE:
            if (node.tagName == 'div' and
                node.attributes.get('class', 'codehilite')):
                # This is a code block, which will consist of a bunch of lines
                # for the source code. We want to split that up into
                # individual lines with their own <pre> tags.
                for line in node.toxml().splitlines():
                    yield '<pre>%s</pre>' % line
            elif node.tagName in ('ul', 'ol'):
                # This is a list. We'll need to split all of its items
                # into individual lists, in order to retain bullet points
                # or the numbers.
                #
                # For the case of numbers, we can set each list to start
                # at the appropriate number so that they don't all say "1."
                i = node.attributes.get('start', 1)

                for child_node in node.childNodes:
                    if (child_node.nodeType == child_node.ELEMENT_NODE and
                        child_node.tagName == 'li'):
                        # This is a list item element. It may be multiple
                        # lines, but we'll have to treat it as one line.
                        yield '<%s start="%s">%s</%s>' % (
                            node.tagName, i, child_node.toxml(),
                            node.tagName)

                        i += 1
            elif node.tagName == 'p':
                # This is a paragraph, possibly containing multiple lines.
                for line in node.toxml().splitlines():
                    yield line
            else:
                # Whatever this is, treat it as one block.
                yield node.toxml()
        elif node.nodeType == node.TEXT_NODE:
            # This may be several blank extraneous blank lines, due to
            # Markdown's generation from invisible markup like fences.
            # We want to condense this down to one blank line.
            yield '\n'


def get_markdown_element_tree(markdown_html):
    """Returns an XML element tree for Markdown-generated HTML.

    This will build the tree and return all nodes representing the rendered
    Markdown content.
    """
    if isinstance(markdown_html, six.text_type):
        markdown_html = markdown_html.encode('utf-8')

    doc = parseString(b'<html>%s</html>' % markdown_html)
    return doc.childNodes[0].childNodes


def render_markdown(text):
    """Renders Markdown text to HTML.

    The Markdown text will be sanitized to prevent injecting custom HTML.
    It will also enable a few plugins for code highlighting and sane lists.
    """
    return markdown(text, **MARKDOWN_KWARGS)


def render_markdown_from_file(f):
    """Renders Markdown text to HTML.

    The Markdown text will be sanitized to prevent injecting custom HTML.
    It will also enable a few plugins for code highlighting and sane lists.
    """
    s = StringIO()
    markdownFromFile(input=f, output=s, **MARKDOWN_KWARGS)
    html = s.getvalue()
    s.close()

    return html
