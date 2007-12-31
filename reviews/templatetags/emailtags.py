import re

from django import template
from django.template.loader import render_to_string
from djblets.util.decorators import basictag, blocktag

from reviewboard.reviews.templatetags.reviewtags import humanize_list


register = template.Library()


@register.tag
@basictag(takes_context=True)
def quoted_email(context, template_name):
    """
    Renders a specified template as a quoted reply, using the current context.
    """
    return quote_text(render_to_string(template_name, context))


@register.tag
@blocktag
def condense(context, nodelist):
    """
    Condenses a block of text so that there are never more than three
    consecutive newlines.
    """
    text = nodelist.render(context).strip()
    text = re.sub("\n{4,}", "\n\n\n", text)
    return text


@register.filter
def quote_text(text, level=1):
    """
    Quotes a block of text the specified number of times.
    """
    lines = text.split("\n")
    quoted = ""

    for line in lines:
        quoted += "%s%s\n" % ("> " * level, line)

    return quoted.rstrip()
