"""Standard authentication backend."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set, TYPE_CHECKING, Union, cast

from django.conf import settings
from django.contrib.auth import hashers
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from djblets.db.query import get_object_or_none

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.forms.auth import StandardAuthSettingsForm
from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
    from django.db.models import Model
    from django.http import HttpRequest


logger = logging.getLogger(__name__)


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

    def authenticate(
        self,
        request: Optional[HttpRequest] = None,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ) -> Optional[User]:
        """Authenticate the user.

        This will attempt to authenticate the user against the database.
        If the username and password are valid, a user will be returned.

        Version Changed:
            6.0:
            * ``request`` is now optional.
            * ``username`` and ``password`` are technically optional, to
              aid in consistency for type hints, but will result in a ``None``
              result.

        Version Changed:
            4.0:
            The ``request`` argument is now mandatory as the first positional
            argument, as per requirements in Django.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the caller. This may be ``None``.

            username (str):
                The username used for authentication.

            password (str):
                The password used for authentication.

            **kwargs (dict, unused):
                Additional keyword arguments supplied by the caller.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user, or ``None`` if the user could not be
            authenticated for any reason.
        """
        return cast(
            User,
            ModelBackend.authenticate(self,
                                      request,
                                      username=username,
                                      password=password,
                                      **kwargs))

    def get_or_create_user(
        self,
        username: str,
        request: Optional[HttpRequest] = None,
    ) -> Optional[User]:
        """Return an existing user or create one if it doesn't exist.

        This does not authenticate the user.

        Args:
            username (str):
                The username to fetch or create.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Returns:
            django.contrib.auth.models.User:
            The resulting user, or ``None`` if one could not be found.
        """
        return get_object_or_none(User, username=username)

    def update_password(
        self,
        user: User,
        password: str,
    ) -> None:
        """Update a user's password on the backend.

        This will update the user information, but will not save the user
        instance. That must be saved manually.

        Args:
            user (django.contrib.auth.models.User):
                The user whose password will be changed.

            password (str):
                The new password.
        """
        user.password = hashers.make_password(password)

    def get_all_permissions(
        self,
        user: Union[AbstractBaseUser, AnonymousUser],
        obj: Optional[Model] = None,
    ) -> Set[str]:
        """Return a list of all permissions for a user.

        If a LocalSite instance is passed as ``obj``, then the permissions
        returned will be those that the user has on that LocalSite. Otherwise,
        they will be their global permissions.

        It is not legal to pass any other object.

        Args:
            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to retrieve permission for.

            obj (django.db.models.Model, optional):
                A model used as context.

                If provided, this must be a
                :py:class:`~reviewboard.site.models.LocalSite`.

        Returns:
            set of str:
            A set of all permission codes.
        """
        if obj is not None and not isinstance(obj, LocalSite):
            logger.error('Unexpected object %r passed to '
                         'StandardAuthBackend.get_all_permissions. '
                         'Returning an empty list.',
                         obj)

            if settings.DEBUG:
                raise ValueError('Unexpected object %r' % obj)

            return set()

        if user.is_anonymous:
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
            local_site_perm_cache: Dict[str, Set[str]]

            try:
                local_site_perm_cache = getattr(user, '_local_site_perm_cache')
            except AttributeError:
                local_site_perm_cache = {}
                setattr(user, '_local_site_perm_cache', local_site_perm_cache)

            if obj.pk not in local_site_perm_cache:
                perm_cache: Set[str] = set()

                try:
                    site_profile = user.get_site_profile(
                        obj,
                        create_if_missing=False)
                    site_perms = site_profile.permissions or {}

                    if site_perms:
                        perm_cache = {
                            key
                            for key, value in site_perms.items()
                            if value
                        }
                except LocalSiteProfile.DoesNotExist:
                    pass

                local_site_perm_cache[obj.pk] = perm_cache

            permissions = permissions.copy()
            permissions.update(local_site_perm_cache[obj.pk])

        return permissions

    def has_perm(
        self,
        user: Union[AbstractBaseUser, AnonymousUser],
        perm: str,
        obj: Any = None,
    ) -> bool:
        """Return whether or not a user has the given permission.

        If a LocalSite instance is passed as ``obj``, then the permissions
        checked will be those that the user has on that LocalSite. Otherwise,
        they will be their global permissions.

        It is not legal to pass any other object.

        Args:
            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to retrieve permission for.

            perm (str):
                The permission code to check for.

            obj (django.db.models.Model, optional):
                A model used as context.

                If provided, this must be a
                :py:class:`~reviewboard.site.models.LocalSite`.

        Returns:
            bool:
            ``True`` if the user has the permission. ``False`` if it does not.
        """
        if obj is not None and not isinstance(obj, LocalSite):
            logger.error('Unexpected object %r passed to has_perm. '
                         'Returning False.', obj)

            if settings.DEBUG:
                raise ValueError('Unexpected object %r' % obj)

            return False

        if not user.is_active:
            return False

        if obj is not None:
            local_site_admin_for: Dict[str, bool]

            try:
                local_site_admin_for = getattr(user, '_local_site_admin_for')
            except AttributeError:
                local_site_admin_for = {}
                setattr(user, '_local_site_admin_for', local_site_admin_for)

            try:
                is_mutable = local_site_admin_for[obj.pk]
            except KeyError:
                is_mutable = obj.is_mutable_by(user)
                local_site_admin_for[obj.pk] = is_mutable

            if is_mutable:
                return perm in self._VALID_LOCAL_SITE_PERMISSIONS

        return super().has_perm(user, perm, obj)
