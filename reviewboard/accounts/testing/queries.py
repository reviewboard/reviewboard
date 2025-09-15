"""Testing utilities for building expected queries for accounts.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from django.contrib.auth.models import Permission, User
from django.db.models import Q

from reviewboard.accounts.models import LocalSiteProfile, Profile

if TYPE_CHECKING:
    from django_assert_queries.query_comparator import ExpectedQueries

    from reviewboard.site.models import LocalSite


def get_user_by_pk_equeries(
    *,
    user: User,
    note: Optional[str] = None,
) -> ExpectedQueries:
    """Return expected queries for fetching a user by ID.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's expected to be fetched.

        note (str, optional):
            An optional note to use, instead of the default.

    Returns:
        list of dict:
        The list of expected queries.
    """
    return [
        {
            '__note__': note or f'Fetch the user {user.username}',
            'model': User,
            'where': Q(pk=user.pk),
        },
    ]


def get_user_local_site_profile_equeries(
    *,
    user: User,
    profile: Profile,
    local_site: Optional[LocalSite] = None,
) -> ExpectedQueries:
    """Return expected queries for accessing a user's LocalSiteProfile.

    This corresponds to a call to :py:meth:`User.get_site_profile()`.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user with the profile.

        profile (reviewboard.accounts.models.Profile):
            The user's primary profile.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site associated with the profile.

    Returns:
        list of dict:
        The list of expected queries.
    """
    return [
        {
            '__note__': "Fetch the user's LocalSiteProfile",
            'model': LocalSiteProfile,
            'where': (Q(local_site=local_site) &
                      Q(profile=profile) &
                      Q(user=user)),
        }
    ]


def get_user_permissions_equeries(
    *,
    user: User,
) -> ExpectedQueries:
    """Return expected queries for fetching a user's permissions.

    This corresponds to a call to :py:meth:`StandardAuthBackend.has_perm()
    <reviewboard.accounts.backends.standard.StandardAuthBackend>`, without
    passing a Local Site.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user with the profile.

    Returns:
        list of dict:
        The list of expected queries.
    """
    username = user.username

    return [
        {
            '__note__': f'Fetch the user "{username}"\'s permissions',
            'join_types': {
                'auth_user_user_permissions': 'INNER JOIN',
                'django_content_type': 'INNER JOIN',
            },
            'model': Permission,
            'num_joins': 2,
            'tables': {
                'auth_permission',
                'auth_user_user_permissions',
                'django_content_type',
            },
            'values_select': ('content_type__app_label', 'codename'),
            'where': Q(user__id=user.pk),
        },
        {
            '__note__': f'Fetch the user "{username}"\'s permission groups',
            'join_types': {
                'auth_group': 'INNER JOIN',
                'auth_group_permissions': 'INNER JOIN',
                'auth_user_groups': 'INNER JOIN',
                'django_content_type': 'INNER JOIN',
            },
            'model': Permission,
            'num_joins': 4,
            'tables': {
                'auth_group',
                'auth_group_permissions',
                'auth_permission',
                'auth_user_groups',
                'django_content_type',
            },
            'values_select': ('content_type__app_label', 'codename'),
            'where': Q(group__user=user),
        },
    ]


def get_user_profile_equeries(
    *,
    user: User,
) -> ExpectedQueries:
    """Return expected queries for accessing a user's profile.

    This corresponds to a call to :py:meth:`User.get_profile()`.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user with the profile.

    Returns:
        list of dict:
        The list of expected queries.
    """
    return [
        {
            '__note__': "Fetch the user's profile",
            'model': Profile,
            'where': Q(user=user),
        },
    ]
