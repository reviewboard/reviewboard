"""Managers for reviewboard.site.models.

Version Added:
    5.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict
from uuid import uuid4

from django.core.cache import cache
from django.db.models import Count, Manager, Q
from djblets.cache.backend import cache_memoize, make_cache_key
from housekeeping.functions import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard10_0Warning

if TYPE_CHECKING:
    from reviewboard.site.models import AnyOrAllLocalSites, LocalSite


class LocalSiteStatsData(TypedDict):
    """Statistics on Local Sites.

    This includes information on how many Local Sites are in the database,
    total and broken down by public/private access.

    A state UUID is included that will be regenerated every time this data
    is updated. This can be used as a component in other cache keys, ETags,
    or for other unique identifiers in order to help ensure that information
    built on these results are fresh.

    Version Added:
        8.0
    """

    #: The total number of private LocalSites in the database.
    private_count: int

    #: The total number of public LocalSites in the database.
    public_count: int

    #: A UUID specific to the current state generation.
    #:
    #: This can be used to help with other caching and invalidation.
    state_uuid: str

    #: The total number of LocalSites in the database.
    total_count: int


class LocalSiteACLStatsData(TypedDict):
    """Statistics on Local Site access controls.

    This includes information on how many users and administrators are on
    the Local Site and whether the site is public or private.

    A state UUID is included that will be regenerated every time this data
    is updated. This can be used as a component in other cache keys, ETags,
    or for other unique identifiers in order to help ensure that information
    built on these results are fresh.

    Version Added:
        8.0
    """

    #: The number of administrators on the Local Site.
    admin_count: int

    #: Whether the Local Site is public.
    public: bool

    #: A UUID specific to the current state generation.
    #:
    #: This can be used to help with other caching and invalidation.
    state_uuid: str

    #: The number of users on the Local Site.
    user_count: int


class LocalSiteManager(Manager['LocalSite']):
    """Manager for LocalSite models.

    This provides querying and statistics calculations for Local Sites.

    Version Added:
        5.0
    """

    _STATS_CACHE_KEY = 'stats-localsites'

    def get_stats(self) -> LocalSiteStatsData:
        """Return statistics on the LocalSites in the database.

        This will include the total number of :py:class:`LocalSites
        <reviewboard.site.models.LocalSite>`, the number of public LocalSites,
        and the number of private LocalSites.

        This information is cached to avoid querying the database any more
        often than necessary. Statistics will be re-calculated if they fall
        out of cache or if invalidated by saving a LocalSite.

        Version Added:
            5.0

        Returns:
            LocalSiteStatsData:
            The Local Site statistics data.
        """
        def _gen_stats() -> LocalSiteStatsData:
            counts = self.aggregate(
                total=Count('*'),
                public_count=Count('public', filter=Q(public=True)),
            )
            count = counts['total']
            public_count = counts['public_count']
            private_count = count - public_count

            return {
                'private_count': private_count,
                'public_count': public_count,
                'state_uuid': str(uuid4()),
                'total_count': count,
            }

        return cache_memoize(self._STATS_CACHE_KEY, _gen_stats)

    def get_local_site_acl_stats(
        self,
        local_site_or_id: LocalSite | int,
    ) -> LocalSiteACLStatsData | None:
        """Return LocalSite-specific ACL statistics.

        This will include the number of users and administrators on the
        :py:class:`reviewboard.site.models.LocalSite`, along with a UUID
        representing the current membership state.

        This can be used to make determinations on whether to query for
        certain information on a Local Site, and as components in other
        cacheable state.

        This information is cached to avoid querying the database any more
        often than necessary. Statistics will be re-calculated if they fall
        out of cache or if invalidated by altering users or administrators.

        Version Added:
            5.0

        Args:
            local_site_or_id (reviewboard.site.models.LocalSite or int):
                The Local Site instance or ID.

        Returns:
            LocalSiteACLStatsData:
            The Local Site ACL statistics data, or ``None`` if the site
            could not be found.
        """
        def _gen_stats() -> LocalSiteACLStatsData | None:
            model = self.model

            if isinstance(local_site_or_id, int):
                try:
                    local_site = (
                        self.filter(pk=local_site_or_id)
                        .only('public')
                        .get()
                    )
                except model.DoesNotExist:
                    return None
            else:
                local_site = local_site_or_id

            user_count = (
                model.users.through.objects
                .filter(localsite=local_site.pk)
                .count()
            )

            admin_count = (
                model.admins.through.objects
                .filter(localsite=local_site.pk)
                .count()
            )

            return {
                'admin_count': admin_count,
                'public': local_site.public,
                'user_count': user_count,
                'state_uuid': str(uuid4()),
            }

        return cache_memoize(
            self._make_local_site_stats_acl_cache_key(local_site_or_id),
            _gen_stats)

    def has_local_sites(self) -> bool:
        """Return whether there are LocalSites in the database.

        This will optimistically fetch this information from cached
        statistics, only querying the database if necessary.

        Version Added:
            5.0

        Returns:
            bool:
            ``True`` if there are LocalSites. ``False`` if there are not.
        """
        return self.get_stats().get('total_count', 0) > 0

    def has_public_local_sites(self) -> bool:
        """Return whether there are public LocalSites in the database.

        This will optimistically fetch this information from cached
        statistics, only querying the database if necessary.

        Version Added:
            5.0

        Returns:
            bool:
            ``True`` if there are public LocalSites. ``False`` if there are
            not.
        """
        return self.get_stats().get('public_count', 0) > 0

    def has_private_local_sites(self) -> bool:
        """Return whether there are private LocalSites in the database.

        This will optimistically fetch this information from cached
        statistics, only querying the database if necessary.

        Version Added:
            5.0

        Returns:
            bool:
            ``True`` if there are private LocalSites. ``False`` if there are
            not.
        """
        return self.get_stats().get('private_count', 0) > 0

    def invalidate_stats_cache(self) -> None:
        """Invalidate the cache for LocalSite statistics.

        Version Added:
            5.0
        """
        cache.delete(make_cache_key(self._STATS_CACHE_KEY))

    def invalidate_local_site_acl_stats_cache(
        self,
        local_site_or_id: LocalSite | int,
    ) -> None:
        """Invalidate the cache for LocalSite-specific ACL statistics.

        Version Added:
            5.0

        Args:
            local_site_or_id (reviewboard.site.models.LocalSite or int):
                The Local Site instance or ID.
        """
        cache.delete(make_cache_key(
            self._make_local_site_stats_acl_cache_key(local_site_or_id)))

    @deprecate_non_keyword_only_args(RemovedInReviewBoard10_0Warning)
    def build_q(
        self,
        local_site: AnyOrAllLocalSites,
        *,
        allow_all: bool = True,
        local_site_field: str = 'local_site',
    ) -> Q:
        """Return a Q object for matching a Local Site.

        This is used to conditionally build a Q object for filtering by
        Local Site.

        If Local Sites aren't used on the server, or if ``local_site`` is
        :py:attr:`LocalSite.ALL <reviewboard.site.models.LocalSite.ALL>`,
        The Q object will be empty (and will be optimized out of the query).

        Otherwise, a standard Q object matching ``local_site`` will be
        returned.

        This will take care of asserting that compatible arguments are
        provided, so there are no surprises.

        Version Changed:
            8.0:
            ``allow_all`` and ``local_site_field`` must now be provided
            as keyword-only arguments. Support for providing these as
            positional arguments is deprecated and will be removed in
            Review Board 10.

        Version Added:
            5.0

        Args:
            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                The Local Site value used to filter the queryset, if
                Local Sites are used on the server.

            allow_all (bool, optional):
                Whether :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>` is allowed as a
                value.

            local_site_field (str, optional):
                The name of the field to query. This can be set if a different
                field name or spanned relation (e.g., ``myrel__local_site=``)
                is required.

        Returns:
            django.db.models.Q:
            The resulting query object.

        Raises:
            ValueError:
                Incompatible sets of arguments were provided.
        """
        ALL = self.model.ALL

        if not allow_all and local_site is ALL:
            raise ValueError(
                'allow_all=False was provided, but local_site=LocalSite.ALL '
                'was passed.'
            )

        if local_site is ALL:
            return Q()

        if not self.has_local_sites():
            if local_site not in (None, ALL):
                raise ValueError(
                    f'The server has no LocalSites, but {local_site!r} was '
                    f'passed.'
                )

            return Q()

        return Q(**{local_site_field: local_site})

    def _make_local_site_stats_acl_cache_key(
        self,
        local_site_or_id: LocalSite | int,
    ) -> str:
        """Return a cache key for per-Local Site ACL stats.

        Version Changed:
            8.0:
            This now returns a :py:exc:`ValueError` for an invalid
            ``local_site_or_id`` instead of asserting.

        Args:
            local_site_or_id (reviewboard.site.models.LocalSite or int):
                The Local Site instance or ID.

        Returns:
            str:
            The new cache key.

        Raises:
            ValueError:
                An invalid value for ``local_site_or_id`` was provided.
        """
        if isinstance(local_site_or_id, self.model):
            local_site_id = local_site_or_id.pk
        elif isinstance(local_site_or_id, int):
            local_site_id = local_site_or_id
        else:
            raise ValueError(
                f'Unsupported value provided for local_site_or_id: '
                f'{local_site_or_id!r}'
            )

        return f'local-site-acl-stats-{local_site_id}'
