"""Utility methods for read-only mode."""

from __future__ import unicode_literals

from djblets.siteconfig.models import SiteConfiguration


def is_site_read_only_for(user):
    """Check whether user should be affected by read-only mode.

    Superusers are not affected by read-only mode. Otherwise, check the current
    :py:class:`~djblets.siteconfig.models.SiteConfiguration` for
    ``site_read_only``.

    Args:
        user (django.contrib.auth.models.User):
            The user that is to be checked.

    Returns:
        bool:
        Whether the site is read-only for a user.
    """
    if user.is_superuser:
        return False

    if not hasattr(user, '_is_site_read_only'):
        siteconfig = SiteConfiguration.objects.get_current()
        user._is_site_read_only = siteconfig.get('site_read_only')

    return user._is_site_read_only
