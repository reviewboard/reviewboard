from __future__ import unicode_literals

import markdown
from django import template
from django.utils.safestring import mark_safe
from djblets.markdown import markdown_unescape


register = template.Library()


@register.filter
def markdown_email_html(text, is_rich_text):
    if not is_rich_text:
        return text

    # We use XHTML1 instead of HTML5 to ensure the results can be parsed by
    # an XML parser. This is actually needed for the main Markdown renderer
    # for the web UI, but consistency is good here.
    return mark_safe(markdown.markdown(
        text,
        output_format='xhtml1',
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.sane_lists',
            'pymdownx.tilde',
            'djblets.markdown.extensions.escape_html',
            'djblets.markdown.extensions.wysiwyg_email',
        ],
        extension_configs={
            'codehilite': {
                'noclasses': True,
            },
        }))


@register.filter
def markdown_email_text(text, is_rich_text):
    if not is_rich_text:
        return text

    return markdown_unescape(text)
