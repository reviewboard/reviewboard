"""Managers for reviewboard.site.models.

Version Added:
    5.0
"""

from uuid import uuid4

from django.core.cache import cache
from django.db.models import Manager
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
            count = self.count()

            if count > 0:
                public_count = self.filter(public=True).count()
            else:
                public_count = 0

            private_count = count - public_count

            return {
                'private_count': private_count,
                'public_count': public_count,
                'state_uuid': str(uuid4()),
                'total_count': count,
            }

        return cache_memoize(self._STATS_CACHE_KEY, _gen_stats)

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
