import markdown
from django import template
from django.utils.safestring import mark_safe
from djblets.markdown import markdown_unescape


register = template.Library()


@register.filter
def markdown_email_html(text, is_rich_text):
    if not is_rich_text:
        return text

    return mark_safe(markdown.markdown(
        text,
        output_format='html',
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
