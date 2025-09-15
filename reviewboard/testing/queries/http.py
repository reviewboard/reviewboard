"""Testing utilities for building HTTP-related expected queries.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union

from django.contrib.auth.models import AnonymousUser, User

from reviewboard.accounts.testing.queries import (
    get_user_by_pk_equeries,
    get_user_profile_equeries)
from reviewboard.site.testing.queries import \
    get_check_local_site_access_equeries

if TYPE_CHECKING:
    from django_assert_queries.query_comparator import ExpectedQueries

    from reviewboard.site.models import LocalSite


def get_http_request_user_equeries(
    *,
    user: User,
) -> ExpectedQueries:
    """Return expected queries for fetching the user from the HTTP request.

    This corresponds to a call to :py:attr:`HttpRequest.user
    <django.http.HttpRequest.user>`.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.User):
            The user that's expected to be fetched.

    Returns:
        list of dict:
        The list of expected queries.
    """
    return get_user_by_pk_equeries(
        user=user,
        note=f'Fetch the logged-in user "{user.username}"')


def get_http_request_start_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: Optional[LocalSite] = None,
    checks_local_site_access: bool = True,
) -> ExpectedQueries:
    """Return expected queries for the start of an HTTP request.

    This covers queries that fetch the user, their profile, and optionally
    the check for Local Site access.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        checks_local_site_access (bool, optional):
            Whether the requested view uses the
            :py:func:`~reviewboard.site.decorators.check_local_site_access`
            decorator.

    Returns:
        list of dict:
        The list of expected queries.
    """
    equeries: ExpectedQueries = []

    if user.is_authenticated:
        assert isinstance(user, User)

        equeries += get_http_request_user_equeries(user=user)
        equeries += get_user_profile_equeries(user=user)

    if local_site is not None and checks_local_site_access:
        equeries += get_check_local_site_access_equeries(user=user,
                                                         local_site=local_site)

    return equeries
