from __future__ import unicode_literals

import warnings

import pymdownx.emoji
from bleach.sanitizer import Cleaner
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from django.utils.encoding import force_text
from django.utils.html import escape
from djblets import markdown as djblets_markdown
from djblets.siteconfig.models import SiteConfiguration
from markdown import markdown


# Keyword arguments used when calling a Markdown renderer function.
#
# We use XHTML1 instead of HTML5 to ensure the results can be parsed by an
# XML parser, needed for change descriptions and other parts of the web UI.
MARKDOWN_KWARGS = {
    'enable_attributes': False,
    'output_format': 'xhtml1',
    'lazy_ol': False,
    'extensions': [
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'pymdownx.tilde',
        'pymdownx.emoji',
        'djblets.markdown.extensions.escape_html',
        'djblets.markdown.extensions.wysiwyg',
    ],
    'extension_configs': {
        'markdown.extensions.codehilite': {
            'guess_lang': False,
        },
        'pymdownx.emoji': {
            'emoji_index': pymdownx.emoji.gemoji,
            'options': {
                'classes': 'emoji',
                'image_path': ('https://github.githubassets.com/images/icons/'
                               'emoji/unicode/'),
                'non_standard_image_path': ('https://github.githubassets.com/'
                                            'images/icons/emoji/'),
            },
        },
    },
}


#: A list of HTML tags considered to be safe in Markdown-generated output.
#:
#: Anything not in this list will be escaped when sanitizing the resulting
#: HTML.
#:
#: Version Added:
#:     3.0.22
SAFE_MARKDOWN_TAGS = [
    'a',
    'b',
    'blockquote',
    'br',
    'code',
    'dd',
    'del',
    'div',
    'dt',
    'em',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'hr',
    'i',
    'img',
    'li',
    'ol',
    'p',
    'pre',
    'span',
    'strong',
    'sub',
    'sup',
    'table',
    'tbody',
    'td',
    'foot',
    'th',
    'thead',
    'tr',
    'tt',
    'ul',
]


#: Mappings of HTML tags to attributes considered to be safe for Markdown.
#:
#: Anything not in this list will be removed ehen sanitizing the resulting
#: HTML.
#:
#: Version Added:
#:     3.0.22
SAFE_MARKDOWN_ATTRS = {
    '*': ['class', 'id'],
    'a': ['href', 'alt', 'title'],
    'img': ['src', 'alt', 'title'],
}


def markdown_escape_field(obj, field_name):
    """Escapes Markdown text in a model or dictionary's field.

    This is a convenience around markdown_escape to escape the contents of
    a particular field in a model or dictionary.
    """
    if isinstance(obj, Model):
        setattr(obj, field_name,
                djblets_markdown.markdown_escape(getattr(obj, field_name)))
    elif isinstance(obj, dict):
        obj[field_name] = djblets_markdown.markdown_escape(obj[field_name])
    else:
        raise TypeError('Unexpected type %r passed to markdown_escape_field'
                        % obj)


def markdown_unescape_field(obj, field_name):
    """Unescapes Markdown text in a model or dictionary's field.

    This is a convenience around markdown_unescape to unescape the contents of
    a particular field in a model or dictionary.
    """
    if isinstance(obj, Model):
        setattr(obj, field_name,
                djblets_markdown.markdown_unescape(getattr(obj, field_name)))
    elif isinstance(obj, dict):
        obj[field_name] = djblets_markdown.markdown_unescape(obj[field_name])
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
        text = djblets_markdown.markdown_escape(text)

    if escape_html:
        text = escape(text)

    return text


def markdown_render_conditional(text, rich_text):
    """Return the escaped HTML content based on the rich_text flag."""
    if rich_text:
        return render_markdown(text)
    else:
        return escape(text)


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


def render_markdown(text):
    """Render Markdown text to XHTML.

    The Markdown text will be sanitized to prevent injecting custom HTML
    or dangerous links. It will also enable a few plugins for code
    highlighting and sane lists.

    It's rendered to XHTML in order to allow the element tree to be easily
    parsed for code review and change description diffing.

    Args:
        text (bytes or unicode):
            The Markdown text to render.

            If this is a byte string, it must represent UTF-8-encoded text.

    Returns:
        unicode:
        The Markdown-rendered XHTML.
    """
    html = markdown(force_text(text), **MARKDOWN_KWARGS)

    # Create a bleach HTML cleaner, and override settings on the html5lib
    # serializer it contains to ensure we use self-closing HTML tags, like
    # <br/>. This is needed so that we can parse the resulting HTML in
    # Djblets for things like Markdown diffing.
    cleaner = Cleaner(tags=SAFE_MARKDOWN_TAGS,
                      attributes=SAFE_MARKDOWN_ATTRS)
    cleaner.serializer.use_trailing_solidus = True

    return cleaner.clean(html)


def render_markdown_from_file(f):
    """Renders Markdown text to HTML.

    The Markdown text will be sanitized to prevent injecting custom HTML.
    It will also enable a few plugins for code highlighting and sane lists.
    """
    return djblets_markdown.render_markdown_from_file(f, **MARKDOWN_KWARGS)
