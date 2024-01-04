"""Testing utilities for building expected queries for Local Sites.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union

from django.contrib.auth.models import User
from django.db.models import Q, Value
from djblets.db.query_comparator import ExpectedQueries

from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser


def get_local_site_by_name_equeries(
    *,
    local_site: LocalSite,
) -> ExpectedQueries:
    """Return expected queries for accessing a Local Site by name.

    Version Added:
        5.0.7

    Args:
        local_site (reviewboard.site.models.LocalSite):
            The Local Site being accessed.

    Returns:
        list of dict:
        The list of expected queries.
    """
    return [
        {
            '__note__': f'Fetch the Local Site "{local_site.name}"',
            'model': LocalSite,
            'where': Q(name=local_site.name),
        },
    ]


def get_local_site_is_accessible_by_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: LocalSite,
) -> ExpectedQueries:
    """Return expected queries for Local Site accessibility checks.

    This corresponds to a call to :py:meth:`LocalSite.is_accessible_by()
    <reviewboard.site.models.LocalSite.is_accessible_by>`.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite):
            The Local Site being accessed.

    Returns:
        list of dict:
        The list of expected queries.
    """
    if user.is_superuser or user.is_anonymous:
        return []

    return [
        {
            '__note__': 'Check if the user is a member of the Local Site',
            'model': User,
            'annotations': {
                'a': Value(1),
            },
            'join_types': {
                'site_localsite_users': 'INNER JOIN',
            },
            'limit': 1,
            'num_joins': 1,
            'tables': {
                'auth_user',
                'site_localsite_users',
            },
            'where': (Q(local_site__id=local_site.pk) &
                      Q(pk=user.pk)),
        },
    ]


def get_local_site_is_mutable_by_equeries(
    *,
    user: User,
    local_site: LocalSite,
    note: Optional[str] = None,
) -> ExpectedQueries:
    """Return expected queries for Local Site mutability checks.

    This corresponds to a call to :py:meth:`LocalSite.is_mutable_by()
    <reviewboard.site.models.LocalSite.is_mutable_by>`.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite):
            The Local Site being accessed.

        note (str, optional):
            An optional note to use, instead of the default.

    Returns:
        list of dict:
        The list of expected queries.
    """
    if user.is_superuser or user.is_anonymous:
        return []

    return [
        {
            '__note__': note or (
                'Check if the user is an admin of the Local Site'
            ),
            'model': User,
            'annotations': {
                'a': Value(1),
            },
            'join_types': {
                'site_localsite_admins': 'INNER JOIN',
            },
            'limit': 1,
            'num_joins': 1,
            'tables': {
                'auth_user',
                'site_localsite_admins',
            },
            'where': (Q(local_site_admins__id=local_site.pk) &
                      Q(pk=user.pk)),
        },
    ]


def get_check_local_site_access_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: LocalSite,
) -> ExpectedQueries:
    """Return expected queries for the @check_local_site_access decorator.

    This corresponds to a call to
    :py:func:`~reviewboard.site.decorators.check_local_site_access`.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite):
            The Local Site being accessed.

    Returns:
        list of dict:
        The list of expected queries.
    """
    return (get_local_site_by_name_equeries(local_site=local_site) +
            get_local_site_is_accessible_by_equeries(user=user,
                                                     local_site=local_site))
