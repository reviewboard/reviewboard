"""Unit tests for the All Review Requests page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import Permission, User
from django.db.models import Count, Q
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile, Profile
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite


class AllReviewRequestViewTests(BaseViewTestCase):
    """Unit tests for the all_review_requests view."""

    datagrid_url = '/r/'

    @add_fixtures(['test_users'])
    def test_with_access(self):
        """Testing all_review_requests view"""
        self._test_with_access()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_site(self):
        """Testing all_review_requests view on a Local Site"""
        self._test_with_access(with_local_site=True,
                               local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_access_with_local_sites_in_db(self):
        """Testing all_review_requests view with Local Sites in the database
        """
        self._test_with_access(local_sites_in_db=True)

    def test_as_anonymous_and_redirect(self):
        """Testing all_review_requests view as anonymous user
        with anonymous access disabled
        """
        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            response = self.client.get('/r/')

        self.assertEqual(response.status_code, 302)

    @add_fixtures(['test_scmtools', 'test_users'])
    def test_with_private_review_requests(self):
        """Testing all_review_requests view with private review requests"""
        self._test_with_private_review_requests()

    @add_fixtures(['test_site', 'test_scmtools', 'test_users'])
    def test_with_private_review_requests_with_local_site(self):
        """Testing all_review_requests view with private review requests on
        a Local Site
        """
        self._test_with_private_review_requests(with_local_site=True,
                                                local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools', 'test_users'])
    def test_with_private_review_requests_with_local_sites_in_db(self):
        """Testing all_review_requests view with private review requests with
        Local Sites in the database
        """
        self._test_with_private_review_requests(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_with_inactive_users(self):
        """Testing all_review_requests view with review requests from inactive
        users
        """
        self._test_with_inactive_users()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_inactive_users_with_local_site(self):
        """Testing all_review_requests view with review requests from inactive
        users on a Local Site
        """
        self._test_with_inactive_users(with_local_site=True,
                                       local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_inactive_users_with_local_sites_in_db(self):
        """Testing all_review_requests view with review requests from inactive
        users with Local Sites in the database
        """
        self._test_with_inactive_users(local_sites_in_db=True)

    def _test_with_access(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for a user with access to the datagrid.

        This accesses the All Review Requests datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results.

        Args:
            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            publish=True)
        self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Test 2',
            publish=True)
        self.create_review_request(
            local_site=local_site,
            local_id=3,
            summary='Test 3',
            publish=True)

        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')
        profile = user.get_profile()

        if local_site:
            local_site.users.add(user)

        self._prefetch_cached(local_site=local_site)

        extra = {
            'new_review_count': ("""
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = 4
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != 4
            """, []),
            'draft_summary': ("""
                SELECT reviews_reviewrequestdraft.summary
                  FROM reviews_reviewrequestdraft
                  WHERE reviews_reviewrequestdraft.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'visibility': ("""
                SELECT accounts_reviewrequestvisit.visibility
                  FROM accounts_reviewrequestvisit
                 WHERE accounts_reviewrequestvisit.review_request_id =
                       reviews_reviewrequest.id
                   AND accounts_reviewrequestvisit.user_id = 4
            """, []),
        }

        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'model': LocalSite,
                    'tables': {
                        'site_localsite',
                    },
                    'where': Q(name=local_site.name),
                },
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': Repository,
                'num_joins': 4,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                    'scmtools_repository',
                    'scmtools_repository_review_groups',
                    'scmtools_repository_users',
                },
                'values_select': ('pk',),
                'where': ((Q(public=True) |
                           Q(users__pk=user.pk) |
                           Q(review_groups__users=user.pk)) &
                          Q(local_site=local_site)),
            },
            {
                'model': Permission,
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'num_joins': 4,
                'tables': {
                    'auth_group',
                    'auth_group_permissions',
                    'auth_permission',
                    'auth_user_groups',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(group__user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_admins',
                    },
                    'where': (Q(local_site_admins__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
                {
                    'model': LocalSiteProfile,
                    'where': (Q(local_site=local_site) &
                              Q(profile=profile) &
                              Q(user=user)),
                },
            ]

        queries += [
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'values_select': ('pk',),
                'where': ((Q(invite_only=False) |
                           Q(users=user.pk)) &
                          Q(local_site=local_site)),
            },
            {
                'model': Profile,
                'tables': {
                    'accounts_profile',
                },
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
            {
                'model': ReviewRequest,
                'annotations': {'__count': Count('*')},
            },
            {
                'distinct': True,
                'extra': extra,
                'limit': 3,
                'model': ReviewRequest,
                'num_joins': 2,
                'order_by': ('-last_updated',),
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'where': (
                    Q((Q(public=True) |
                       Q(submitter=user)) &
                      local_site_q &
                      (Q(submitter=user) |
                       (Q(repository=None) |
                        Q(repository__in=[])) &
                       (Q(target_people=user) |
                        Q(target_groups=None) |
                        Q(target_groups__in=[])))) &
                    Q(local_site=local_site)
                ),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=profile.pk) &
                          Q(pk__in=[3, 2, 1])),
            },
        ]

        if local_site:
            queries += [
                {
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'where': Q(pk__in=[3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'where': Q(pk__in=[3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 1')

    def _test_with_private_review_requests(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private review requests.

        This accesses the All Review Requests datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure only accessible
        private review requests are included.

        Args:
            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        user = User.objects.get(username='grumpy')
        profile = user.get_profile()

        if local_site:
            local_site.users.add(user)

        # These are public
        self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            publish=True)
        self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Test 2',
            publish=True)

        repository1 = self.create_repository(
            local_site=local_site,
            name='repo1',
            public=False)
        repository1.users.add(user)
        self.create_review_request(
            local_site=local_site,
            local_id=3,
            summary='Test 3',
            repository=repository1,
            publish=True)

        group1 = self.create_review_group(
            local_site=local_site,
            name='group1',
            invite_only=True)
        group1.users.add(user)
        review_request = self.create_review_request(
            local_site=local_site,
            local_id=4,
            summary='Test 4',
            publish=True)
        review_request.target_groups.add(group1)

        # These are private
        repository2 = self.create_repository(
            local_site=local_site,
            name='group2',
            public=False)
        self.create_review_request(
            local_site=local_site,
            local_id=5,
            summary='Test 5',
            repository=repository2,
            publish=True)

        group2 = self.create_review_group(
            local_site=local_site,
            name='group2',
            invite_only=True)
        review_request = self.create_review_request(
            local_site=local_site,
            local_id=6,
            summary='Test 6',
            publish=True)
        review_request.target_groups.add(group2)

        # Log in and check what we get.
        self.client.login(username='grumpy', password='grumpy')

        self._prefetch_cached(local_site=local_site)

        extra = {
            'new_review_count': ("""
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = 4
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != 4
            """, []),
            'draft_summary': ("""
                SELECT reviews_reviewrequestdraft.summary
                  FROM reviews_reviewrequestdraft
                  WHERE reviews_reviewrequestdraft.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'visibility': ("""
                SELECT accounts_reviewrequestvisit.visibility
                  FROM accounts_reviewrequestvisit
                 WHERE accounts_reviewrequestvisit.review_request_id =
                       reviews_reviewrequest.id
                   AND accounts_reviewrequestvisit.user_id = 4
            """, []),
        }

        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'model': LocalSite,
                    'tables': {
                        'site_localsite',
                    },
                    'where': Q(name=local_site.name),
                },
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': Repository,
                'num_joins': 4,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                    'scmtools_repository',
                    'scmtools_repository_review_groups',
                    'scmtools_repository_users',
                },
                'values_select': ('pk',),
                'where': ((Q(public=True) |
                           Q(users__pk=user.pk) |
                           Q(review_groups__users=user.pk)) &
                          Q(local_site=local_site)),
            },
            {
                'model': Permission,
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'num_joins': 4,
                'tables': {
                    'auth_group',
                    'auth_group_permissions',
                    'auth_permission',
                    'auth_user_groups',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(group__user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_admins',
                    },
                    'where': (Q(local_site_admins__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
                {
                    'model': LocalSiteProfile,
                    'where': (Q(local_site=local_site) &
                              Q(profile=profile) &
                              Q(user=user)),
                },
            ]

        queries += [
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'values_select': ('pk',),
                'where': ((Q(invite_only=False) |
                           Q(users=user.pk)) &
                          Q(local_site=local_site)),
            },
            {
                'model': Profile,
                'tables': {
                    'accounts_profile',
                },
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
            {
                'annotations': {'__count': Count('*')},
                'model': ReviewRequest,
            },
            {
                'distinct': True,
                'extra': extra,
                'limit': 4,
                'model': ReviewRequest,
                'num_joins': 2,
                'order_by': ('-last_updated',),
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'where': (
                    Q((Q(public=True) |
                       Q(submitter=user)) &
                      local_site_q &
                      (Q(submitter=user) |
                       (Q(repository=None) |
                        Q(repository__in=[1])) &
                       (Q(target_people=user) |
                        Q(target_groups=None) |
                        Q(target_groups__in=[1])))) &
                    Q(local_site=local_site)
                ),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=profile.pk) &
                          Q(pk__in=[4, 3, 2, 1])),
            },
        ]

        if local_site:
            queries += [
                {
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'where': Q(pk__in=[4, 3, 2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'where': Q(pk__in=[4, 3, 2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 4')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 3')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[3]['object'].summary, 'Test 1')

    def _test_with_inactive_users(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking for review requests from inactive users.

        This accesses the All Review Requests datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure review requests
        from inactive users are included.

        Args:
            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        if local_sites_in_db:
            local_site_q = Q(local_site=local_site)
        else:
            local_site_q = Q()

        User.objects.filter(username='doc').update(is_active=False)

        review_request = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Test 1',
            submitter='doc',
            publish=True)
        review_request.close(ReviewRequest.SUBMITTED)
        self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Test 2',
            submitter='grumpy',
            publish=True)

        self.client.login(username='grumpy', password='grumpy')
        user = User.objects.get(username='grumpy')
        profile = user.get_profile()

        if local_site:
            local_site.users.add(user)

        self._prefetch_cached(local_site=local_site)

        extra = {
            'new_review_count': ("""
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = 4
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != 4
            """, []),
            'draft_summary': ("""
                SELECT reviews_reviewrequestdraft.summary
                  FROM reviews_reviewrequestdraft
                  WHERE reviews_reviewrequestdraft.review_request_id =
                        reviews_reviewrequest.id
            """, []),
            'visibility': ("""
                SELECT accounts_reviewrequestvisit.visibility
                  FROM accounts_reviewrequestvisit
                 WHERE accounts_reviewrequestvisit.review_request_id =
                       reviews_reviewrequest.id
                   AND accounts_reviewrequestvisit.user_id = 4
            """, []),
        }

        queries = [
            {
                'model': User,
                'where': Q(pk=user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'model': LocalSite,
                    'tables': {
                        'site_localsite',
                    },
                    'where': Q(name=local_site.name),
                },
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': Q(local_site__id=local_site.pk) & Q(pk=user.pk),
                },
            ]

        queries += [
            {
                'model': Repository,
                'num_joins': 4,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                    'scmtools_repository',
                    'scmtools_repository_review_groups',
                    'scmtools_repository_users',
                },
                'values_select': ('pk',),
                'where': ((Q(public=True) |
                           Q(users__pk=user.pk) |
                           Q(review_groups__users=user.pk)) &
                          Q(local_site=local_site)),
            },
            {
                'model': Permission,
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'num_joins': 4,
                'tables': {
                    'auth_group',
                    'auth_group_permissions',
                    'auth_permission',
                    'auth_user_groups',
                    'django_content_type',
                },
                'values_select': ('content_type__app_label', 'codename'),
                'where': Q(group__user=user),
            },
        ]

        if local_site:
            queries += [
                {
                    'extra': {
                        'a': ('1', []),
                    },
                    'limit': 1,
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_admins',
                    },
                    'where': (Q(local_site_admins__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
                {
                    'model': LocalSiteProfile,
                    'where': (Q(local_site=local_site) &
                              Q(profile=profile) &
                              Q(user=user)),
                },
            ]

        queries += [
            {
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'values_select': ('pk',),
                'where': ((Q(invite_only=False) |
                           Q(users=user.pk)) &
                          Q(local_site=local_site)),
            },
            {
                'model': Profile,
                'tables': {
                    'accounts_profile',
                },
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
            {
                'annotations': {'__count': Count('*')},
                'model': ReviewRequest,
            },
            {
                'distinct': True,
                'extra': extra,
                'limit': 2,
                'model': ReviewRequest,
                'num_joins': 2,
                'order_by': ('-last_updated',),
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'where': (
                    Q((Q(public=True) |
                       Q(submitter=user)) &
                      local_site_q &
                      (Q(submitter=user) |
                       (Q(repository=None) |
                        Q(repository__in=[])) &
                       (Q(target_people=user) |
                        Q(target_groups=None) |
                        Q(target_groups__in=[])))) &
                    Q(local_site=local_site)
                ),
            },
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'values_select': ('pk',),
                'where': (Q(starred_by__id=profile.pk) &
                          Q(pk__in=[2, 1])),
            },
        ]

        if local_site:
            queries += [
                {
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {
                        'local_site',
                        'submitter',
                    },
                    'where': Q(pk__in=[2, 1]),
                },
            ]
        else:
            queries += [
                {
                    'extra': extra,
                    'model': ReviewRequest,
                    'select_related': {'submitter'},
                    'where': Q(pk__in=[2, 1]),
                },
            ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Test 2')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Test 1')
