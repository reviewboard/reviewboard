"""Standard authentication backend."""

from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.auth import hashers
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from djblets.db.query import get_object_or_none

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import StandardAuthSettingsForm
from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.site.models import LocalSite


class StandardAuthBackend(BaseAuthBackend, ModelBackend):
    """Authenticate users against the local database.

    This will authenticate a user against their entry in the database, if
    the user has a local password stored. This is the default form of
    authentication in Review Board.

    This backend also handles permission checking for users on LocalSites.
    In Django, this is the responsibility of at least one auth backend in
    the list of configured backends.

    Regardless of the specific type of authentication chosen for the
    installation, StandardAuthBackend will always be provided in the list
    of configured backends. Because of this, it will always be able to
    handle authentication against locally added users and handle
    LocalSite-based permissions for all configurations.
    """

    backend_id = 'builtin'
    name = _('Standard Registration')
    settings_form = StandardAuthSettingsForm
    supports_registration = True
    supports_change_name = True
    supports_change_email = True
    supports_change_password = True

    _VALID_LOCAL_SITE_PERMISSIONS = [
        'hostingsvcs.change_hostingserviceaccount',
        'hostingsvcs.create_hostingserviceaccount',
        'reviews.add_group',
        'reviews.can_change_status',
        'reviews.can_edit_reviewrequest',
        'reviews.can_submit_as_another_user',
        'reviews.can_view_invite_only_groups',
        'reviews.change_default_reviewer',
        'reviews.change_group',
        'reviews.delete_file',
        'reviews.delete_screenshot',
        'scmtools.add_repository',
        'scmtools.change_repository',
    ]

    def authenticate(self, request, username, password, **kwargs):
        """Authenticate the user.

        This will attempt to authenticate the user against the database.
        If the username and password are valid, a user will be returned.

        Version Changed:
            4.0:
            The ``request`` argument is now mandatory as the first positional
            argument, as per requirements in Django.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the caller. This may be ``None``.

            username (unicode):
                The username used for authentication.

            password (unicode):
                The password used for authentication.

            **kwargs (dict, unused):
                Additional keyword arguments supplied by the caller.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user, or ``None`` if the user could not be
            authenticated for any reason.
        """
        return ModelBackend.authenticate(self,
                                         request,
                                         username=username,
                                         password=password,
                                         **kwargs)

    def get_or_create_user(self, username, request):
        """Get an existing user, or create one if it does not exist."""
        return get_object_or_none(User, username=username)

    def update_password(self, user, password):
        """Update the given user's password."""
        user.password = hashers.make_password(password)

    def get_all_permissions(self, user, obj=None):
        """Get a list of all permissions for a user.

        If a LocalSite instance is passed as ``obj``, then the permissions
        returned will be those that the user has on that LocalSite. Otherwise,
        they will be their global permissions.

        It is not legal to pass any other object.
        """
        if obj is not None and not isinstance(obj, LocalSite):
            logging.error('Unexpected object %r passed to '
                          'StandardAuthBackend.get_all_permissions. '
                          'Returning an empty list.',
                          obj)

            if settings.DEBUG:
                raise ValueError('Unexpected object %r' % obj)

            return set()

        if user.is_anonymous():
            return set()

        # First, get the list of all global permissions.
        #
        # Django's ModelBackend doesn't support passing an object, and will
        # return an empty set, so don't pass an object for this attempt.
        permissions = \
            super(StandardAuthBackend, self).get_all_permissions(user)

        if obj is not None:
            # We know now that this is a LocalSite, due to the assertion
            # above.
            if not hasattr(user, '_local_site_perm_cache'):
                user._local_site_perm_cache = {}

            if obj.pk not in user._local_site_perm_cache:
                perm_cache = set()

                try:
                    site_profile = user.get_site_profile(
                        obj,
                        create_if_missing=False)
                    site_perms = site_profile.permissions or {}

                    if site_perms:
                        perm_cache = set([
                            key
                            for key, value in six.iteritems(site_perms)
                            if value
                        ])
                except LocalSiteProfile.DoesNotExist:
                    pass

                user._local_site_perm_cache[obj.pk] = perm_cache

            permissions = permissions.copy()
            permissions.update(user._local_site_perm_cache[obj.pk])

        return permissions

    def has_perm(self, user, perm, obj=None):
        """Get whether or not a user has the given permission.

        If a LocalSite instance is passed as ``obj``, then the permissions
        checked will be those that the user has on that LocalSite. Otherwise,
        they will be their global permissions.

        It is not legal to pass any other object.
        """
        if obj is not None and not isinstance(obj, LocalSite):
            logging.error('Unexpected object %r passed to has_perm. '
                          'Returning False.', obj)

            if settings.DEBUG:
                raise ValueError('Unexpected object %r' % obj)

            return False

        if not user.is_active:
            return False

        if obj is not None:
            if not hasattr(user, '_local_site_admin_for'):
                user._local_site_admin_for = {}

            if obj.pk not in user._local_site_admin_for:
                user._local_site_admin_for[obj.pk] = obj.is_mutable_by(user)

            if user._local_site_admin_for[obj.pk]:
                return perm in self._VALID_LOCAL_SITE_PERMISSIONS

        return super(StandardAuthBackend, self).has_perm(user, perm, obj)
