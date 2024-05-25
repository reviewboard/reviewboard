"""Testing utilities for building expected queries for review groups.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Dict, Set, TYPE_CHECKING, Union

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q
from djblets.db.query_comparator import ExpectedQueries

from reviewboard.accounts.testing.queries import (
    get_user_local_site_profile_equeries,
    get_user_permissions_equeries,
)
from reviewboard.reviews.models import Group
from reviewboard.site.models import LocalSite
from reviewboard.site.testing.queries import \
    get_local_site_is_mutable_by_equeries

if TYPE_CHECKING:
    from reviewboard.site.models import AnyOrAllLocalSites
    from reviewboard.testing.queries.base import ExpectedQResult


def get_review_groups_accessible_q(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    visible_only: bool = True,
    has_view_invite_only_groups_perm: bool = False,
    needs_local_site_profile_query: bool = False,
    needs_user_permission_queries: bool = True,
    users_join_type: str = 'INNER JOIN',
) -> ExpectedQResult:
    """Return a Q expression for accessible review group queries.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        visible_only (bool, optional):
            Whether the query is limited to visible review groups.

        has_view_invite_only_groups_perm (bool, optional):
            Whether to expect the ``reviews.has_view_invite_only_groups_perm``
            permission to be set.

            Set to ``True`` if this is not cached at this point.

        needs_local_site_profile_query (bool, optional):
            Whether the query should fetch a
            :py:class:`~reviewboard.accounts.models.LocalSiteProfile`.

            Set to ``True`` if this is not cached at this point.

        needs_user_permission_queries (bool, optional):
            Whether the query should check for the
            ``reviews.can_view_invite_only_groups`` permission.

            Set to ``False`` if this is already cached at this point.

        users_join_type (str, optional):
            The join type expected for any users relations.

            This defaults to `INNER JOIN`, as that's more likely in cases where
            this is being embedded in another query, outside of the manager's
            own methods.

    Returns:
        dict:
        The expected Q results.
    """
    tables: Set[str] = {'reviews_group'}
    join_types: Dict[str, str] = {}

    if user.is_superuser:
        if visible_only:
            if local_site is LocalSite.ALL:
                q = Q(visible=True)
            else:
                q = (Q(visible=True) &
                     Q(local_site=local_site))
        else:
            if local_site is LocalSite.ALL:
                q = Q()
            else:
                q = Q(local_site=local_site)
    elif user.is_authenticated:
        if has_view_invite_only_groups_perm and visible_only:
            tables.add('reviews_group_users')
            join_types['reviews_group_users'] = users_join_type

            if local_site is LocalSite.ALL:
                q = (Q(visible=True) |
                     Q(users=user.pk))
            else:
                q = ((Q(visible=True) |
                      Q(users=user.pk)) &
                     Q(local_site=local_site))
        elif has_view_invite_only_groups_perm and not visible_only:
            if local_site is LocalSite.ALL:
                q = Q()
            else:
                q = Q(local_site=local_site)
        elif not has_view_invite_only_groups_perm and visible_only:
            tables.add('reviews_group_users')
            join_types['reviews_group_users'] = users_join_type

            if local_site is LocalSite.ALL:
                q = ((Q(invite_only=False) &
                      Q(visible=True)) |
                     Q(users=user.pk))
            else:
                q = (((Q(invite_only=False) &
                       Q(visible=True)) |
                      Q(users=user.pk)) &
                     Q(local_site=local_site))
        else:
            tables.add('reviews_group_users')
            join_types['reviews_group_users'] = users_join_type

            if local_site is LocalSite.ALL:
                q = (Q(invite_only=False) |
                     Q(users=user.pk))
            else:
                q = ((Q(invite_only=False) |
                      Q(users=user.pk)) &
                     Q(local_site=local_site))
    else:
        assert user.is_anonymous

        if visible_only:
            if local_site is LocalSite.ALL:
                q = (Q(invite_only=False) &
                     Q(visible=True))
            else:
                q = ((Q(invite_only=False) &
                      Q(visible=True)) &
                     Q(local_site=local_site))
        else:
            if local_site is LocalSite.ALL:
                q = Q(invite_only=False)
            else:
                q = (Q(invite_only=False) &
                     Q(local_site=local_site))

    return {
        'join_types': join_types,
        'prep_equeries': get_review_groups_accessible_prep_equeries(
            user=user,
            local_site=local_site,
            needs_local_site_profile_query=needs_local_site_profile_query,
            needs_user_permission_queries=needs_user_permission_queries),
        'q': q,
        'tables': tables,
    }


def get_review_groups_accessible_prep_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    needs_local_site_profile_query: bool = False,
    needs_user_permission_queries: bool = True,
) -> ExpectedQueries:
    """Return expected Group accessibility preparation queries.

    These are queries that must be performed before the main accessibility
    query is executed.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        needs_local_site_profile_query (bool, optional):
            Whether the query should fetch a
            :py:class:`~reviewboard.accounts.models.LocalSiteProfile`.

            Set to ``True`` if this is not cached at this point.

        needs_user_permission_queries (bool, optional):
            Whether the query should check for the
            ``reviews.can_view_invite_only_groups`` permission.

            Set to ``False`` if this is already cached at this point.

    Returns:
        list of dict:
        The list of expected queries.
    """
    equeries: ExpectedQueries = []

    if user.is_authenticated and not user.is_superuser:
        assert isinstance(user, User)

        # This starts out by checking for user permissions, both on the
        # User/Group and on the Local Site.
        if needs_user_permission_queries:
            equeries += get_user_permissions_equeries(user=user)

        if local_site is not None and local_site is not LocalSite.ALL:
            equeries += get_local_site_is_mutable_by_equeries(
                local_site=local_site,
                user=user)

            if needs_local_site_profile_query:
                equeries += get_user_local_site_profile_equeries(
                    user=user,
                    profile=user.get_profile(),
                    local_site=local_site)

    return equeries


def get_review_groups_accessible_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    visible_only: bool = True,
    has_view_invite_only_groups_perm: bool = False,
    needs_local_site_profile_query: bool = False,
    needs_user_permission_queries: bool = True,
) -> ExpectedQueries:
    """Return Group accessibility preparation queries.

    This corresponds to a call from
    :py:meth:`Group.objects.accessible()
    <reviewboard.reviews.managers.GroupManager.accessible>`.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        visible_only (bool, optional):
            Whether the queries are for visible groups only.

        has_view_invite_only_groups_perm (bool, optional):
            Whether to expect the ``reviews.has_view_invite_only_groups_perm``
            permission to be set.

        needs_local_site_profile_query (bool, optional):
            Whether the query should fetch a
            :py:class:`~reviewboard.accounts.models.LocalSiteProfile`.

            Set to ``False`` if this should be cached at this point.

        needs_user_permission_queries (bool, optional):
            Whether the query should check for the
            ``reviews.can_view_invite_only_groups`` permission.

            Set to ``False`` if this is already cached at this point.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_review_groups_accessible_q(
        user=user,
        local_site=local_site,
        visible_only=visible_only,
        has_view_invite_only_groups_perm=has_view_invite_only_groups_perm,
        users_join_type='LEFT OUTER JOIN',
        needs_local_site_profile_query=needs_local_site_profile_query,
        needs_user_permission_queries=needs_user_permission_queries)
    q_tables = q_result['tables']

    equeries: ExpectedQueries = q_result.get('prep_equeries', []) + [
        {
            '__note__': 'Fetch a list of accessible review groups',
            'distinct': True,
            'join_types': q_result.get('join_types', {}),
            'model': Group,
            'num_joins': len(q_tables) - 1,
            'tables': q_tables,
            'where': q_result['q'],
        },
    ]

    return equeries


def get_review_groups_accessible_ids_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    visible_only: bool = True,
    has_view_invite_only_groups_perm: bool = False,
    needs_local_site_profile_query: bool = False,
    needs_user_permission_queries: bool = True,
) -> ExpectedQueries:
    """Return expected queries for Group.objects.accessible_ids().

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        visible_only (bool, optional):
            Whether the queries are for visible groups only.

        has_view_invite_only_groups_perm (bool, optional):
            Whether to expect the ``reviews.has_view_invite_only_groups_perm``
            permission to be set.

        needs_local_site_profile_query (bool, optional):
            Whether the query should fetch a
            :py:class:`~reviewboard.accounts.models.LocalSiteProfile`.

            Set to ``False`` if this should be cached at this point.

        needs_user_permission_queries (bool, optional):
            Whether the query should check for the
            ``reviews.can_view_invite_only_groups`` permission.

            Set to ``False`` if this is already cached at this point.

    Returns:
        list of dict:
        The list of expected queries.
    """
    equeries = get_review_groups_accessible_equeries(
        user=user,
        local_site=local_site,
        visible_only=visible_only,
        has_view_invite_only_groups_perm=has_view_invite_only_groups_perm,
        needs_local_site_profile_query=needs_local_site_profile_query,
        needs_user_permission_queries=needs_user_permission_queries)
    equeries[-1].update({
        '__note__': 'Fetch a list of accessible review group IDs',
        'distinct': False,
        'values_select': ('pk',),
    })

    return equeries
