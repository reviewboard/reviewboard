from __future__ import unicode_literals

import logging

from django import template
from django.utils.html import mark_safe
from djblets.util.decorators import basictag

from reviewboard.avatars import avatar_services


register = template.Library()


@register.tag()
@basictag(takes_context=True)
def avatar(context, user, size, service_id=None):
    """Render the user's avatar to HTML.

    When the ``service_id`` argument is not provided, or the specified service
    is not registered or is not enabled, the default avatar service will be
    used for rendering instead.

    Args:
        context (django.template.Context):
            The template rendering context.

        user (django.contrib.auth.models.User):
            The user whose avatar is to be rendered.

        size (int):
            The height and width of the avatar, in pixels.

        service_id (unicode, optional):
            The unique identifier of the avatar service to use. If this is
            omitted, or the specified service is not registered and enabled,
            the default avatar service will be used.

    Returns:
        django.utils.safestring.SafeText:
        The user's avatar rendered to HTML, or an empty string if no avatar
        service could be found.
    """
    if (service_id is not None and
        avatar_services.has_service(service_id) and
        avatar_services.is_enabled(service_id)):
        service = avatar_services.get('id', service_id)
    else:
        service = avatar_services.default_service

    if service is None:
        logging.error('Could not get a suitable avatar service for user %s.',
                      user)
        return mark_safe('')

    return service.render(request=context['request'], user=user, size=size)
