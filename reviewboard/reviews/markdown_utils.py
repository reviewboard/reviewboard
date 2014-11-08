from __future__ import unicode_literals

import re
from xml.dom.minidom import parseString

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from django.utils import six
from django.utils.html import escape
from django.utils.six.moves import cStringIO as StringIO
from djblets.siteconfig.models import SiteConfiguration
from markdown import Markdown, markdown, markdownFromFile


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
    | (?<!\w|_)(__?)
    | (__?)(?!\w|_)

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
    'extension_configs': {
        'codehilite': {
            'guess_lang': False,
        },
    },
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
    text = UNESCAPE_CHARS_RE.sub(r'\1', escaped_text)

    split = text.split('\n')
    for i, line in enumerate(split):
        if line.startswith('&nbsp;   '):
            split[i] = ' ' + line[6:]
        elif line.startswith('&nbsp;\t'):
            split[i] = line[6:]

    return '\n'.join(split)


def markdown_escape_field(obj, field_name):
    """Escapes Markdown text in a model or dictionary's field.

    This is a convenience around markdown_escape to escape the contents of
    a particular field in a model or dictionary.
    """
    if isinstance(obj, Model):
        setattr(obj, field_name, markdown_escape(getattr(obj, field_name)))
    elif isinstance(obj, dict):
        obj[field_name] = markdown_escape(obj[field_name])
    else:
        raise TypeError('Unexpected type %r passed to markdown_escape_field'
                        % obj)


def markdown_unescape_field(obj, field_name):
    """Unescapes Markdown text in a model or dictionary's field.

    This is a convenience around markdown_unescape to unescape the contents of
    a particular field in a model or dictionary.
    """
    if isinstance(obj, Model):
        setattr(obj, field_name, markdown_unescape(getattr(obj, field_name)))
    elif isinstance(obj, dict):
        obj[field_name] = markdown_unescape(obj[field_name])
    else:
        raise TypeError('Unexpected type %r passed to markdown_unescape_field'
                        % obj)


def normalize_text_for_edit(user, text, rich_text, escape_html=True):
    """Normalizes text, converting it for editing.

    This will normalize text for editing based on the rich_text flag and
    the user settings.

    If the text is not in Markdown and the user edits in Markdown by default,
    this will return the text escaped for edit. Otherwise, the text is
    returned as-is.
    """
    if text is None:
        return ''

    if not rich_text and is_rich_text_default_for_user(user):
        # This isn't rich text, but it's going to be edited as rich text,
        # so escape it.
        text = markdown_escape(text)

    if escape_html:
        text = escape(text)

    return text


def is_rich_text_default_for_user(user):
    """Returns whether the user edits in Markdown by default."""
    if user.is_authenticated():
        try:
            return user.get_profile().should_use_rich_text
        except ObjectDoesNotExist:
            pass

    siteconfig = SiteConfiguration.objects.get_current()

    return siteconfig.get('default_use_rich_text')


def markdown_set_field_escaped(obj, field, escaped):
    """Escapes or unescapes the specified field in a model or dictionary."""
    if escaped:
        markdown_escape_field(obj, field)
    else:
        markdown_unescape_field(obj, field)


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
