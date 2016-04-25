from __future__ import unicode_literals

from django import template


register = template.Library()


@register.assignment_tag()
def changedesc_user(changedesc, model):
    return changedesc.get_user(model)
