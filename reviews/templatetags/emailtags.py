from django import template
from django.template import TemplateSyntaxError
from django.template.loader import render_to_string

from reviewboard.reviews.templatetags.reviewtags import humanize_list


register = template.Library()


class QuotedEmail(template.Node):
    def __init__(self, template_name):
        self.template_name = template_name

    def render(self, context):
        lines = render_to_string(self.template_name, context).split("\n")
        email = ""

        for line in lines:
            email += "> %s\n" % line

        return email


@register.tag
def quoted_email(parser, token):
    try:
        tag_name, template_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires a template name"

    return QuotedEmail(template_name)


@register.simple_tag
def reviewer_list(review_request):
    names  = [group.name    for group in review_request.target_groups.all()]
    names += [user.username for user  in review_request.target_people.all()]
    return humanize_list(names)
