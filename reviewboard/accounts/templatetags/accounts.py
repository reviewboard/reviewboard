"""Account-related template tags."""

from __future__ import unicode_literals

from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def user_profile_display_name(context, user):
    """Render the user's display name.

    Args:
        context (django.template.context.Context):
            The template rendering context.

        user (django.contrib.auth.models.User):
            The user whose display name is to be rendered.

    Returns:
        unicode:
        The user's display name.
    """
    request = context['request']

    return user.get_profile().get_display_name(request.user)
