import re

from django import template
from django.template.loader import render_to_string

from reviewboard.reviews.templatetags.reviewtags import humanize_list
from djblets.util.decorators import blocktag


register = template.Library()


class QuotedEmail(template.Node):
    def __init__(self, template_name):
        self.template_name = template_name

    def render(self, context):
        return quote_text(render_to_string(self.template_name, context))


@register.tag
def quoted_email(parser, token):
    try:
        tag_name, template_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires a template name"

    return QuotedEmail(template_name)


@register.tag
@blocktag
def condense(context, nodelist):
    text = nodelist.render(context).strip()
    text = re.sub("\n{4,}", "\n\n\n", text)
    return text


@register.simple_tag
def reviewer_list(review_request):
    return humanize_list([group.display_name or group.name \
                          for group in review_request.target_groups.all()] + \
                         [user.get_full_name() or user.username \
                          for user in review_request.target_people.all()])


@register.filter
def quote_text(text, level = 1):
    lines = text.split("\n")
    quoted = ""

    for line in lines:
        quoted += "%s%s\n" % ("> " * level, line)

    return quoted.rstrip()
