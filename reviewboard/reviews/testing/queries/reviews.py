"""Testing utilities for building expected queries for reviews.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Set, TYPE_CHECKING, Union

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q

from reviewboard.reviews.models import Review
from reviewboard.reviews.testing.queries.review_groups import \
    get_review_groups_accessible_ids_equeries
from reviewboard.scmtools.testing.queries import \
    get_repositories_accessible_ids_equeries
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries
    from typing_extensions import NotRequired, TypedDict, Unpack

    from reviewboard.site.models import AnyOrAllLocalSites
    from reviewboard.testing.queries.base import ExpectedQResult

    class _AccessibleKwargs(TypedDict):
        user: Union[AnonymousUser, User]
        local_site: NotRequired[AnyOrAllLocalSites]
        has_local_sites_in_db: NotRequired[bool]
        filter_private: NotRequired[bool]
        status: NotRequired[Optional[str]]
        public: NotRequired[Optional[bool]]
        base_reply_to: NotRequired[Optional[Review]]
        extra_query: NotRequired[Q]
        accessible_repository_ids: NotRequired[Sequence[int]]
        accessible_review_group_ids: NotRequired[Sequence[int]]
        has_view_invite_only_groups_perm: NotRequired[bool]
        needs_local_site_profile_query: NotRequired[bool]


##########################
# Q-expression utilities #
##########################

def get_reviews_accessible_q(
    *,
    user: Union[AnonymousUser, User],
    local_site: AnyOrAllLocalSites = None,
    has_local_sites_in_db: bool = False,
    filter_private: bool = False,
    status: Optional[str] = None,
    public: Optional[bool] = None,
    base_reply_to: Optional[Review] = None,
    extra_query: Q = Q(),
    accessible_repository_ids: Sequence[int] = [],
    accessible_review_group_ids: Sequence[int] = [],
    has_view_invite_only_groups_perm: bool = False,
    needs_local_site_profile_query: bool = False,
) -> ExpectedQResult:
    """Return a Q expression for accessible review queries.

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

        filter_private (bool, optional):
            Whether review requests would be filtered using ACL checks.

        status (str, optional):
            The optional status that would be used in the query.

        public (bool, optional):
            The optional public state to match in queries.

        base_reply_to (reviewboard.reviews.models.review.Review, optional):
            Any review that this results would be in reply to.

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

        if filter_private and not is_superuser:
            prep_equeries += get_repositories_accessible_ids_equeries(
                user=user,
                local_site=local_site,
                visible_only=False)
            prep_equeries += get_review_groups_accessible_ids_equeries(
                user=user,
                local_site=local_site,
                visible_only=False,
                needs_local_site_profile_query=needs_local_site_profile_query)

    # This is intended to be verbose, to ensure we're matching exactly the
    # queries we expect. We want to minimize building of queries.
    #
    # That said, to keep this maintainable, query is built in 2 stages:
    #
    # 1. Initial caller-requested access control/visibility queries
    # 2. Access control filter queries
    init_q: Q
    access_q: Q
    tables: Set[str] = {'reviews_review'}
    join_types: Dict[str, str] = {}

    # Stage 1: Initial filtering Q-expression.
    if status:
        tables.add('reviews_reviewrequest')
        join_types['reviews_reviewrequest'] = 'INNER JOIN'

        if include_local_site_q:
            init_q = (Q(base_reply_to=base_reply_to) &
                      Q(review_request__status=status) &
                      Q(review_request__local_site=local_site) &
                      extra_query)
        else:
            init_q = (Q(base_reply_to=base_reply_to) &
                      Q(review_request__status=status) &
                      extra_query)
    else:
        if include_local_site_q:
            tables.add('reviews_reviewrequest')
            join_types['reviews_reviewrequest'] = 'INNER JOIN'

            init_q = (Q(base_reply_to=base_reply_to) &
                      Q(review_request__local_site=local_site) &
                      extra_query)
        else:
            init_q = (Q(base_reply_to=base_reply_to) &
                      extra_query)

    # Stage 2: Access control Q-expression.
    if filter_private:
        if is_superuser:
            if public is None:
                access_q = Q()
            else:
                access_q = Q(public=public)
        elif is_authenticated:
            if public is None:
                tables.update({
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                })
                join_types.update({
                    'reviews_reviewrequest': 'INNER JOIN',
                    'reviews_reviewrequest_target_groups': 'LEFT OUTER JOIN',
                    'reviews_reviewrequest_target_people': 'LEFT OUTER JOIN',
                })

                access_q = (
                    Q(user=user) |
                    (Q(public=True) &
                     (Q(review_request__repository=None) |
                      Q(review_request__repository__in=(
                          accessible_repository_ids))) &
                     (Q(review_request__target_people=user) |
                      Q(review_request__target_groups=None) |
                      Q(review_request__target_groups__in=(
                          accessible_review_group_ids))))
                )
            elif public is True:
                tables.update({
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                })
                join_types.update({
                    'reviews_reviewrequest': 'INNER JOIN',
                    'reviews_reviewrequest_target_groups': 'LEFT OUTER JOIN',
                    'reviews_reviewrequest_target_people': 'LEFT OUTER JOIN',
                })

                access_q = (
                    Q(public=True) &
                    (Q(review_request__repository=None) |
                     Q(review_request__repository__in=(
                         accessible_repository_ids))) &
                    (Q(review_request__target_people=user) |
                     Q(review_request__target_groups=None) |
                     Q(review_request__target_groups__in=(
                         accessible_review_group_ids)))
                )
            elif public is False:
                access_q = (Q(public=False) &
                            Q(user=user))
        else:
            assert user.is_anonymous
            assert public is not False, (
                "get_review_accessible_q can't be passed with public=False, "
                "filter_private, and anonymous users. ReviewManager._query "
                "supports this, but it cannot be expressed as a Q(). Make "
                "sure to check this condition manually in tests instead."
            )

            tables.update({
                'reviews_group',
                'reviews_reviewrequest',
                'reviews_reviewrequest_target_groups',
                'scmtools_repository',
            })
            join_types.update({
                'reviews_group': 'LEFT OUTER JOIN',
                'reviews_reviewrequest': 'INNER JOIN',
                'reviews_reviewrequest_target_groups': 'LEFT OUTER JOIN',
                'scmtools_repository': 'LEFT OUTER JOIN',
            })

            access_q = (
                (Q(review_request__repository=None) |
                 Q(review_request__repository__public=True)) &
                (Q(review_request__target_groups=None) |
                 Q(review_request__target_groups__invite_only=False)) &
                Q(public=True)
            )
    else:
        if public is None:
            access_q = Q()
        else:
            access_q = Q(public=public)

    return {
        'join_types': join_types,
        'prep_equeries': prep_equeries,
        'q': init_q & access_q,
        'tables': tables,
    }


def get_reviews_from_user_q(
    *,
    from_user: Union[str, User],
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQResult:
    """Return a Q expression for accessible reviews from a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.from_user()
    <reviewboard.reviews.managers.ReviewRequestManager.from_user>`.

    Version Added:
        5.0.7

    Args:
        from_user (str or django.contrib.auth.models.User):
            The username or user that the reviews will be from.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_reviews_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    extra_tables: Set[str] = set()
    extra_join_types: Dict[str, str] = {}

    if isinstance(from_user, User):
        extra_query = Q(user=from_user)
    else:
        assert isinstance(from_user, str)

        extra_query = Q(user__username=from_user)
        extra_tables.add('auth_user')
        extra_join_types['auth_user'] = 'INNER JOIN'

    kwargs['extra_query'] = extra_query

    q_result = get_reviews_accessible_q(**kwargs)
    q_result.setdefault('join_types', {}).update(extra_join_types)
    q_result['tables'].update(extra_tables)

    return q_result


###########################
# Expected Query utilties #
###########################

def get_reviews_accessible_equeries(
    *,
    distinct: bool = False,
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for accessible reviews.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.accessible()
    <reviewboard.reviews.managers.ReviewRequestManager.accessible>`.

    Version Added:
        5.0.7

    Args:
        distinct (bool, optional):
            Whether this is a distinct query.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_reviews_accessible_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    kwargs.setdefault('filter_private', True)

    q_result = get_reviews_accessible_q(**kwargs)
    q_tables = q_result['tables']

    return q_result.get('prep_equeries', []) + [
        {
            '__note__': 'Fetch accessible reviews',
            'distinct': distinct,
            'join_types': q_result.get('join_types', {}),
            'num_joins': len(q_tables) - 1,
            'model': Review,
            'tables': q_tables,
            'where': q_result['q'],
        },
    ]


def get_reviews_from_user_equeries(
    *,
    from_user: Union[str, User],
    **kwargs: Unpack[_AccessibleKwargs],
) -> ExpectedQueries:
    """Return queries for accessible reviews from a user.

    This corresponds to a call from
    :py:meth:`ReviewRequest.objects.from_user()
    <reviewboard.reviews.managers.ReviewRequestManager.from_user>`.

    Version Added:
        5.0.7

    Args:
        from_user (str or django.contrib.auth.models.User):
            The username or user that the reviews will be from.

        **kwargs (dict, optional):
            Keyword arguments to pass to
            :py:func:`get_reviews_from_user_q`.

    Returns:
        list of dict:
        The list of expected queries.
    """
    q_result = get_reviews_from_user_q(from_user=from_user, **kwargs)
    q_tables = q_result['tables']

    if isinstance(from_user, User):
        username = from_user.username
    else:
        assert isinstance(from_user, str)

        username = from_user

    return q_result.get('prep_equeries', []) + [
        {
            '__note__': f'Fetch accessible reviews from user "{username}"',
            'distinct': False,
            'join_types': q_result.get('join_types', {}),
            'num_joins': len(q_tables) - 1,
            'model': Review,
            'tables': q_tables,
            'where': q_result['q'],
        },
    ]
