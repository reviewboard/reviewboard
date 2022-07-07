"""Managers for reviewboard.site.models.

Version Added:
    5.0
"""

from uuid import uuid4

from django.core.cache import cache
from django.db.models import Count, Manager, Q
from djblets.cache.backend import cache_memoize, make_cache_key


class LocalSiteManager(Manager):
    """Manager for LocalSite models.

    This provides querying and statistics calculations for Local Sites.

    Version Added:
        5.0
    """

    _STATS_CACHE_KEY = 'stats-localsites'

    def get_stats(self):
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
            dict:
            The statistics, containing:

            Keys:
                private_count (int):
                    The total number of private LocalSites in the database.

                public_count (int):
                    The total number of public LocalSites in the database.

                state_uuid (str):
                    A UUID specific to the current state generation. This can
                    be used to help with other caching and invalidation.

                total_count (int):
                    The total number of LocalSites in the database.
        """
        def _gen_stats():
            counts = self.aggregate(
                total=Count('*'),
                public_count=Count('public', filter=Q(public=True)))
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

    def get_local_site_acl_stats(self, local_site_or_id):
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
            dict:
            The statistics, containing:

            Keys:
                admin_count (int):
                    The number of administrators on the site.

                public (bool):
                    Whether the Local Site is public.

                user_count (int):
                    The number of users on the site.

                state_uuid (str):
                    A UUID specific to the current user/admin membership and
                    public state.
        """
        def _gen_stats():
            if isinstance(local_site_or_id, int):
                try:
                    local_site = (
                        self.filter(pk=local_site_or_id)
                        .only('public')
                        .get()
                    )
                except self.model.DoesNotExist:
                    return None
            else:
                local_site = local_site_or_id

            user_count = (
                self.model.users.through.objects
                .filter(localsite=local_site.pk)
                .count()
            )

            admin_count = (
                self.model.admins.through.objects
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

    def has_local_sites(self):
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

    def has_public_local_sites(self):
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

    def has_private_local_sites(self):
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

    def invalidate_stats_cache(self):
        """Invalidate the cache for LocalSite statistics.

        Version Added:
            5.0
        """
        cache.delete(make_cache_key(self._STATS_CACHE_KEY))

    def invalidate_local_site_acl_stats_cache(self, local_site_or_id):
        """Invalidate the cache for LocalSit-specific ACL statistics.

        Version Added:
            5.0

        Args:
            local_site_or_id (reviewboard.site.models.LocalSite or int):
                The Local Site instance or ID.
        """
        cache.delete(make_cache_key(
            self._make_local_site_stats_acl_cache_key(local_site_or_id)))

    def build_q(self, local_site, allow_all=True,
                local_site_field='local_site'):
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
            AssertionError:
                Incompatible sets of arguments were provided.
        """
        ALL = self.model.ALL

        assert allow_all or local_site is not ALL

        if local_site is ALL:
            return Q()

        if not self.has_local_sites():
            assert local_site in (None, ALL), (
                'The server has no LocalSites, but %r was passed'
                % local_site)

            return Q()

        return Q(local_site=local_site)

    def _make_local_site_stats_acl_cache_key(self, local_site_or_id):
        """Return a cache key for per-Local Site ACL stats.

        Args:
            local_site_or_id (reviewboard.site.models.LocalSite or int):
                The Local Site instance or ID.

        Returns:
            str:
            The new cache key.
        """
        if isinstance(local_site_or_id, self.model):
            local_site_id = local_site_or_id.pk
        else:
            assert isinstance(local_site_or_id, int)

            local_site_id = local_site_or_id

        return 'local-site-acl-stats-%s' % local_site_id
