"""Testing utilities for building expected queries for repositories.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from django.contrib.auth.models import User
from django.db.models import Q
from djblets.db.query_comparator import ExpectedQueries

from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from reviewboard.site.models import AnyOrAllLocalSites


def get_repositories_accessible_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    visible_only: bool = True,
    distinct: bool = True,
) -> ExpectedQueries:
    """Return expected queries for Repository.objects.accessible().

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        visible_only (bool, optional):
            Whether the queries are for visible repositories only.

        distinct (bool, optional):
            Whether to expect a distinct query.

    Returns:
        list of dict:
        The list of expected queries.
    """
    # This is intentionally made to be verbose. Rather than constructing Q
    # objects more dynamically (like the accessible() implementation does),
    # we want to have each case build up the full query, so each combination
    # is explicitly defined.
    repositories_tables = {'scmtools_repository'}

    if user.is_superuser:
        if visible_only:
            if local_site is LocalSite.ALL:
                repositories_where = Q(visible=True)
            else:
                repositories_where = (Q(visible=True) &
                                      Q(local_site=local_site))
        else:
            if local_site is LocalSite.ALL:
                repositories_where = Q()
            else:
                repositories_where = Q(local_site=local_site)
    elif user.is_authenticated:
        repositories_tables.update({
            'reviews_group',
            'reviews_group_users',
            'scmtools_repository_review_groups',
            'scmtools_repository_users',
        })

        if visible_only:
            if local_site is LocalSite.ALL:
                repositories_where = ((Q(public=True) &
                                       Q(visible=True)) |
                                      Q(users__pk=user.pk) |
                                      Q(review_groups__users=user.pk))
            else:
                repositories_where = (((Q(public=True) &
                                        Q(visible=True)) |
                                       Q(users__pk=user.pk) |
                                       Q(review_groups__users=user.pk)) &
                                      Q(local_site=local_site))
        else:
            if local_site is LocalSite.ALL:
                repositories_where = (Q(public=True) |
                                      (Q(users__pk=user.pk) |
                                       Q(review_groups__users=user.pk)))
            else:
                repositories_where = ((Q(public=True) |
                                       (Q(users__pk=user.pk) |
                                        Q(review_groups__users=user.pk))) &
                                      Q(local_site=local_site))
    else:
        assert user.is_anonymous

        if visible_only:
            if local_site is LocalSite.ALL:
                repositories_where = (Q(public=True) &
                                      Q(visible=True))
            else:
                repositories_where = (Q(public=True) &
                                      Q(visible=True) &
                                      Q(local_site=local_site))
        else:
            if local_site is LocalSite.ALL:
                repositories_where = Q(public=True)
            else:
                repositories_where = (Q(public=True) &
                                      Q(local_site=local_site))

    return [
        {
            '__note__': 'Fetch a list of accessible repositories',
            'distinct': distinct,
            'model': Repository,
            'num_joins': len(repositories_tables) - 1,
            'tables': repositories_tables,
            'where': repositories_where,
        },
    ]


def get_repositories_accessible_ids_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    visible_only: bool = True,
) -> ExpectedQueries:
    """Return expected queries for Repository.objects.accessible_ids().

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        visible_only (bool, optional):
            Whether the queries are for visible repositories only.

    Returns:
        list of dict:
        The list of expected queries.
    """
    equeries = get_repositories_accessible_equeries(
        user=user,
        local_site=local_site,
        visible_only=visible_only,
        distinct=False)
    equeries[-1].update({
        '__note__': 'Fetch a list of accessible repository IDs',
        'values_select': ('pk',),
    })

    return equeries
