from __future__ import unicode_literals

import json
import logging

from django import template
from django.utils import six
from django.utils.html import mark_safe

from reviewboard.avatars import avatar_services


register = template.Library()


@register.simple_tag(takes_context=True)
def avatar(context, user, size, service_id=None):
    """Render the user's avatar to HTML.

    When the ``service_id`` argument is not provided, or the specified service
    is not registered or is not enabled, the user's specified avatar service
    will be used for rendering instead.

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
    service = avatar_services.for_user(user, service_id)

    if service is None:
        logging.error('Could not get a suitable avatar service for user %s.',
                      user)
        return mark_safe('')

    return service.render(request=context['request'], user=user, size=size)


@register.simple_tag(takes_context=True)
def avatar_url(context, user, size, resolution='1x', service_id=None):
    """Return the URL of the requested avatar.

    Args:
        context (django.template.Context):
            The template rendering context.

        user (django.contrib.auth.models.User):
            The user whose avatar is to be rendered.

        size (int):
            The height and width of the avatar, in pixels.

        resolution (unicode, optional):
            The resolution of the avatar. This should be one of ``'1x'``, for
            normal DPI, or ``'2x'``, for high DPI. This defaults to normal DPI.

        service_id (unicode, optional):
            The unique identifier of the avatar service to use. If this is
            omitted, or the specified service is not registered and enabled,
            the default avatar service will be used.

    Returns:
        django.utils.safestring.SafeText:
        The URL of the requested avatar, or an empty string if no avatar
        service could be found.
    """
    if resolution not in ('1x', '2x'):
        raise ValueError('resolution should be "1x" or "2x", not %r.'
                         % resolution)

    service = avatar_services.for_user(user, service_id)

    if service is None:
        logging.error('Could not get a suitable avatar service for user %s.',
                      user)
        return mark_safe('')

    urls = service.get_avatar_urls(request=context['request'],
                                   user=user,
                                   size=size)
    return urls[resolution]


@register.simple_tag(takes_context=True)
def avatar_urls(context, user, size, service_id=None):
    """Serialize the user's avatar URLs into a JavaScript object.

    Args:
        context (django.template.Context):
            The template rendering context.

        user (django.contrib.auth.models.User):
            The user whose avatar URLs are to be serialized.

        size (int):
            The height and width of the avatar, in pixels.

        service_id (unicode, optional):
            The unique identifier of the avatar service to use. If this is
            omitted, or the specified service is not registered and enabled,
            the default avatar service will be used.

    Returns:
        django.utils.safestring.SafeText:
        The rendered JavaScript object.
    """
    service = avatar_services.for_user(user, service_id)

    if service is None:
        logging.error('Could not get a suitable avatar service for user %s.',
                      user)
        urls = {}
    else:
        urls = {
            resolution: url
            for resolution, url in six.iteritems(
                service.get_avatar_urls(request=context['request'],
                                        user=user,
                                        size=size)
            )
        }

    return mark_safe(json.dumps(urls, sort_keys=True))
