"""Unit tests for reviewboard.site.managers.LocalSiteManager."""

from uuid import UUID, uuid4

import kgb

from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class LocalSiteManagerTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.site.managers.LocalSiteManager."""

    def test_get_stats_with_no_sites(self):
        """Testing LocalSiteManager.get_stats with no LocalSites"""
        uuids = self._pregenerate_cache_state_uuids(1)

        # 1 query:
        #
        # 1. Total LocalSite count
        with self.assertNumQueries(1):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 0,
            })

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 0,
            })

    def test_get_stats_with_sites(self):
        """Testing LocalSiteManager.get_stats with LocalSites"""
        uuids = self._pregenerate_cache_state_uuids(2)

        self.create_local_site(name='test-site-1')
        self.create_local_site(name='test-site-2')
        self.create_local_site(name='test-site-3',
                               public=True)

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 2,
                'public_count': 1,
                'state_uuid': uuids[0],
                'total_count': 3,
            })

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 2,
                'public_count': 1,
                'state_uuid': uuids[0],
                'total_count': 3,
            })

    def test_get_stats_after_private_save(self):
        """Testing LocalSiteManager.get_stats after private LocalSite.save"""
        uuids = self._pregenerate_cache_state_uuids(2)

        # 1 query:
        #
        # 1. Total LocalSite count
        with self.assertNumQueries(1):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 0,
            })

        self.create_local_site(name='test-site-1')

        # The second query should hit cache.
        with self.assertNumQueries(2):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 1,
                'public_count': 0,
                'state_uuid': uuids[1],
                'total_count': 1,
            })

    def test_get_stats_after_public_save(self):
        """Testing LocalSiteManager.get_stats after public LocalSite.save"""
        uuids = self._pregenerate_cache_state_uuids(2)

        # 1 query:
        #
        # 1. Total LocalSite count
        with self.assertNumQueries(1):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 0,
            })

        self.create_local_site(name='test-site-1',
                               public=True)

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 1,
                'state_uuid': uuids[1],
                'total_count': 1,
            })

    def test_get_stats_after_public_state_save(self):
        """Testing LocalSiteManager.get_stats after private -> public
        LocalSite.save
        """
        uuids = self._pregenerate_cache_state_uuids(2)

        local_site = self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 1,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 1,
            })

        local_site.public = True
        local_site.save(update_fields=('public',))

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 1,
                'state_uuid': uuids[1],
                'total_count': 1,
            })

    def test_get_stats_after_delete(self):
        """Testing LocalSiteManager.get_stats after LocalSite.delete"""
        uuids = self._pregenerate_cache_state_uuids(2)

        local_site = self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 1,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 1,
            })

        local_site.delete()

        # 1 query:
        #
        # 1. Total LocalSite count
        with self.assertNumQueries(1):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[1],
                'total_count': 0,
            })

    def test_has_local_sites_with_no_sites(self):
        """Testing LocalSiteManager.has_local_sites with no LocalSites"""
        # 2 query:
        #
        # 1. Total LocalSite count
        with self.assertNumQueries(1):
            self.assertFalse(LocalSite.objects.has_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertFalse(LocalSite.objects.has_local_sites())

    def test_has_local_sites_with_public_sites(self):
        """Testing LocalSiteManager.has_local_sites with public LocalSites"""
        self.create_local_site(name='test-site-1',
                               public=True)

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertTrue(LocalSite.objects.has_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertTrue(LocalSite.objects.has_local_sites())

    def test_has_local_sites_with_private_sites(self):
        """Testing LocalSiteManager.has_local_sites with private LocalSites"""
        self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertTrue(LocalSite.objects.has_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertTrue(LocalSite.objects.has_local_sites())

    def test_has_public_local_sites_with_no_public_sites(self):
        """Testing LocalSiteManager.has_public_local_sites with no public
        LocalSites
        """
        self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertFalse(LocalSite.objects.has_public_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertFalse(LocalSite.objects.has_public_local_sites())

    def test_has_public_local_sites_with_public_sites(self):
        """Testing LocalSiteManager.has_public_local_sites with public
        LocalSites
        """
        self.create_local_site(name='test-site-1',
                               public=True)

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertTrue(LocalSite.objects.has_public_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertTrue(LocalSite.objects.has_public_local_sites())

    def test_has_private_local_sites_with_no_private_sites(self):
        """Testing LocalSiteManager.has_private_local_sites with no private
        LocalSites
        """
        self.create_local_site(name='test-site-1',
                               public=True)

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. private LocalSite count
        with self.assertNumQueries(2):
            self.assertFalse(LocalSite.objects.has_private_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertFalse(LocalSite.objects.has_private_local_sites())

    def test_has_private_local_sites_with_private_sites(self):
        """Testing LocalSiteManager.has_private_local_sites with private
        LocalSites
        """
        self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. private LocalSite count
        with self.assertNumQueries(2):
            self.assertTrue(LocalSite.objects.has_private_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertTrue(LocalSite.objects.has_private_local_sites())

    def test_invalidate_stats_cache(self):
        """Testing LocalSiteManager.invalidate_stats_cache"""
        self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertTrue(LocalSite.objects.has_local_sites())

        LocalSite.objects.invalidate_stats_cache()

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertNumQueries(2):
            self.assertTrue(LocalSite.objects.has_local_sites())

    def _pregenerate_cache_state_uuids(self, count):
        """Pre-generate a list of UUIDs for state_uuid cache information.

        This will generate a list, ensure :py:func:`uuid.uuid4` returns them
        in the order called, and returns them for reference.

        Args:
            count (int):
                The number of UUIDs to pre-generate.

        Returns:
            list of str:
            The list of pre-generated UUIDs.
        """
        uuids = [
            '00000000-0000-0000-0000-%012d' % _i
            for _i in range(count)
        ]

        self.spy_on(uuid4, op=kgb.SpyOpReturnInOrder([
            UUID(_uuid)
            for _uuid in uuids
        ]))

        return uuids
