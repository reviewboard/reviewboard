"""Testing utilities for building expected queries for review requests.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional, Sequence, Set, TYPE_CHECKING, Union

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q

from reviewboard.accounts.testing.queries import get_user_profile_equeries
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.testing.queries.review_groups import \
    get_review_groups_accessible_ids_equeries
from reviewboard.scmtools.testing.queries import \
    get_repositories_accessible_ids_equeries
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries
    from typing_extensions import NotRequired, TypedDict, Unpack

    from reviewboard.accounts.models import Profile
    from reviewboard.site.models import AnyOrAllLocalSites
    from reviewboard.testing.queries.base import ExpectedQResult

    class _AccessibleKwargs(TypedDict):
        user: Optional[Union[AnonymousUser, User]]
        local_site: NotRequired[AnyOrAllLocalSites]
        has_local_sites_in_db: NotRequired[bool]
        show_all_unpublished: NotRequired[bool]
        show_inactive: NotRequired[bool]
        filter_private: NotRequired[bool]
        status: NotRequired[Optional[str]]
        extra_query: NotRequired[Q]
        accessible_repository_ids: NotRequired[Sequence[int]]
        accessible_review_group_ids: NotRequired[Sequence[int]]
        needs_local_site_profile_query: NotRequired[bool]
        needs_user_permission_queries: NotRequired[bool]


##########################
# Q-expression utilities #
##########################

def get_review_requests_accessible_q(
    *,
    user: Optional[Union[AnonymousUser, User]],
    local_site: AnyOrAllLocalSites = None,
    has_local_sites_in_db: bool = False,
    show_all_unpublished: bool = False,
    show_inactive: bool = False,
    filter_private: bool = False,
    status: Optional[str] = 'P',
    extra_query: Q = Q(),
    accessible_repository_ids: Sequence[int] = [],
    accessible_review_group_ids: Sequence[int] = [],
    needs_local_site_profile_query: bool = False,
    needs_user_permission_queries: bool = True,
) -> ExpectedQResult:
    """Return a Q expression for accessible review request queries.

    Version Added:
        5.0.7

    Args:
        user (django.contrib.auth.models.AnonymousUser or
              django.contrib.auth.models.User):
            The user that's checked for access.

        local_site (reviewboard.site.models.LocalSite, optional):
            The optional Local Site value used in the queries.

        has_local_sites_in_db (bool, optional):
            Whether the query expects Local Sites to be in the database.

        show_all_unpublished (bool, optional):
            Whether unpublished review requests would be allowed in the
            results.

        show_inactive (bool, optional):
            Whether review requests from inactive users would be allowed in
            the results.

        filter_private (bool, optional):
            Whether review requests would be filtered using ACL checks.

        status (str, optional):
            The optional status that would be used in the query.

        extra_query (django.db.models.Q, optional):
            An extra query filter that would be included.

        accessible_repository_ids (list of int, optional):
            A list of accessible repository IDs that would be expected in the
            query.

        accessible_review_group_ids (list of int, optional):
            A list of accessible review group IDs that would be expected in the
            query.

        needs_local_site_profile_query (bool, optional):
            Whether the query should fetch a
            :py:class:`~reviewboard.accounts.models.LocalSiteProfile`.

            Set this to ``False`` if this should be cached at this point.

        needs_user_permission_queries (bool, optional):
            Whether the query should check for the
            ``reviews.can_view_invite_only_groups`` permission.

            Set to ``False`` if this is already cached at this point.

    Returns:
        dict:
        The expected Q results.
    """
    include_local_site_q = (has_local_sites_in_db and
                            local_site is not LocalSite.ALL)

    prep_equeries: ExpectedQueries = []

    is_authenticated: bool
    is_superuser: bool

    if user is None or isinstance(user, AnonymousUser):
        is_authenticated = False
        is_superuser = False
    else:
        is_authenticated = True
        is_superuser = user.is_superuser

        if filter_private:
            prep_equeries = get_review_requests_accessible_prep_equeries(
                user=user,
                local_site=local_site,
                needs_local_site_profile_query=needs_local_site_profile_query,
                needs_user_permission_queries=needs_user_permission_queries)

    # This is intended to be verbose, to ensure we're matching exactly the
    # queries we expect. We want to minimize building of queries.
    #
    # That said, to keep this maintainable, query is built in 2 stages:
    #
    # 1. Initial caller-requested access control/visibility queries
    # 2. Access control filter queries
    init_q: Q
    access_q: Q
    tables: Set[str] = {'reviews_reviewrequest'}

    # Stage 1 has the following states (excluding Local Sites in DB):
    #
    # +----+---------------+----------------------+---------------+--------+
    # |  Q | authenticated | show_all_unpublished | show_inactive | status |
    # +----+---------------+----------------------+---------------+--------+
    # |  1 | X             | X                    | X             | x      |
    # |  2 | X             | X                    | X             |        |
    # |  3 | X             | X                    |               | X      |
    # |  4 | X             | X                    |               |        |
    # |  5 | X             |                      | X             | X      |
    # |  6 | X             |                      | X             |        |
    # |  7 | X             |                      |               | X      |
    # |  8 | X             |                      |               |        |
    # |  9 |               | X                    | X             | x      |
    # | 10 |               | X                    | X             |        |
    # | 11 |               | X                    |               | X      |
    # | 12 |               | X                    |               |        |
    # | 13 |               |                      | X             | X      |
    # | 14 |               |                      | X             |        |
    # | 15 |               |                      |               | X      |
    # | 16 |               |                      |               |        |
    # +----+---------------+----------------------+---------------+--------+
    #
    # Some of the resulting queries are identical, but will be repeated.
    if is_authenticated:
        if show_all_unpublished:
            if show_inactive and status:
                # Q 1
                if include_local_site_q:
                    init_q = (Q(status=status) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(status=status) &
                              extra_query)
            elif show_inactive and not status:
                # Q 2
                if include_local_site_q:
                    init_q = (Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = extra_query
            elif not show_inactive and status:
                # Q 3
                tables.add('auth_user')

                if include_local_site_q:
                    init_q = (Q(submitter__is_active=True) &
                              Q(status=status) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(submitter__is_active=True) &
                              Q(status=status) &
                              extra_query)
            else:
                # Q 4
                assert not show_inactive
                assert not status

                tables.add('auth_user')

                if include_local_site_q:
                    init_q = (Q(submitter__is_active=True) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(submitter__is_active=True) &
                              extra_query)
        else:
            # show_all_unpublished=False

            if show_inactive and status:
                # Q 5
                if include_local_site_q:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              Q(status=status) &
                              extra_query)
            elif show_inactive and not status:
                # Q 6
                if include_local_site_q:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              extra_query)
            elif not show_inactive and status:
                # Q 7
                tables.add('auth_user')

                if include_local_site_q:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              Q(submitter__is_active=True) &
                              Q(status=status) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              Q(submitter__is_active=True) &
                              Q(status=status) &
                              extra_query)
            else:
                # Q 8
                assert not show_inactive
                assert not status

                tables.add('auth_user')

                if include_local_site_q:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              Q(submitter__is_active=True) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = ((Q(public=True) |
                               Q(submitter=user)) &
                              Q(submitter__is_active=True) &
                              extra_query)
    else:
        # Anonymous.
        if show_all_unpublished:
            if show_inactive and status:
                # Q 9
                if include_local_site_q:
                    init_q = (Q(status=status) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(status=status) &
                              extra_query)
            elif show_inactive and not status:
                # Q 10
                if include_local_site_q:
                    init_q = (Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = extra_query
            elif not show_inactive and status:
                # Q 11
                tables.add('auth_user')

                if include_local_site_q:
                    init_q = (Q(submitter__is_active=True) &
                              Q(status=status) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(submitter__is_active=True) &
                              Q(status=status) &
                              extra_query)
            else:
                # Q 12
                assert not show_inactive
                assert not status

                tables.add('auth_user')

                if include_local_site_q:
                    init_q = (Q(submitter__is_active=True) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(submitter__is_active=True) &
                              extra_query)
        else:
            # show_all_unpublished=False

            if show_inactive and status:
                # Q 13
                if include_local_site_q:
                    init_q = (Q(public=True) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(public=True) &
                              Q(status=status) &
                              extra_query)
            elif show_inactive and not status:
                # Q 14
                if include_local_site_q:
                    init_q = (Q(public=True) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(public=True) &
                              extra_query)
            elif not show_inactive and status:
                # Q 15
                tables.add('auth_user')

                if include_local_site_q:
                    init_q = (Q(public=True) &
                              Q(submitter__is_active=True) &
                              Q(status=status) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(public=True) &
                              Q(submitter__is_active=True) &
                              Q(status=status) &
                              extra_query)
            else:
                # Q 16
                assert not show_inactive
                assert not status

                tables.add('auth_user')

                if include_local_site_q:
                    init_q = (Q(public=True) &
                              Q(submitter__is_active=True) &
                              Q(local_site=local_site) &
                              extra_query)
                else:
                    init_q = (Q(public=True) &
                              Q(submitter__is_active=True) &
                              extra_query)

    # Stage 2: Access control filters.
    if filter_private:
        if is_superuser:
            access_q = Q()
        else:
            tables.add('reviews_reviewrequest_target_groups')

            if is_authenticated:
                tables.add('reviews_reviewrequest_target_people')

                access_q = (Q(submitter=user) |
                            (Q(repository=None) |
                             Q(repository__in=accessible_repository_ids)) &
                            (Q(target_people=user) |
                             Q(target_groups=None) |
                             Q(target_groups__in=accessible_review_group_ids)))
            else:
                tables.update({
                    'reviews_group',
                    'scmtools_repository',
                })

                access_q = ((Q(repository=None) |
                             Q(repository__public=True)) &
                            (Q(target_groups=None) |
                             Q(target_groups__invite_only=False)))
    else:
        access_q = Q()

    return {
        'prep_equeries': prep_equeries,
        'q': init_q & access_q,
        'tables': tables,
    }


def get_review_requests_from_user_q(
    *,
    from_user: Union[str, User],
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQResult:
    """Return a Q expression for review requests from a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.from_user()
    <reviewboard.reviews.managers.ReviewRequestManager.from_user>`.

    It wraps :py:func:`get_review_requests_accessible_q` and takes all the same
    arguments.

    Version Added:
        5.0.7

    Args:
        from_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be published from
            for the query.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        dict:
        The expected Q results.
    """
    extra_tables: Set[str] = set()

    if isinstance(from_user, User):
        extra_query = Q(submitter=from_user)
    else:
        assert isinstance(from_user, str)

        extra_query = Q(submitter__username=from_user)
        extra_tables.add('auth_user')

    kwargs['extra_query'] = extra_query

    result_q = get_review_requests_accessible_q(**kwargs)
    result_q['tables'].update(extra_tables)

    return result_q


def get_review_requests_to_group_q(
    *,
    to_group_name: str,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQResult:
    """Return a Q expression for review requests to a group.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_group()
    <reviewboard.reviews.managers.ReviewRequestManager.to_group>`.

    It wraps :py:func:`get_review_requests_accessible_q` and takes all the same
    arguments.

    Version Added:
        5.0.7

    Args:
        to_group_name (str):
            The name of the group.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        dict:
        The expected Q results.
    """
    has_local_sites_in_db = kwargs.get('has_local_sites_in_db', False)

    if has_local_sites_in_db:
        extra_query = (Q(target_groups__name=to_group_name) &
                       Q(target_groups__local_site=kwargs.get('local_site')))
    else:
        extra_query = Q(target_groups__name=to_group_name)

    kwargs['extra_query'] = extra_query

    q_result = get_review_requests_accessible_q(**kwargs)
    q_result['tables'].update({
        'reviews_group',
        'reviews_reviewrequest_target_groups',
    })

    return q_result


def get_review_requests_to_user_q(
    *,
    to_user: Union[str, User],
    to_user_profile: Optional[Profile],
    target_groups: Sequence[Group] = [],
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQResult:
    """Return a Q expression for review requests to a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_user()
    <reviewboard.reviews.managers.ReviewRequestManager.to_user>`.

    It wraps :py:func:`get_review_requests_accessible_q` and takes all the same
    arguments.

    The ``prep_equeries`` key of the result must immediately precede any
    Usage of the resulting Q-expression.

    Version Added:
        5.0.7

    Args:
        to_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be assigned to.

        to_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user that review requests would be assigned to.

        target_groups (list of reviewboard.reviews.models.group.Group):
            The list of review groups that the user may be a member of,
            for the query.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        dict:
        The expected Q results.
    """
    extra_tables: Set[str] = {
        'reviews_reviewrequest_target_people',
        'reviews_reviewrequest_target_groups',
    }

    target_group_ids = [
        _group.pk
        for _group in target_groups
    ]

    prep_equeries: ExpectedQueries = []

    if isinstance(to_user, User):
        to_username = to_user.username
        needs_profile = False
    else:
        assert isinstance(to_user, str)

        to_username = to_user
        to_user = (
            User.objects
            .filter(username=to_user)
            .only('pk')
            .get()
        )
        needs_profile = True

        prep_equeries += [
            {
                '__note__': f'Fetching user {to_username}',
                'model': User,
                'where': Q(username=to_username),
            },
        ]

    if to_user_profile is None:
        extra_query = (Q(target_people=to_user) |
                       Q(target_groups__in=target_group_ids))
    else:
        extra_query = (Q(target_people=to_user) |
                       Q(target_groups__in=target_group_ids) |
                       Q(starred_by=to_user_profile))
        extra_tables.add('accounts_profile_starred_review_requests')

    kwargs['extra_query'] = extra_query

    q_result = get_review_requests_accessible_q(**kwargs)

    prep_equeries += q_result.get('prep_equeries', []) + [
        {
            '__note__': (
                f'Fetch the list of user "{to_username}"\'s review groups'
            ),
            'model': Group,
            'num_joins': 1,
            'values_select': ('pk',),
            'tables': {
                'reviews_group',
                'reviews_group_users',
            },
            'where': Q(users__id=to_user.pk),
        },
    ]

    if needs_profile:
        prep_equeries += get_user_profile_equeries(user=to_user)

    q_result['tables'].update(extra_tables)
    q_result['prep_equeries'] = prep_equeries

    return q_result


def get_review_requests_to_user_directly_q(
    *,
    to_user: Union[str, User],
    to_user_profile: Optional[Profile],
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQResult:
    """Return a Q expression for review requests directly to a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_user_directly()
    <reviewboard.reviews.managers.ReviewRequestManager.to_user_directly>`.

    It wraps :py:func:`get_review_requests_accessible_q` and takes all the same
    arguments.

    Version Added:
        5.0.7

    Args:
        to_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be assigned to.

        to_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user that review requests would be assigned to.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        dict:
        The expected Q results.
    """
    extra_tables: Set[str] = {'reviews_reviewrequest_target_people'}

    prep_equeries: ExpectedQueries = []

    if isinstance(to_user, User):
        to_username = to_user.username
        needs_profile = False
    else:
        assert isinstance(to_user, str)

        to_username = to_user
        to_user = (
            User.objects
            .filter(username=to_user)
            .only('pk')
            .get()
        )
        needs_profile = True

        prep_equeries += [
            {
                '__note__': f'Fetching user {to_username}',
                'model': User,
                'where': Q(username=to_username),
            },
        ]

    if to_user_profile is None:
        extra_query = Q(target_people=to_user)
    else:
        extra_query = (Q(target_people=to_user) |
                       Q(starred_by=to_user_profile))
        extra_tables.add('accounts_profile_starred_review_requests')

    kwargs['extra_query'] = extra_query

    q_result = get_review_requests_accessible_q(**kwargs)

    prep_equeries += q_result.get('prep_equeries', [])

    if needs_profile:
        prep_equeries += get_user_profile_equeries(user=to_user)

    q_result['tables'].update(extra_tables)
    q_result['prep_equeries'] = prep_equeries

    return q_result


def get_review_requests_to_user_groups_q(
    *,
    to_user: Union[str, User],
    to_user_profile: Optional[Profile],
    target_groups: Sequence[Group] = [],
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQResult:
    """Return a Q expression for review requests to a user's groups.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_user_groups()
    <reviewboard.reviews.managers.ReviewRequestManager.to_user_groups>`.

    It wraps :py:func:`get_review_requests_accessible_q` and takes all the same
    arguments.

    The ``prep_equeries`` key of the result must immediately precede any
    Usage of the resulting Q-expression.

    Version Added:
        5.0.7

    Args:
        to_user (str or django.contrib.auth.models.User):
            The username or user belonging to a group that review requests
            would be assigned to.

        to_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user belonging to a group that review requests
            would be assigned to.

        target_groups (list of reviewboard.reviews.models.group.Group):
            The list of review groups that the user may be a member of,
            for the query.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        dict:
        The expected Q results.
    """
    extra_tables: Set[str] = {'reviews_reviewrequest_target_groups'}

    prep_equeries: ExpectedQueries = []

    if isinstance(to_user, User):
        to_username = to_user.username
    else:
        assert isinstance(to_user, str)

        to_username = to_user
        to_user = (
            User.objects
            .filter(username=to_user)
            .only('pk')
            .get()
        )

        prep_equeries += [
            {
                '__note__': f'Fetching user {to_username}',
                'model': User,
                'where': Q(username=to_username),
            },
        ]

    kwargs['extra_query'] = Q(target_groups__in=[
        _group.pk
        for _group in target_groups
    ])

    q_result = get_review_requests_accessible_q(**kwargs)

    prep_equeries += q_result.get('prep_equeries', []) + [
        {
            '__note__': (
                f'Fetch the list of user "{to_username}"\'s review groups'
            ),
            'model': Group,
            'num_joins': 1,
            'values_select': ('pk',),
            'tables': {
                'reviews_group',
                'reviews_group_users',
            },
            'where': Q(users__id=to_user.pk),
        },
    ]

    q_result['tables'].update(extra_tables)
    q_result['prep_equeries'] = prep_equeries

    return q_result


def get_review_requests_to_or_from_user_q(
    *,
    to_or_from_user: Union[str, User],
    to_or_from_user_profile: Optional[Profile],
    target_groups: Sequence[Group] = [],
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQResult:
    """Return a Q expression for review requests to/from a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_or_from_user()
    <reviewboard.reviews.managers.ReviewRequestManager.to_or_from_user>`.

    It wraps :py:func:`get_review_requests_accessible_q` and takes all the same
    arguments.

    The ``prep_equeries`` key of the result must immediately precede any
    Usage of the resulting Q-expression.

    Version Added:
        5.0.7

    Args:
        to_or_from_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be assigned to
            or posted from.

        to_or_from_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user that review requests would be assigned to
            or posted from.

        target_groups (list of reviewboard.reviews.models.group.Group):
            The list of review groups that the user may be a member of,
            for the query.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        dict:
        The expected Q results.
    """
    extra_tables: Set[str] = {
        'reviews_reviewrequest_target_people',
        'reviews_reviewrequest_target_groups',
    }

    target_group_ids = [
        _group.pk
        for _group in target_groups
    ]

    prep_equeries: ExpectedQueries = []

    if isinstance(to_or_from_user, User):
        to_or_from_username = to_or_from_user.username
        has_user_obj = True
        needs_profile = False
    else:
        assert isinstance(to_or_from_user, str)

        to_or_from_username = to_or_from_user
        to_or_from_user = (
            User.objects
            .filter(username=to_or_from_user)
            .only('pk')
            .get()
        )

        has_user_obj = False
        needs_profile = True

        prep_equeries += [
            {
                '__note__': f'Fetching user {to_or_from_username}',
                'model': User,
                'where': Q(username=to_or_from_username),
            },
        ]

    if to_or_from_user_profile is None:
        if has_user_obj:
            extra_query = (Q(target_people=to_or_from_user) |
                           Q(target_groups__in=target_group_ids) |
                           Q(submitter=to_or_from_user))
        else:
            extra_tables.add('auth_user')
            extra_query = (Q(target_people=to_or_from_user) |
                           Q(target_groups__in=target_group_ids) |
                           Q(submitter__username=to_or_from_username))
    else:
        extra_tables.add('accounts_profile_starred_review_requests')

        if has_user_obj:
            extra_query = (Q(target_people=to_or_from_user) |
                           Q(target_groups__in=target_group_ids) |
                           Q(starred_by=to_or_from_user_profile) |
                           Q(submitter=to_or_from_user))
        else:
            extra_tables.add('auth_user')
            extra_query = (Q(target_people=to_or_from_user) |
                           Q(target_groups__in=target_group_ids) |
                           Q(starred_by=to_or_from_user_profile) |
                           Q(submitter__username=to_or_from_username))

    kwargs['extra_query'] = extra_query

    q_result = get_review_requests_accessible_q(**kwargs)

    prep_equeries += q_result.get('prep_equeries', []) + [
        {
            '__note__': (
                f'Fetch the list of user "{to_or_from_username}"\'s review '
                f'groups'
            ),
            'model': Group,
            'num_joins': 1,
            'values_select': ('pk',),
            'tables': {
                'reviews_group',
                'reviews_group_users',
            },
            'where': Q(users__id=to_or_from_user.pk),
        },
    ]

    if needs_profile:
        prep_equeries += get_user_profile_equeries(user=to_or_from_user)

    q_result['tables'].update(extra_tables)
    q_result['prep_equeries'] = prep_equeries

    return q_result


###########################
# Expected Query utilties #
###########################

def get_review_requests_accessible_prep_equeries(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    needs_local_site_profile_query: bool = True,
    needs_user_permission_queries: bool = True,
) -> ExpectedQueries:
    """Return expected review request accessibility preparation queries.

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

            Set to ``False`` if this should be cached at this point.

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
        equeries += get_repositories_accessible_ids_equeries(
            user=user,
            local_site=local_site,
            visible_only=False)
        equeries += get_review_groups_accessible_ids_equeries(
            user=user,
            local_site=local_site,
            visible_only=False,
            needs_local_site_profile_query=needs_local_site_profile_query,
            needs_user_permission_queries=needs_user_permission_queries)

    return equeries


def get_review_requests_accessible_equeries(
    *,
    distinct: bool = True,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for accessible review requests.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.public()
    <reviewboard.reviews.managers.ReviewRequestManager.public>`.

    Version Added:
        5.0.7

    Args:
        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    kwargs['filter_private'] = True

    q_result = get_review_requests_accessible_q(**kwargs)
    q_tables = q_result['tables']

    equeries = q_result.get('prep_equeries', [])
    equeries += [
        {
            '__note__': 'Fetch accessible review requests',
            'distinct': distinct,
            'num_joins': len(q_tables) - 1,
            'model': ReviewRequest,
            'tables': q_tables,
            'where': q_result['q'],
        }
    ]

    return equeries


def get_review_requests_from_user_equeries(
    *,
    from_user: Union[str, User],
    distinct: bool = True,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for review requests from a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.from_user()
    <reviewboard.reviews.managers.ReviewRequestManager.from_user>`.

    Version Added:
        5.0.7

    Args:
        from_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be published from
            for the query.

        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_review_requests_from_user_q(from_user=from_user,
                                               **kwargs)

    if isinstance(from_user, User):
        username = from_user.username
    else:
        username = from_user

    equeries = q_result.get('prep_equeries', [])
    equeries += [
        {
            '__note__': f'Fetch review requests from user "{username}"',
            'distinct': distinct,
            'num_joins': 1,
            'model': ReviewRequest,
            'tables': {
                'auth_user',
                'reviews_reviewrequest',
            },
            'where': q_result['q'],
        }
    ]

    return equeries


def get_review_requests_to_group_equeries(
    *,
    to_group_name: str,
    distinct: bool = True,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for review requests to a group.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_group()
    <reviewboard.reviews.managers.ReviewRequestManager.to_group>`.

    Version Added:
        5.0.7

    Args:
        to_group (str):
            The name of the group that review requests would be assigned to.

        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_review_requests_to_group_q(to_group_name=to_group_name,
                                              **kwargs)
    q_tables = q_result['tables']

    equeries = q_result.get('prep_equeries', [])
    equeries += [
        {
            '__note__': f'Fetch review requests to group "{to_group_name}"',
            'distinct': distinct,
            'num_joins': len(q_tables) - 1,
            'model': ReviewRequest,
            'tables': q_tables,
            'where': q_result['q'],
        }
    ]

    return equeries


def get_review_requests_to_user_equeries(
    *,
    to_user: Union[str, User],
    to_user_profile: Optional[Profile] = None,
    target_groups: Sequence[Group] = [],
    distinct: bool = True,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for review requests to a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_user()
    <reviewboard.reviews.managers.ReviewRequestManager.to_user>`.

    Version Added:
        5.0.7

    Args:
        to_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be assigned to.

        to_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user that review requests would be assigned to.

        target_groups (list of reviewboard.reviews.models.group.Group):
            The list of review groups that the user may be a member of,
            for the query.

        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_review_requests_to_user_q(
        to_user=to_user,
        to_user_profile=to_user_profile,
        target_groups=target_groups,
        **kwargs)
    q_tables = q_result['tables']

    if isinstance(to_user, User):
        username = to_user.username
    else:
        username = to_user

    equeries = q_result.get('prep_equeries', [])
    equeries += [
        {
            '__note__': f'Fetch review requests to user "{username}"',
            'distinct': distinct,
            'num_joins': len(q_tables) - 1,
            'model': ReviewRequest,
            'tables': q_tables,
            'where': q_result['q'],
        }
    ]

    return equeries


def get_review_requests_to_user_directly_equeries(
    *,
    to_user: Union[str, User],
    to_user_profile: Optional[Profile] = None,
    distinct: bool = True,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for review requests directly to a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_user_directly()
    <reviewboard.reviews.managers.ReviewRequestManager.to_user_directly>`.

    Version Added:
        5.0.7

    Args:
        to_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be assigned to.

        to_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user that review requests would be assigned to.

        target_groups (list of reviewboard.reviews.models.group.Group):
            The list of review groups that the user may be a member of,
            for the query.

        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_review_requests_to_user_directly_q(
        to_user=to_user,
        to_user_profile=to_user_profile,
        **kwargs)
    q_tables = q_result['tables']

    if isinstance(to_user, User):
        username = to_user.username
    else:
        username = to_user

    equeries = q_result.get('prep_equeries', [])
    equeries += [
        {
            '__note__': f'Fetch review requests to user "{username}"',
            'distinct': distinct,
            'num_joins': len(q_tables) - 1,
            'model': ReviewRequest,
            'tables': q_tables,
            'where': q_result['q'],
        }
    ]

    return equeries


def get_review_requests_to_user_groups_equeries(
    *,
    to_user: Union[str, User],
    to_user_profile: Optional[Profile] = None,
    target_groups: Sequence[Group] = [],
    distinct: bool = True,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for review requests to a user's groups.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_user_groups()
    <reviewboard.reviews.managers.ReviewRequestManager.to_user_groups>`.

    Version Added:
        5.0.7

    Args:
        to_user (str or django.contrib.auth.models.User):
            The username or user belonging to a group that review requests
            would be assigned to.

        to_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user belonging to a group that review requests
            would be assigned to.

        target_groups (list of reviewboard.reviews.models.group.Group):
            The list of review groups that the user may be a member of,
            for the query.

        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_review_requests_to_user_groups_q(
        to_user=to_user,
        to_user_profile=to_user_profile,
        target_groups=target_groups,
        **kwargs)
    q_tables = q_result['tables']

    if isinstance(to_user, User):
        username = to_user.username
    else:
        username = to_user

    equeries = q_result.get('prep_equeries', [])
    equeries += [
        {
            '__note__': f'Fetch review requests to user "{username}"',
            'distinct': distinct,
            'num_joins': len(q_tables) - 1,
            'model': ReviewRequest,
            'tables': q_tables,
            'where': q_result['q'],
        }
    ]

    return equeries


def get_review_requests_to_or_from_user_equeries(
    *,
    to_or_from_user: Union[str, User],
    to_or_from_user_profile: Optional[Profile] = None,
    target_groups: Sequence[Group] = [],
    distinct: bool = True,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for review requests to/from a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.to_user()
    <reviewboard.reviews.managers.ReviewRequestManager.to_user>`.

    Version Added:
        5.0.7

    Args:
        to_or_from_user (str or django.contrib.auth.models.User):
            The username or user that review requests would be assigned to
            or posted from.

        to_or_from_user_profile (reviewboard.accounts.models.Profile):
            The profile of the user that review requests would be assigned to
            or posted from.

        target_groups (list of reviewboard.reviews.models.group.Group):
            The list of review groups that the user may be a member of,
            for the query.

        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_review_requests_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_review_requests_to_or_from_user_q(
        to_or_from_user=to_or_from_user,
        to_or_from_user_profile=to_or_from_user_profile,
        target_groups=target_groups,
        **kwargs)
    q_tables = q_result['tables']

    if isinstance(to_or_from_user, User):
        username = to_or_from_user.username
    else:
        username = to_or_from_user

    equeries = q_result.get('prep_equeries', [])
    equeries += [
        {
            '__note__': f'Fetch review requests to user "{username}"',
            'distinct': distinct,
            'num_joins': len(q_tables) - 1,
            'model': ReviewRequest,
            'tables': q_tables,
            'where': q_result['q'],
        }
    ]

    return equeries
