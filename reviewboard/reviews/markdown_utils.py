from __future__ import annotations

import logging
import re
from html import unescape
from typing import TYPE_CHECKING

import pymdownx.emoji
from bleach.sanitizer import Cleaner
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from django.utils.encoding import force_str
from django.utils.html import escape
from djblets import markdown as djblets_markdown
from djblets.siteconfig.models import SiteConfiguration
from markdown import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from reviewboard.reviews.markdown_lists import ListIndentExtension
from reviewboard.treesitter.core import get_parser
from reviewboard.treesitter.highlight import highlight as ts_highlight
from reviewboard.treesitter.language import get_language_name_for_info_string

if TYPE_CHECKING:
    from collections.abc import Sequence
    from xml.etree.ElementTree import Element

    from markdown import Markdown


logger = logging.getLogger(__name__)


class _AlertBlockquoteTreeprocessor(Treeprocessor):
    """Renders alerts as blockquotes.

    Version Added:
        9.0
    """

    def run(
        self,
        root: Element,
    ) -> None:
        """Change each alert's element to a blockquote.

        Args:
            root (xml.etree.ElementTree.Element):
                The root of the rendered tree.
        """
        for element in root.iter('div'):
            if 'admonition' in element.get('class', '').split():
                element.tag = 'blockquote'


class _AlertBlockquoteExtension(Extension):
    """Renders alerts as blockquotes instead of divs.

    Code that splits rendered Markdown into lines treats a top-level div as
    a code block. Alerts are blockquotes in the source, and this keeps them
    that way. Places that don't style alerts, such as some e-mail clients,
    still show a blockquote.

    Version Added:
        9.0
    """

    def extendMarkdown(  # noqa: N802
        self,
        md: Markdown,
    ) -> None:
        """Add the treeprocessor to the Markdown instance.

        Args:
            md (markdown.Markdown):
                The Markdown instance.
        """
        md.treeprocessors.register(_AlertBlockquoteTreeprocessor(md),
                                   'alert_blockquote', 0)


#: Keyword arguments used when calling a Markdown renderer function.
#:
#: We use XHTML instead of HTML5 to ensure the results can be parsed by an
#: XML parser, needed for doing diffs in change descriptions and the Markdown
#: review UI.
#:
#: Comments on Markdown file attachments store row numbers, and these
#: options decide how content is split into rows. A change that adds,
#: removes, merges, or splits blocks, or changes their text, will move those
#: comments. Bump MarkdownReviewUI.rendered_lines_version for any such
#: change, and keep a frozen copy of the old rendering in
#: :py:mod:`reviewboard.reviews.ui.legacy_markdown` so older comments can
#: be mapped.
MARKDOWN_KWARGS = {
    'enable_attributes': False,
    'output_format': 'xhtml',
    'lazy_ol': False,
    'extensions': [
        'markdown.extensions.sane_lists',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'pymdownx.tilde',
        'pymdownx.emoji',
        'djblets.markdown.extensions.escape_html',
        'djblets.markdown.extensions.wysiwyg',
        'pymdownx.highlight',
        'pymdownx.magiclink',
        'pymdownx.quotes',
        'pymdownx.superfences',
        'pymdownx.tasklist',
        ListIndentExtension(),
        _AlertBlockquoteExtension(),
    ],
    'extension_configs': {
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
        'pymdownx.highlight': {
            'use_pygments': False,
        },
        'pymdownx.quotes': {
            'callouts': True,
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
#: Anything not in this list will be removed when sanitizing the resulting
#: HTML.
#:
#: Version Added:
#:     3.0.22
SAFE_MARKDOWN_ATTRS = {
    '*': ['class', 'id'],
    'a': ['href', 'alt', 'title'],
    'img': ['src', 'alt', 'title'],
}


#: Regex to find code blocks in rendered Markdown.
#:
#: This also takes any line break just before the block. That comes from a
#: fence inside a list item, and would show as an extra blank line.
#:
#: Version Added:
#:     9.0
_CODE_BLOCK_RE = re.compile(
    r'(?:<br />\s*)?'
    r'<pre class="highlight"><code(?: class="language-(?P<lang>[^"]+)")?>'
    r'(?P<code>.*?)</code></pre>',
    re.S)

#: Regex to find task list checkboxes.
#:
#: Version Added:
#:     9.0
_TASK_CHECKBOX_RE = re.compile(
    r'<input type="checkbox" disabled(?P<checked> checked)?/>')


#: A list of protocols considered safe for URLs.
#:
#: This can be overridden by setting
#: ``settings.ALLOWED_MARKDOWN_URL_PROTOCOLS``.
#:
#: Version Added:
#:     3.0.24
SAFE_MARKDOWN_URL_PROTOCOLS = ['http', 'https', 'mailto']


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
    if user.is_authenticated:
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


def clean_markdown_html(html):
    """Return a cleaned, secure version of Markdown-rendered HTML/XHTML.

    This will sanitize Markdown-rendered HTML, ensuring that only a trusted
    list of HTML tags, attributes, and URI schemes are included in the
    HTML. Anything else will be left out or transformed into a safe
    representation of the original content.

    The result will always be in XHTML form, to allow for XML processing of the
    content.

    Version Added:
        3.0.24

    Args:
        html (unicode):
            The Markdown-rendered HTML to clean.

    Returns:
        unicode:
        A sanitizied XHTML representation of the Markdown-rendered HTML.
    """
    # Allow users to override the protocols. We're checking for this
    # dynamically, partly to ease unit testing, and partly to eventually
    # allow dynamic configuration.
    safe_url_protocols = SAFE_MARKDOWN_URL_PROTOCOLS
    custom_safe_url_protocols = settings.ALLOWED_MARKDOWN_URL_PROTOCOLS

    if custom_safe_url_protocols:
        safe_url_protocols = (set(safe_url_protocols) |
                              set(custom_safe_url_protocols))

    # Create a bleach HTML cleaner, and override settings on the html5lib
    # serializer it contains to ensure we use self-closing HTML tags, like
    # <br/>. This is needed so that we can parse the resulting HTML in
    # Djblets for things like Markdown diffing.
    cleaner = Cleaner(tags=SAFE_MARKDOWN_TAGS,
                      attributes=SAFE_MARKDOWN_ATTRS,
                      protocols=safe_url_protocols)
    cleaner.serializer.use_trailing_solidus = True

    return cleaner.clean(html)


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
    html = markdown(force_str(text), **MARKDOWN_KWARGS)
    html = _CODE_BLOCK_RE.sub(_replace_code_block, html)
    html = replace_task_checkboxes(html)

    return clean_markdown_html(html)


def render_markdown_from_file(f):
    """Render Markdown text from a file to XHTML.

    The Markdown text will be sanitized to prevent injecting custom HTML.
    It will also enable a few plugins for code highlighting and sane lists.

    Version Changed:
        3.0.24:
        This has been updated to sanitize the rendered HTML to avoid any
        security issues.

    Args:
        f (file):
            The file stream to read from.

    Returns:
        unicode:
        The Markdown-rendered XHTML.
    """
    return render_markdown(f.read())


def _replace_code_block(
    m: re.Match[str],
) -> str:
    """Return a highlighted code block.

    Code blocks are split into lines when diffing fields, so this uses
    the same layout as the ``codehilite`` extension. Each line of code is
    on its own line in the HTML.

    Version Added:
        9.0

    Args:
        m (re.Match):
            The match for the code block.

    Returns:
        str:
        The HTML for the code block.
    """
    code_html = m.group('code')
    code = unescape(code_html)
    lines = highlight_code_block(code, code.split('\n'), m.group('lang') or '')

    if lines is None:
        lines = code_html.split('\n')

    inner = '\n'.join(lines)

    return f'<div class="codehilite"><pre><code>{inner}\n</code></pre></div>'


def replace_task_checkboxes(
    html: str,
) -> str:
    """Replace task list checkboxes with characters.

    Checkboxes aren't allowed through the sanitizer, so they're shown as
    characters instead. This must be called before
    :py:func:`clean_markdown_html`. HTML typed in the text is escaped by
    then, so only checkboxes from task lists are replaced.

    Version Added:
        9.0

    Args:
        html (str):
            The rendered Markdown.

    Returns:
        str:
        The HTML with checkboxes replaced.
    """
    return _TASK_CHECKBOX_RE.sub(_replace_task_checkbox, html)


def _replace_task_checkbox(
    m: re.Match[str],
) -> str:
    """Return a character to show in place of a task's checkbox.

    Version Added:
        9.0

    Args:
        m (re.Match):
            The match for the checkbox.

    Returns:
        str:
        The HTML for the checkbox.
    """
    if m.group('checked'):
        return '<span class="task-list-checkbox -is-checked">\u2611</span>'
    else:
        return '<span class="task-list-checkbox">\u2610</span>'


def highlight_code_block(
    code: str,
    code_lines: Sequence[str],
    info_string: str,
) -> Sequence[str] | None:
    """Return syntax-highlighted lines for a code block.

    This uses tree-sitter when it supports the language, and Pygments
    otherwise.

    Version Added:
        9.0

    Args:
        code (str):
            The code to highlight.

        code_lines (list of str):
            The code, split into lines.

        info_string (str):
            The language named on the code fence. This may be empty.

    Returns:
        list of str:
        The highlighted lines, or ``None`` if the code can't be highlighted.
    """
    if not info_string:
        return None

    language_name = get_language_name_for_info_string(info_string)

    if language_name:
        content = code.encode()

        try:
            tree = get_parser(language_name).parse(content)
            lines = ts_highlight(content, code_lines, tree, language_name)

            if lines:
                return lines
        except Exception as e:
            logger.exception('Tree-sitter highlighting failed for a %s code '
                             'block in Markdown: %s',
                             language_name, e)

    try:
        lexer = get_lexer_by_name(info_string)
    except ClassNotFound:
        return None

    lines = highlight(code, lexer, HtmlFormatter(nowrap=True)).splitlines()

    if len(lines) != len(code_lines):
        # Line counts must match, or lines would be lost.
        return None

    return lines
