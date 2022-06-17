"""Unit tests for reviewboard.site.managers.LocalSiteManager."""

from uuid import UUID, uuid4

import kgb
from django.contrib.auth.models import User
from django.db.models import Count, Q

from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class LocalSiteManagerTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.site.managers.LocalSiteManager."""

    def test_get_stats_with_no_sites(self):
        """Testing LocalSiteManager.get_stats with no LocalSites"""
        uuids = self._pregenerate_cache_state_uuids(1)

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
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

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
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
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 0,
            })

        self.create_local_site(name='test-site-1')

        # The second query should hit cache.
        with self.assertQueries(queries):
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
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 0,
            })

        self.create_local_site(name='test-site-1',
                               public=True)

        # Cache should be invalidated.
        with self.assertQueries(queries):
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

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
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
        with self.assertQueries(queries):
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

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 1,
                'public_count': 0,
                'state_uuid': uuids[0],
                'total_count': 1,
            })

        local_site.delete()

        # Cache should be invalidated.
        with self.assertQueries(queries):
            self.assertEqual(LocalSite.objects.get_stats(), {
                'private_count': 0,
                'public_count': 0,
                'state_uuid': uuids[1],
                'total_count': 0,
            })

    def test_get_local_site_acl_stats_with_local_site(self):
        """Testing LocalSiteManager.get_local_site_acl_stats with LocalSite"""
        uuids = self._pregenerate_cache_state_uuids(1)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')
        user3 = self.create_user(username='user3')
        user4 = self.create_user(username='user4')
        user5 = self.create_user(username='user5')

        local_site = self.create_local_site(name='test-site-1')
        local_site.users.add(user1, user2, user3)
        local_site.admins.add(user4, user5)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            stats = LocalSite.objects.get_local_site_acl_stats(local_site)

        self.assertEqual(stats, {
            'admin_count': 2,
            'user_count': 3,
            'public': False,
            'state_uuid': uuids[0],
        })

        # The second query should hit cache.
        with self.assertNumQueries(0):
            new_stats = LocalSite.objects.get_local_site_acl_stats(local_site)

        self.assertEqual(new_stats, stats)

    def test_get_local_site_acl_stats_with_local_site_id(self):
        """Testing LocalSiteManager.get_local_site_acl_stats with LocalSite ID
        """
        uuids = self._pregenerate_cache_state_uuids(1)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')
        user3 = self.create_user(username='user3')
        user4 = self.create_user(username='user4')
        user5 = self.create_user(username='user5')

        local_site = self.create_local_site(name='test-site-1')
        local_site.users.add(user1, user2, user3)
        local_site.admins.add(user4, user5)

        # 3 queries:
        #
        # 1. Local Site instance
        # 2. User count
        # 3. Admin count
        queries = [
            {
                'model': LocalSite,
                'only_fields': {'public'},
                'where': Q(pk=local_site.pk),
            },
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            stats = LocalSite.objects.get_local_site_acl_stats(local_site.pk)

        self.assertEqual(stats, {
            'admin_count': 2,
            'user_count': 3,
            'public': False,
            'state_uuid': uuids[0],
        })

        # The second query should hit cache.
        with self.assertNumQueries(0):
            new_stats = LocalSite.objects.get_local_site_acl_stats(
                local_site.pk)

        self.assertEqual(new_stats, stats)

    def test_get_local_site_acl_stats_after_save(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after changing
        public state
        """
        uuids = self._pregenerate_cache_state_uuids(2)

        local_site = self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.public = True
        local_site.save()

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': True,
                    'state_uuid': uuids[1],
                })

    def test_get_local_site_acl_stats_after_save_update_fields_public(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        LocalSite.save(update_fields=['public'])
        """
        uuids = self._pregenerate_cache_state_uuids(2)

        local_site = self.create_local_site(name='test-site-1',
                                            public=True)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': True,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.public = False
        local_site.save(update_fields=('public',))

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[1],
                })

    def test_get_local_site_acl_stats_after_save_update_fields(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        LocalSite.save(update_fields=) without public
        """
        uuids = self._pregenerate_cache_state_uuids(1)

        local_site = self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            stats = LocalSite.objects.get_local_site_acl_stats(local_site)

        self.assertEqual(stats, {
            'admin_count': 0,
            'user_count': 0,
            'public': False,
            'state_uuid': uuids[0],
        })

        # This should NOT invalidate the cache.
        local_site.save(update_fields=('name',))

        with self.assertNumQueries(0):
            new_stats = LocalSite.objects.get_local_site_acl_stats(local_site)

        self.assertEqual(new_stats, stats)

    def test_get_local_site_acl_stats_after_delete(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        LocalSite.delete
        """
        uuids = self._pregenerate_cache_state_uuids(1)

        local_site = self.create_local_site(name='test-site-1')
        local_site_id = local_site.pk

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.delete()

        # Any subsequent fetches should return None (which will still be
        # cached).
        queries = [
            {
                'model': LocalSite,
                'only_fields': {'public'},
                'where': Q(pk=local_site_id),
            },
        ]

        with self.assertQueries(queries):
            self.assertIsNone(
                LocalSite.objects.get_local_site_acl_stats(local_site_id))

        with self.assertNumQueries(0):
            self.assertIsNone(
                LocalSite.objects.get_local_site_acl_stats(local_site_id))

    def test_get_local_site_acl_stats_after_add_user(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        adding to LocalSite.users
        """
        uuids = self._pregenerate_cache_state_uuids(3)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        local_site = self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.users.add(user1)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 1,
                    'public': False,
                    'state_uuid': uuids[1],
                })

        # Now add it on the reverse relation. This should invalidate the
        # cache.
        user2.local_site.add(local_site)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 2,
                    'public': False,
                    'state_uuid': uuids[2],
                })

    def test_get_local_site_acl_stats_after_remove_user(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        removing from LocalSite.users
        """
        uuids = self._pregenerate_cache_state_uuids(3)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        local_site = self.create_local_site(name='test-site-1')
        local_site.users.add(user1, user2)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 2,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.users.remove(user1)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 1,
                    'public': False,
                    'state_uuid': uuids[1],
                })

        # Now remove on the reverse relation. This should invalidate the
        # cache.
        user2.local_site.remove(local_site)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[2],
                })

    def test_get_local_site_acl_stats_after_clear_user(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        clearing LocalSite.users
        """
        uuids = self._pregenerate_cache_state_uuids(2)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        local_site = self.create_local_site(name='test-site-1')
        local_site.users.add(user1, user2)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 2,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.users.clear()

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[1],
                })

    def test_get_local_site_acl_stats_after_add_admin(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        adding to LocalSite.admins
        """
        uuids = self._pregenerate_cache_state_uuids(3)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        local_site = self.create_local_site(name='test-site-1')

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.admins.add(user1)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 1,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[1],
                })

        # Now add it on the reverse relation. This should invalidate the
        # cache.
        user2.local_site_admins.add(local_site)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 2,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[2],
                })

    def test_get_local_site_acl_stats_after_remove_admin(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        removing from LocalSite.admins
        """
        uuids = self._pregenerate_cache_state_uuids(3)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        local_site = self.create_local_site(name='test-site-1')
        local_site.admins.add(user1, user2)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 2,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.admins.remove(user1)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 1,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[1],
                })

        # Now remove on the reverse relation. This should invalidate the
        # cache.
        user2.local_site_admins.remove(local_site)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[2],
                })

    def test_get_local_site_acl_stats_after_clear_admins(self):
        """Testing LocalSiteManager.get_local_site_acl_stats after
        clearing LocalSite.admins
        """
        uuids = self._pregenerate_cache_state_uuids(2)

        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        local_site = self.create_local_site(name='test-site-1')
        local_site.admins.add(user1, user2)

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        queries = [
            {
                'model': LocalSite.users.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
            {
                'model': LocalSite.admins.through,
                'annotations': {'__count': Count('*')},
                'where': Q(localsite=local_site.pk),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 2,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[0],
                })

        # This should invalidate the cache.
        local_site.admins.clear()

        # 2 queries:
        #
        # 1. User count
        # 2. Admin count
        with self.assertQueries(queries):
            self.assertEqual(
                LocalSite.objects.get_local_site_acl_stats(local_site),
                {
                    'admin_count': 0,
                    'user_count': 0,
                    'public': False,
                    'state_uuid': uuids[1],
                })

    def test_has_local_sites_with_no_sites(self):
        """Testing LocalSiteManager.has_local_sites with no LocalSites"""
        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(LocalSite.objects.has_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertFalse(LocalSite.objects.has_local_sites())

    def test_has_local_sites_with_public_sites(self):
        """Testing LocalSiteManager.has_local_sites with public LocalSites"""
        self.create_local_site(name='test-site-1',
                               public=True)

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(LocalSite.objects.has_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertTrue(LocalSite.objects.has_local_sites())

    def test_has_local_sites_with_private_sites(self):
        """Testing LocalSiteManager.has_local_sites with private LocalSites"""
        self.create_local_site(name='test-site-1')

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(LocalSite.objects.has_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertTrue(LocalSite.objects.has_local_sites())

    def test_has_public_local_sites_with_no_public_sites(self):
        """Testing LocalSiteManager.has_public_local_sites with no public
        LocalSites
        """
        self.create_local_site(name='test-site-1')

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
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

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
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

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(LocalSite.objects.has_private_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertFalse(LocalSite.objects.has_private_local_sites())

    def test_has_private_local_sites_with_private_sites(self):
        """Testing LocalSiteManager.has_private_local_sites with private
        LocalSites
        """
        self.create_local_site(name='test-site-1')

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(LocalSite.objects.has_private_local_sites())

        # The second query should hit cache.
        with self.assertNumQueries(0):
            self.assertTrue(LocalSite.objects.has_private_local_sites())

    def test_invalidate_stats_cache(self):
        """Testing LocalSiteManager.invalidate_stats_cache"""
        self.create_local_site(name='test-site-1')

        # 1 query:
        #
        # 1. Total and public LocalSite counts
        queries = [
            {
                'model': LocalSite,
                'annotations': {
                    'total': Count('*'),
                    'public_count': Count('public', filter=Q(public=True)),
                },
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(LocalSite.objects.has_local_sites())

        LocalSite.objects.invalidate_stats_cache()

        # 2 queries:
        #
        # 1. Total LocalSite count
        # 2. Public LocalSite count
        with self.assertQueries(queries):
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
