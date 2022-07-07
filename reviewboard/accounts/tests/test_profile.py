"""Unit tests for reviewboard.accounts.models.Profile."""

from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile, Profile
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ProfileTests(TestCase):
    """Unit tests for reviewboard.accounts.models.Profile."""

    fixtures = ['test_users']

    def test_get_display_name_unauthenticated_public(self):
        """Testing Profile.get_display_name with a public profile"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = False

        self.assertEqual(profile.get_display_name(AnonymousUser()),
                         user.username)

    def test_get_display_name_unauthenticated_private(self):
        """Testing Profile.get_display_name for an unauthenticated user viewing
        a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(profile.get_display_name(AnonymousUser()),
                         user.username)

    def test_get_display_name_public(self):
        """Testing Profile.get_display_name for an authenticated user viewing a
        public profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = False

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='grumpy')),
            user.get_full_name())

    def test_get_display_name_private(self):
        """Testing Profile.get_display_name for an authenticated user viewing a
        private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='grumpy')),
            user.username)

    def test_get_display_name_admin_private(self):
        """Testing Profile.get_display_name for an admin viewing a private
        profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='admin')),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_get_display_name_localsite_member_private(self):
        """Testing Profile.get_display_name for a LocalSite member viewing
        a LocalSite member with a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        viewer = User.objects.get(username='grumpy')
        site = LocalSite.objects.get(pk=1)
        site.users.add(viewer)

        self.assertEqual(profile.get_display_name(viewer), user.username)

    @add_fixtures(['test_site'])
    def test_get_display_name_localsite_admin_private(self):
        """Testing Profile.get_display_name for a LocalSite admin viewing
        a LocalSite member with a private profile
        """
        user = User.objects.get(username='admin')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(
            profile.get_display_name(User.objects.get(username='doc')),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_get_display_name_localsite_admin_private_other_site(self):
        """Testing Profile.get_display_name for a LocalSite admin viewing a
        member of another LocalSite with a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        viewer = User.objects.get(username='grumpy')
        site = LocalSite.objects.create(name='site-3')
        site.users.add(viewer)
        site.admins.add(viewer)

        self.assertEqual(profile.get_display_name(viewer), user.username)

    def test_get_display_name_self_private(self):
        """Testing Profile.get_display_name for a user viewing themselves with
        a private profile
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        profile.is_private = True

        self.assertEqual(profile.get_display_name(user), user.get_full_name())

    def test_star_review_group(self):
        """Testing Profile.star_review_group"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        group1 = self.create_review_group(name='group1')
        profile.starred_groups.add(group1)

        group2 = self.create_review_group(name='group2')

        # 1 query:
        #
        # 2. Insert-or-ignore new entry
        queries = [
            {
                'type': 'INSERT',
                'model': Profile.starred_groups.through,
            },
        ]

        with self.assertQueries(queries):
            profile.star_review_group(group2)

        self.assertEqual(list(profile.starred_groups.order_by('pk')),
                         [group1, group2])

    @add_fixtures(['test_site'])
    def test_star_review_group_invalidates_cache(self):
        """Testing Profile.star_review_group invalidates count caches"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        profile.star_review_group(self.create_review_group(name='group1'))

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review group count.
        cross_site_queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review group count.
        global_site_queries = [
            {
                'model': Group,
                'annotations': {'__count': Count('*')},
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 1)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 1)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review group count.
        local_site_queries = [
            {
                'model': Group,
                'annotations': {'__count': Count('*')},
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': (Q(starred_by__id=user.pk) &
                          Q(local_site=local_site)),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

        # Star again. This should invalidate the global and cross-site caches.
        profile.star_review_group(self.create_review_group(name='group2'))
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the global site.
        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

        # Fetch the count for the LocalSite. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

    @add_fixtures(['test_site'])
    def test_star_review_group_with_local_site_invalidates_cache(self):
        """Testing Profile.star_review_group with LocalSite invalidates
        count caches
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        profile.star_review_group(self.create_review_group(
            name='group1',
            local_site=local_site))

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review group count.
        cross_site_queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review group count.
        local_site_queries = [
            {
                'model': Group,
                'annotations': {'__count': Count('*')},
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                1)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review group count.
        global_site_queries = [
            {
                'model': Group,
                'annotations': {'__count': Count('*')},
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        # Star again. This should invalidate the LocalSite and cross-site
        # caches.
        profile.star_review_group(self.create_review_group(
            name='group2',
            local_site=local_site))
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the LocalSite.
        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                2)

        # Fetch the count for the global site. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(),
                0)

    def test_unstar_review_group(self):
        """Testing Profile.unstar_review_group"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        group = self.create_review_group(name='group1')
        profile.starred_groups.add(group)

        # 2 queries:
        #
        # 1. Fetch existing starred entries (to avoid duplicates)
        # 2. Remove the entry
        queries = [
            {
                'model': Profile.starred_groups.through,
                'where': Q(profile=(profile.pk,)) & Q(group__in={group.pk}),
            },
            {
                'type': 'DELETE',
                'model': Profile.starred_groups.through,
                'where': Q(id__in=[group.pk]),
            },
        ]

        with self.assertQueries(queries):
            profile.unstar_review_group(group)

        self.assertFalse(profile.starred_groups.exists())

    @add_fixtures(['test_site'])
    def test_unstar_review_group_invalidates_cache(self):
        """Testing Profile.unstar_review_group invalidates count caches"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        profile.star_review_group(group1)
        profile.star_review_group(group2)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred group count.
        cross_site_queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred group count.
        global_site_queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred group count.
        local_site_queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

        # Unstar the group. This should invalidate the global and cross-site
        # caches.
        profile.unstar_review_group(group2)
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the global site.
        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 1)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 1)

        # Fetch the count for the LocalSite. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

    @add_fixtures(['test_site'])
    def test_unstar_review_group_with_local_site_invalidates_cache(self):
        """Testing Profile.unstar_review_group with LocalSite invalidates
        count caches
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        group1 = self.create_review_group(name='group1',
                                          local_site=local_site)
        group2 = self.create_review_group(name='group2',
                                          local_site=local_site)
        profile.star_review_group(group1)
        profile.star_review_group(group2)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred group count.
        cross_site_queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred group count.
        local_site_queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                2)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred group count.
        global_site_queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        # Unstar the group. This should invalidate the LocalSite and
        # cross-site caches.
        profile.unstar_review_group(group2)
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the LocalSite.
        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                1)

        # Fetch the count for the global site. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

    def test_star_review_request_with_discarded(self):
        """Testing Profile.star_review_request with discarded review request"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request1 = self.create_review_request()
        profile.starred_review_requests.add(review_request1)

        review_request2 = self.create_review_request(publish=True)
        review_request2.close(ReviewRequest.DISCARDED)

        # 1 query:
        #
        # 1. Insert-or-ignore new entry
        queries = [
            {
                'type': 'INSERT',
                'model': Profile.starred_review_requests.through,
            },
        ]

        with self.assertQueries(queries):
            profile.star_review_request(review_request2)

        self.assertEqual(list(profile.starred_review_requests.order_by('pk')),
                         [review_request1, review_request2])
        self.assertEqual(site_profile.starred_public_request_count, 0)

    def test_star_review_request_with_draft(self):
        """Testing Profile.star_review_request with draft review request"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request1 = self.create_review_request()
        profile.starred_review_requests.add(review_request1)

        review_request2 = self.create_review_request()

        # 1 query:
        #
        # 1. Insert-or-ignore new entry
        queries = [
            {
                'type': 'INSERT',
                'model': Profile.starred_review_requests.through,
            },
        ]

        with self.assertQueries(queries):
            profile.star_review_request(review_request2)

        self.assertEqual(list(profile.starred_review_requests.order_by('pk')),
                         [review_request1, review_request2])
        self.assertEqual(site_profile.starred_public_request_count, 0)

    def test_star_review_request_with_pending(self):
        """Testing Profile.star_review_request with pending review request"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request1 = self.create_review_request()
        profile.starred_review_requests.add(review_request1)
        site_profile.starred_public_request_count = 1
        site_profile.save(update_fields=('starred_public_request_count',))

        review_request2 = self.create_review_request(publish=True)

        # 3 queries:
        #
        # 1. Insert-or-ignore new entry
        # 2. Update LocalSiteProfile.starred_public_request_count
        # 3. Re-fetch LocalSiteProfile.starred_public_request_count
        queries = [
            {
                'type': 'INSERT',
                'model': Profile.starred_review_requests.through,
            },
            {
                'type': 'UPDATE',
                'model': LocalSiteProfile,
                'where': Q(pk=user.pk),
            },
            {
                'model': LocalSiteProfile,
                'values_select': ('starred_public_request_count',),
                'where': Q(pk=user.pk),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            profile.star_review_request(review_request2)

        self.assertEqual(list(profile.starred_review_requests.order_by('pk')),
                         [review_request1, review_request2])
        self.assertEqual(site_profile.starred_public_request_count, 2)

    def test_star_review_request_with_submitted(self):
        """Testing Profile.star_review_request with submitted review request"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request1 = self.create_review_request()
        profile.starred_review_requests.add(review_request1)
        site_profile.starred_public_request_count = 1
        site_profile.save(update_fields=('starred_public_request_count',))

        review_request2 = self.create_review_request(publish=True)
        review_request2.close(ReviewRequest.SUBMITTED)

        # 3 queries:
        #
        # 1. Insert-or-ignore new entry
        # 2. Update LocalSiteProfile.starred_public_request_count
        # 3. Re-fetch LocalSiteProfile.starred_public_request_count
        queries = [
            {
                'type': 'INSERT',
                'model': Profile.starred_review_requests.through,
            },
            {
                'type': 'UPDATE',
                'model': LocalSiteProfile,
                'where': Q(pk=user.pk),
            },
            {
                'model': LocalSiteProfile,
                'values_select': ('starred_public_request_count',),
                'where': Q(pk=user.pk),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            profile.star_review_request(review_request2)

        self.assertEqual(list(profile.starred_review_requests.order_by('pk')),
                         [review_request1, review_request2])
        self.assertEqual(site_profile.starred_public_request_count, 2)

    @add_fixtures(['test_site'])
    def test_star_review_request_invalidates_cache(self):
        """Testing Profile.star_review_request invalidates count cache"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        profile.star_review_request(self.create_review_request())

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        cross_site_queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        global_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 1)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 1)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        local_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

        # Star again. This should invalidate the global and cross-site caches.
        profile.star_review_request(self.create_review_request(publish=True))

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the global site.
        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

        # Fetch the count for the LocalSite. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

    @add_fixtures(['test_site'])
    def test_star_review_request_with_local_site_invalidates_cache(self):
        """Testing Profile.star_review_request with LocalSite invalidates
        count cache
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        profile.star_review_request(
            self.create_review_request(local_site=local_site))

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        cross_site_queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        local_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                1)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        global_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        # Star again. This should invalidate the global and cross-site caches.
        profile.star_review_request(
            self.create_review_request(publish=True,
                                       local_site=local_site,
                                       local_id=1002))
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the LocalSite.
        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                2)

        # Fetch the count for the global site. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

    def test_unstar_review_request_with_discarded(self):
        """Testing Profile.unstar_review_request with discarded review request
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request = self.create_review_request(publish=True)
        review_request.close(ReviewRequest.DISCARDED)
        profile.starred_review_requests.add(review_request)

        # 2 queries:
        #
        # 1. Fetch existing starred entries (to avoid duplicates)
        # 2. Insert new entry
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'where': (Q(profile=(profile.pk,)) &
                          Q(reviewrequest__in={review_request.pk})),
            },
            {
                'type': 'DELETE',
                'model': Profile.starred_review_requests.through,
                'where': Q(id__in=[review_request.pk]),
            },
        ]

        with self.assertQueries(queries):
            profile.unstar_review_request(review_request)

        self.assertFalse(profile.starred_review_requests.exists())
        self.assertEqual(site_profile.starred_public_request_count, 0)

    def test_unstar_review_request_with_draft(self):
        """Testing Profile.unstar_review_request with draft review request"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request = self.create_review_request()
        profile.starred_review_requests.add(review_request)

        # 2 queries:
        #
        # 1. Fetch existing starred entries (to avoid duplicates)
        # 2. Insert new entry
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'where': (Q(profile=(profile.pk,)) &
                          Q(reviewrequest__in={review_request.pk})),
            },
            {
                'type': 'DELETE',
                'model': Profile.starred_review_requests.through,
                'where': Q(id__in=[review_request.pk]),
            },
        ]

        with self.assertQueries(queries):
            profile.unstar_review_request(review_request)

        self.assertFalse(profile.starred_review_requests.exists())
        self.assertEqual(site_profile.starred_public_request_count, 0)

    def test_unstar_review_request_with_pending(self):
        """Testing Profile.unstar_review_request with pending review request"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request = self.create_review_request(publish=True)
        profile.starred_review_requests.add(review_request)
        site_profile.starred_public_request_count = 1
        site_profile.save(update_fields=('starred_public_request_count',))

        # 4 queries:
        #
        # 1. Fetch existing starred entries (to avoid duplicates)
        # 2. Remove the entry
        # 3. Update LocalSiteProfile.starred_public_request_count
        # 4. Re-fetch LocalSiteProfile.starred_public_request_count
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'where': (Q(profile=(profile.pk,)) &
                          Q(reviewrequest__in={review_request.pk})),
            },
            {
                'type': 'DELETE',
                'model': Profile.starred_review_requests.through,
                'where': Q(id__in=[review_request.pk]),
            },
            {
                'type': 'UPDATE',
                'model': LocalSiteProfile,
                'where': Q(pk=site_profile.pk),
            },
            {
                'model': LocalSiteProfile,
                'values_select': ('starred_public_request_count',),
                'where': Q(pk=site_profile.pk),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            profile.unstar_review_request(review_request)

        self.assertFalse(profile.starred_review_requests.exists())
        self.assertEqual(site_profile.starred_public_request_count, 0)

    def test_unstar_review_request_with_submitted(self):
        """Testing Profile.unstar_review_request with submitted review request
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        site_profile = user.get_site_profile(local_site=None)

        review_request = self.create_review_request(publish=True)
        review_request.close(ReviewRequest.SUBMITTED)

        profile.starred_review_requests.add(review_request)
        site_profile.starred_public_request_count = 1
        site_profile.save(update_fields=('starred_public_request_count',))

        # 4 queries:
        #
        # 1. Fetch existing starred entries (to avoid duplicates)
        # 2. Remove the entry
        # 3. Update LocalSiteProfile.starred_public_request_count
        # 4. Re-fetch LocalSiteProfile.starred_public_request_count
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'where': (Q(profile=(profile.pk,)) &
                          Q(reviewrequest__in={review_request.pk})),
            },
            {
                'type': 'DELETE',
                'model': Profile.starred_review_requests.through,
                'where': Q(id__in=[review_request.pk]),
            },
            {
                'type': 'UPDATE',
                'model': LocalSiteProfile,
                'where': Q(pk=site_profile.pk),
            },
            {
                'model': LocalSiteProfile,
                'values_select': ('starred_public_request_count',),
                'where': Q(pk=site_profile.pk),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            profile.unstar_review_request(review_request)

        self.assertFalse(profile.starred_review_requests.exists())
        self.assertEqual(site_profile.starred_public_request_count, 0)

    @add_fixtures(['test_site'])
    def test_unstar_review_request_invalidates_cache(self):
        """Testing Profile.unstar_review_request invalidates count cache"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        review_request1 = self.create_review_request()
        review_request2 = self.create_review_request()
        profile.star_review_request(review_request1)
        profile.star_review_request(review_request2)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        cross_site_queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        global_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        local_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

        # Unstar it. This should invalidate the global and cross-site caches.
        profile.unstar_review_request(review_request2)

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the global site.
        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 1)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 1)

        # Fetch the count for the LocalSite. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

    @add_fixtures(['test_site'])
    def test_unstar_review_request_with_local_site_invalidates_cache(self):
        """Testing Profile.unstar_review_request with LocalSite invalidates
        count cache
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)
        local_site.users.add(user)

        review_request1 = self.create_review_request(local_site=local_site,
                                                     local_id=1)
        review_request2 = self.create_review_request(local_site=local_site,
                                                     local_id=2)
        profile.star_review_request(review_request1)
        profile.star_review_request(review_request2)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        cross_site_queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                2)

        # Fetch the count for the LocalSite.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        local_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                2)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                2)

        # Fetch the count for the global site.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review request count.
        global_site_queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(global_site_queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        # Unstar it. This should invalidate the LocalSite and cross-site
        # caches.
        profile.unstar_review_request(review_request2)
        self.assertTrue(LocalSite.objects.has_local_sites())

        # Fetch the count for cross-sites.
        with self.assertQueries(cross_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                1)

        # Fetch the count for the LocalSite.
        with self.assertQueries(local_site_queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                1)

        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                1)

        # Fetch the count for the global site. This should still be in cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

    def test_get_starred_review_groups_count(self):
        """Testing Profile.get_starred_review_groups_count"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'))
        cache.clear()

        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should now be 2.
        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

    @add_fixtures(['test_site'])
    def test_get_starred_review_groups_count_with_local_site_in_db(self):
        """Testing Profile.get_starred_review_groups_count with LocalSites in
        database
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 0)

        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'),
            self.create_review_group(name='group3',
                                     with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be 2.
        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_groups_count(), 2)

    @add_fixtures(['test_site'])
    def test_get_starred_review_groups_count_with_local_site(self):
        """Testing Profile.get_starred_review_groups_count with local_site="""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                0)

        # Star review groups and invalidate cache.
        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'),
            self.create_review_group(name='group3',
                                     with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be 1.
        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                1)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(local_site=local_site),
                1)

    @add_fixtures(['test_site'])
    def test_get_starred_review_groups_count_with_local_site_all(self):
        """Testing Profile.get_starred_review_groups_count with
        local_site=LocalSite.ALL
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                0)

        # Star review groups and invalidate cache.
        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'),
            self.create_review_group(name='group3',
                                     with_local_site=True))
        cache.clear()

        # This should now be 1.
        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                3)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_groups_count(
                    local_site=LocalSite.ALL),
                3)

    def test_get_starred_review_requests_count(self):
        """Testing Profile.get_starred_review_requests_count"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request())
        cache.clear()

        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should now be 2.
        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

    @add_fixtures(['test_site'])
    def test_get_starred_review_requests_count_with_local_site_in_db(self):
        """Testing Profile.get_starred_review_requests_count with LocalSites
        in database
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 0)

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request(),
            self.create_review_request(with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be 2.
        with self.assertQueries(queries):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(profile.get_starred_review_requests_count(), 2)

    @add_fixtures(['test_site'])
    def test_get_starred_review_requests_count_with_local_site(self):
        """Testing Profile.get_starred_review_requests_count with local_site=
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                0)

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request(),
            self.create_review_request(with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be 1.
        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                1)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=local_site),
                1)

    @add_fixtures(['test_site'])
    def test_get_starred_review_requests_count_with_local_site_all(self):
        """Testing Profile.get_starred_review_requests_count with
        local_site=LocalSite.ALL
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This should start out as 0.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                0)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                0)

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request(),
            self.create_review_request(with_local_site=True))
        cache.clear()

        # This should now be 1.
        with self.assertQueries(queries):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                3)

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertEqual(
                profile.get_starred_review_requests_count(
                    local_site=LocalSite.ALL),
                3)

    def test_has_starred_review_groups(self):
        """Testing Profile.has_starred_review_groups"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.has_starred_review_groups())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.has_starred_review_groups())

        # Star groups and invalidate cache.
        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'))
        cache.clear()

        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(profile.has_starred_review_groups())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(profile.has_starred_review_groups())

    @add_fixtures(['test_site'])
    def test_has_starred_review_groups_with_local_site_in_db(self):
        """Testing Profile.has_starred_review_groups with LocalSites in
        database
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.has_starred_review_groups())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.has_starred_review_groups())

        # Star groups and invalidate cache.
        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'),
            self.create_review_group(name='group3',
                                     with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(profile.has_starred_review_groups())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(profile.has_starred_review_groups())

    @add_fixtures(['test_site'])
    def test_has_starred_review_groups_with_local_site(self):
        """Testing Profile.has_starred_review_groups with local_site="""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(
                profile.has_starred_review_groups(local_site=local_site))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(
                profile.has_starred_review_groups(local_site=local_site))

        # Star groups and invalidate cache.
        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'),
            self.create_review_group(name='group3',
                                     with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(
                profile.has_starred_review_groups(local_site=local_site))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(
                profile.has_starred_review_groups(local_site=local_site))

    @add_fixtures(['test_site'])
    def test_has_starred_review_groups_with_local_site_all(self):
        """Testing Profile.has_starred_review_groups with
        local_site=LocalSite.ALL
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(
                profile.has_starred_review_groups(local_site=LocalSite.ALL))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(
                profile.has_starred_review_groups(local_site=LocalSite.ALL))

        # Star groups and invalidate cache.
        profile.starred_groups.add(
            self.create_review_group(name='group1'),
            self.create_review_group(name='group2'),
            self.create_review_group(name='group2',
                                     with_local_site=True))
        cache.clear()

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(
                profile.has_starred_review_groups(local_site=LocalSite.ALL))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(
                profile.has_starred_review_groups(local_site=LocalSite.ALL))

    def test_has_starred_review_requests(self):
        """Testing Profile.has_starred_review_requests"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.has_starred_review_requests())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.has_starred_review_requests())

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request())
        cache.clear()

        self.assertFalse(LocalSite.objects.has_local_sites())

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(profile.has_starred_review_requests())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(profile.has_starred_review_requests())

    @add_fixtures(['test_site'])
    def test_has_starred_review_requests_with_local_site_in_db(self):
        """Testing Profile.has_starred_review_requests with LocalSites in
        database
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.has_starred_review_requests())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.has_starred_review_requests())

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request(),
            self.create_review_request(with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(profile.has_starred_review_requests())

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(profile.has_starred_review_requests())

    @add_fixtures(['test_site'])
    def test_has_starred_review_requests_with_local_site(self):
        """Testing Profile.has_starred_review_requests with local_site="""
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        local_site = self.get_local_site(self.local_site_name)

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=local_site),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(
                profile.has_starred_review_requests(local_site=local_site))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(
                profile.has_starred_review_requests(local_site=local_site))

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request(),
            self.create_review_request(with_local_site=True))
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(
                profile.has_starred_review_requests(local_site=local_site))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(
                profile.has_starred_review_requests(local_site=local_site))

    @add_fixtures(['test_site'])
    def test_has_starred_review_requests_with_local_site_all(self):
        """Testing Profile.has_starred_review_requests with
        local_site=LocalSite.ALL
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        # This should start out as False.
        #
        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(
                profile.has_starred_review_requests(local_site=LocalSite.ALL))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(
                profile.has_starred_review_requests(local_site=LocalSite.ALL))

        # Star review requests and invalidate cache.
        profile.starred_review_requests.add(
            self.create_review_request(),
            self.create_review_request(),
            self.create_review_request(with_local_site=True))
        cache.clear()

        # This should now be True.
        with self.assertQueries(queries):
            self.assertTrue(
                profile.has_starred_review_requests(local_site=LocalSite.ALL))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertTrue(
                profile.has_starred_review_requests(local_site=LocalSite.ALL))

    def test_is_review_request_starred(self):
        """Testing Profile.is_review_request_starred"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        review_request = self.create_review_request()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile)
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.is_review_request_starred(review_request))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.is_review_request_starred(review_request))

        # Star a review request and invalidate cache.
        profile.starred_review_requests.add(review_request)
        cache.clear()

        self.assertFalse(LocalSite.objects.has_local_sites())

        # 2 queries:
        #
        # 1. Fetch user's starred review requests count.
        # 2. starred_review_requests lookup
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile)
            },
            {
                'model': Profile.starred_review_requests.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(reviewrequest=review_request.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_request_starred(review_request))

        # A second call will still perform the starred_review_requests lookup.
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(reviewrequest=review_request.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_request_starred(review_request))

    @add_fixtures(['test_site'])
    def test_is_review_request_starred_with_local_site_in_db(self):
        """Testing Profile.is_review_request_starred with LocalSites in
        database
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        review_request = self.create_review_request()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # 1 query:
        #
        # 1. Fetch user's starred review requests count.
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.is_review_request_starred(review_request))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.is_review_request_starred(review_request))

        # Star a review request and invalidate cache.
        profile.starred_review_requests.add(review_request)
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # 2 queries:
        #
        # 1. Fetch user's starred review requests count.
        # 2. starred_review_requests lookup
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
            {
                'model': Profile.starred_review_requests.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(reviewrequest=review_request.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_request_starred(review_request))

        # A second call will still perform the starred_review_requests lookup.
        queries = [
            {
                'model': Profile.starred_review_requests.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(reviewrequest=review_request.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_request_starred(review_request))

    def test_is_review_group_starred(self):
        """Testing Profile.is_review_group_starred"""
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        review_group = self.create_review_group()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertFalse(LocalSite.objects.has_local_sites())

        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.is_review_group_starred(review_group))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.is_review_group_starred(review_group))

        # Star a review group and invalidate cache.
        profile.starred_groups.add(review_group)
        cache.clear()

        self.assertFalse(LocalSite.objects.has_local_sites())

        # 2 queries:
        #
        # 1. The cache fetch
        # 2. starred_groups lookup
        queries = [
            {
                'model': Profile.starred_groups.through,
                'annotations': {'__count': Count('*')},
                'where': Q(profile=profile),
            },
            {
                'model': Profile.starred_groups.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(group=review_group.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_group_starred(review_group))

        # A second call will still perform the starred_groups lookup.
        queries = [
            {
                'model': Profile.starred_groups.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(group=review_group.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_group_starred(review_group))

    @add_fixtures(['test_site'])
    def test_is_review_group_starred_with_local_site_in_db(self):
        """Testing Profile.is_review_group_starred with LocalSites in database
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        review_group = self.create_review_group()

        # This has the side-effect of pre-fetching stats, so they don't
        # interfere with query counts below.
        self.assertTrue(LocalSite.objects.has_local_sites())

        # 1 query:
        #
        # 1. Fetch user's starred review groups count.
        queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
        ]

        with self.assertQueries(queries):
            self.assertFalse(profile.is_review_group_starred(review_group))

        # A second call should hit the cache.
        with self.assertNumQueries(0):
            self.assertFalse(profile.is_review_group_starred(review_group))

        # Star a review group and invalidate cache.
        profile.starred_groups.add(review_group)
        cache.clear()

        self.assertTrue(LocalSite.objects.has_local_sites())

        # 2 queries:
        #
        # 1. The cache fetch
        # 2. starred_groups lookup
        queries = [
            {
                'model': Group,
                'num_joins': 1,
                'annotations': {'__count': Count('*')},
                'tables': {
                    'accounts_profile_starred_groups',
                    'reviews_group',
                },
                'where': Q(starred_by__id=user.pk) & Q(local_site=None),
            },
            {
                'model': Profile.starred_groups.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(group=review_group.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_group_starred(review_group))

        # A second call will still perform the starred_groups lookup.
        queries = [
            {
                'model': Profile.starred_groups.through,
                'extra': {
                    'a': ('1', []),
                },
                'where': (Q(profile=profile.pk) &
                          Q(group=review_group.pk)),
                'limit': 1,
            },
        ]

        with self.assertQueries(queries):
            self.assertTrue(profile.is_review_group_starred(review_group))
