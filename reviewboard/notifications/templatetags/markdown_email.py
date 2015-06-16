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

    marked = markdown.markdown(
        text,
        extensions=[
            'fenced_code', 'codehilite(noclasses=True)', 'tables',
            'djblets.markdown.extensions.wysiwyg_email',
        ],
        output_format='xhtml1',
        safe_mode='escape')

    return mark_safe(marked)


@register.filter
def markdown_email_text(text, is_rich_text):
    if not is_rich_text:
        return text

    return markdown_unescape(text)
