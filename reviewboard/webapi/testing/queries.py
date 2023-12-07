"""Testing utilities for API unit tests.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional, Set, TYPE_CHECKING, Type, Union

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Count, Q
from djblets.db.query_comparator import ExpectedQueries
from oauth2_provider.models import AccessToken

from reviewboard.accounts.testing.queries import get_user_profile_equeries
from reviewboard.oauth.models import Application
from reviewboard.site.testing.queries import (
    get_check_local_site_access_equeries,
)
from reviewboard.testing.queries.http import get_http_request_user_equeries
from reviewboard.webapi.models import WebAPIToken

if TYPE_CHECKING:
    from django.db.models import Model

    from reviewboard.site.models import LocalSite
    from reviewboard.testing.queries.base import ExpectedQResult


def get_webapi_token_equeries(
    *,
    user: User,
    webapi_token: WebAPIToken,
) -> ExpectedQueries:
    """Return expected queries for fetching API tokens for a user.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.User):
            The user that owns the API token.

        webapi_token (reviewboard.webapi.models.WebAPIToken):
            The API token being fetched.

    Returns:
        list of dict:
        The list of expected queries.
    """
    return [
        {
            '__note__': 'Fetch the API token for the request',
            'model': WebAPIToken,
            'where': (Q(pk=webapi_token.pk) &
                      Q(user=user)),
        },
    ]


def get_webapi_request_start_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: Optional[LocalSite] = None,
    webapi_token: Optional[WebAPIToken] = None,
    oauth2_access_token: Optional[AccessToken] = None,
    oauth2_application: Optional[Application] = None,
) -> ExpectedQueries:
    """Return expected queries for the start of an API HTTP request.

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
    assert (oauth2_access_token is None) is (oauth2_application is None)

    equeries: ExpectedQueries = []

    if user.is_authenticated:
        assert isinstance(user, User)

        equeries += get_http_request_user_equeries(user=user)
        equeries += get_user_profile_equeries(user=user)

        if webapi_token is not None:
            equeries += get_webapi_token_equeries(
                user=user,
                webapi_token=webapi_token)

        if oauth2_access_token is not None:
            assert oauth2_application is not None

            equeries += [
                {
                    '__note__': 'Fetch the OAuth2 token for the request',
                    'model': AccessToken,
                    'where': Q(pk=oauth2_access_token.pk),
                },
                {
                    '__note__': 'Fetch the OAuth2 application for the token',
                    'model': Application,
                    'where': Q(id=oauth2_application.pk),
                },
            ]

    if local_site is not None:
        equeries += get_check_local_site_access_equeries(
            user=user,
            local_site=local_site)

    return equeries


def get_webapi_response_start_equeries(
    *,
    model: Type[Model],
    items_q_result: ExpectedQResult,
    items_distinct: bool = False,
    items_select_related: Set[str] = set(),
) -> ExpectedQueries:
    """Return expected queries for the start of an API payload response.

    Version Added:
        5.0.7

    Args:
        model (type):
            The type of model backing the resource.

        items_q_result (dict):
            An expected Q result representing the queries for items and
            item counts.

        items_distinct (bool, optional):
            Whether the items query is expected to be distinct.

        items_select_related (set of str, optional):
            Any models that are select-related for this query.

    Returns:
        list of dict:
        The list of expected queries.
    """
    items_q_tables = items_q_result['tables']
    items_q_join_types = items_q_result.get('join_types', {})
    items_q_num_joins = len(items_q_tables) - 1
    items_q_subqueries = items_q_result.get('subqueries', [])

    equeries = items_q_result.get('prep_equeries', [])

    if items_distinct:
        equeries += [
            {
                '__note__': 'Fetch the total number of items',
                'annotations': {
                    '__count': Count('*'),
                },
                'model': model,

                'subqueries': [
                    {
                        'distinct': True,
                        'join_types': items_q_join_types,
                        'model': model,
                        'num_joins': items_q_num_joins,
                        'subquery': True,
                        'tables': items_q_tables,
                        'where': items_q_result['q'],
                    },
                ],
            },
        ]
    else:
        equeries += [
            {
                '__note__': 'Fetch the total number of items',
                'annotations': {
                    '__count': Count('*'),
                },
                'join_types': items_q_join_types,
                'model': model,
                'num_joins': items_q_num_joins,
                'subqueries': items_q_subqueries,
                'tables': items_q_tables,
                'where': items_q_result['q'],
            },
        ]

    equeries += [
        {
            '__note__': 'Fetch a page of items',
            'distinct': items_distinct,
            'join_types': items_q_join_types,
            'limit': 25,
            'model': model,
            'num_joins': items_q_num_joins,
            'select_related': items_select_related,
            'subqueries': items_q_subqueries,
            'tables': items_q_tables,
            'where': items_q_result['q'],
        },
    ]

    return equeries
