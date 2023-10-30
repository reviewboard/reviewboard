"""Unit tests for the user page.

Version Added:
    5.0.7
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import Permission, User
from django.db.models import Count, Q
from django.urls import reverse
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile, Profile
from reviewboard.datagrids.builtin_items import UserGroupsItem, UserProfileItem
from reviewboard.datagrids.tests.base import BaseViewTestCase
from reviewboard.reviews.models import Group, Review, ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite


class SubmitterViewTests(BaseViewTestCase):
    """Unit tests for the submitter view."""

    datagrid_url = '/users/grumpy/'

    @add_fixtures(['test_users'])
    def test_with_private_review_requests(self):
        """Testing submitter view with private review requests"""
        self._test_with_private_review_requests()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_review_requests_with_local_site(self):
        """Testing submitter view with private review requests on a
        Local Site
        """
        self._test_with_private_review_requests(with_local_site=True,
                                                local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_review_requests_with_local_sites_in_db(self):
        """Testing submitter view with private review requests with
        Local Sites in the database
        """
        self._test_with_private_review_requests(local_sites_in_db=True)

    @add_fixtures(['test_users'])
    def test_sidebar(self):
        """Testing submitter view sidebar"""
        self._test_sidebar()

    @add_fixtures(['test_site', 'test_users'])
    def test_sidebar_with_local_site(self):
        """Testing submitter view sidebar on a Local Site"""
        self._test_sidebar(with_local_site=True,
                           local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_sidebar_with_local_sites_in_db(self):
        """Testing submitter view sidebar with Local Sites in the database"""
        self._test_sidebar(local_sites_in_db=True)

    def test_match_url_with_email_address(self):
        """Testing submitter view URL matching with e-mail address
        as username
        """
        # Test if this throws an exception. Bug #1250
        reverse('user', args=['user@example.com'])

    @add_fixtures(['test_users'])
    def test_with_private_reviews(self):
        """Testing reviews page of submitter view with private reviews"""
        self._test_with_private_reviews()

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_reviews_with_local_site(self):
        """Testing reviews page of submitter view with private reviews on a
        Local Site
        """
        self._test_with_private_reviews(with_local_site=True,
                                        local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_users'])
    def test_with_private_reviews_with_local_sites_in_db(self):
        """Testing reviews page of submitter view with private reviews with
        Local Sites in the database
        """
        self._test_with_private_reviews(local_sites_in_db=True)

    def _test_with_private_review_requests(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private review requests.

        This accesses the User page's datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure inaccessible
        private review requests are excluded.

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

        ReviewRequest.objects.all().delete()

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        grumpy = User.objects.get(username='grumpy')
        grumpy.review_groups.clear()

        if local_site:
            local_site.users.add(grumpy)

        group1 = Group.objects.create(
            local_site=local_site,
            name='test-group-1')
        group1.users.add(grumpy)

        group2 = Group.objects.create(
            local_site=local_site,
            name='test-group-2',
            invite_only=True)
        group2.users.add(grumpy)

        review_requests = []

        for i in range(5):
            review_request = self.create_review_request(
                local_site=local_site,
                local_id=i + 1,
                summary='Summary %s' % (i + 1),
                submitter=grumpy,
                publish=True)

            review_requests.append(review_request)

            if i >= 3:
                review_request.target_groups.add(group2)

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
                    AND accounts_reviewrequestvisit.user_id = 2
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != 2
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
                   AND accounts_reviewrequestvisit.user_id = 2
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
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
                {
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(username='grumpy')),
                },
            ]
        else:
            queries += [
                {
                    'model': User,
                    'where': Q(username='grumpy'),
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
                        'site_localsite_admins',
                        'auth_user',
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
                'distinct': True,
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'name',
                    'local_site',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=grumpy.pk) &
                          Q(((Q(invite_only=False) &
                              Q(visible=True)) |
                             Q(users=user.pk)) &
                            Q(local_site=None)) &
                          Q(local_site_q)),
            },
            {
                'model': Profile,
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
                'limit': 3,
                'model': ReviewRequest,
                'num_joins': 3,
                'order_by': ('-last_updated',),
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'where': (Q((Q(public=True) |
                             Q(submitter=user)) &
                            local_site_q &
                            Q(submitter__username='grumpy') &
                            Q(Q(submitter=user) |
                              (Q(repository=None) |
                               Q(repository__in=[])) &
                              (Q(target_people=user) |
                               Q(target_groups=None) |
                               Q(target_groups__in=[group1.pk])))) &
                          Q(local_site=local_site)),
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

        queries += [
            {
                'model': Profile,
                'where': Q(user=grumpy),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None
        self.assertEqual(len(datagrid.rows), 3)
        self.assertEqual(datagrid.rows[0]['object'].summary, 'Summary 3')
        self.assertEqual(datagrid.rows[1]['object'].summary, 'Summary 2')
        self.assertEqual(datagrid.rows[2]['object'].summary, 'Summary 1')

    def _test_sidebar(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private review requests.

        This accesses the User page's datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure inaccessible
        private review requests are excluded.

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

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        grumpy = User.objects.get(username='grumpy')
        grumpy.review_groups.clear()

        if local_site:
            local_site.users.add(grumpy)

        group1 = self.create_review_group(
            local_site=local_site,
            name='test-group-1')
        group1.users.add(grumpy)

        group2 = self.create_review_group(
            local_site=local_site,
            name='test-group-2',
            invite_only=True)
        group2.users.add(grumpy)

        self._prefetch_cached(local_site=local_site)

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
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
                {
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(username='grumpy')),
                },
            ]
        else:
            queries += [
                {
                    'model': User,
                    'where': Q(username='grumpy'),
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
                        'site_localsite_admins',
                        'auth_user',
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
                'distinct': True,
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'name',
                    'local_site',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=grumpy.pk) &
                          Q(((Q(invite_only=False) &
                              Q(visible=True)) |
                             Q(users=user.pk)) &
                            Q(local_site=None)) &
                          Q(local_site_q)),
            },
            {
                'model': Profile,
                'type': 'UPDATE',
                'where': Q(pk=profile.pk),
            },
            {
                'annotations': {'__count': Count('*')},
                'model': ReviewRequest,
            },
            {
                'model': Profile,
                'where': Q(user=grumpy),
            },
        ]

        # Now load the page and get the sidebar items.
        with self.assertQueries(queries):
            response = self.client.get(
                self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        sidebar_items = datagrid.sidebar_items
        self.assertEqual(len(sidebar_items), 2)

        # Test the User Profile section.
        section = sidebar_items[0]
        self.assertIsInstance(section, UserProfileItem)

        # Test the Groups section.
        section = sidebar_items[1]
        self.assertIsInstance(section, UserGroupsItem)
        self.assertEqual(str(section.label), 'Groups')

        if local_site:
            # Due to a bug, we don't report groups for Local Sites.
            self.assertEqual(len(section.items), 0)
        else:
            self.assertEqual(len(section.items), 1)
            self.assertEqual(str(section.items[0].label),
                             'test-group-1')

    def _test_with_private_reviews(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Common tests for checking access to private reviews.

        This accesses the User page's reviews datagrid as a logged-in user with
        access to the global site or Local Site (depending on the test),
        checking queries and datagrid row results to make sure inaccessible
        private reviews are excluded.

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
            review_local_site_q = Q(review_request__local_site=local_site)
        else:
            local_site_q = Q()
            review_local_site_q = Q()

        ReviewRequest.objects.all().delete()
        Review.objects.all().delete()

        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()

        grumpy = User.objects.get(username='grumpy')
        dopey = User.objects.get(username='dopey')

        if local_site:
            local_site.users.add(dopey, grumpy)

        user.review_groups.clear()
        dopey.review_groups.clear()
        grumpy.review_groups.clear()

        group = Group.objects.create(
            local_site=local_site,
            name='test-group',
            invite_only=True)
        group.users.add(dopey, grumpy)

        review_request1 = self.create_review_request(
            local_site=local_site,
            local_id=1,
            summary='Summary 1',
            submitter=dopey,
            publish=True)
        review_request2 = self.create_review_request(
            local_site=local_site,
            local_id=2,
            summary='Summary 2',
            submitter=dopey,
            publish=True)
        review_request2.target_groups.add(group)

        reviews = [
            self.create_review(review_request1,
                               user=grumpy,
                               publish=True)
            for i in range(5)
        ] + [
            self.create_review(review_request2,
                               user=grumpy,
                               publish=True)
            for i in range(5)
        ]

        self._prefetch_cached(local_site=local_site)

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
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(pk=user.pk)),
                },
                {
                    'model': User,
                    'num_joins': 1,
                    'tables': {
                        'auth_user',
                        'site_localsite_users',
                    },
                    'where': (Q(local_site__id=local_site.pk) &
                              Q(username='grumpy')),
                },
            ]
        else:
            queries += [
                {
                    'model': User,
                    'where': Q(username='grumpy'),
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
                        'site_localsite_admins',
                        'auth_user',
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
                'distinct': True,
                'model': Group,
                'num_joins': 1,
                'only_fields': {
                    'id',
                    'name',
                    'local_site',
                },
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (Q(users__id=grumpy.pk) &
                          Q(Q(Q(Q(invite_only=False) &
                                Q(visible=True)) |
                              Q(users=user.pk)) &
                            Q(local_site=None)) &
                          Q(local_site_q)),
            },
            {
                'model': Review,
                'annotations': {'__count': Count('*')},
                'num_joins': 4,
                'tables': {
                    'auth_user',
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'where': (
                    Q(Q(base_reply_to=None) &
                      review_local_site_q &
                      Q(user__username='grumpy') &
                      Q(public=True) &
                      Q(Q(review_request__repository=None) |
                        Q(review_request__repository__in=[])) &
                      Q(Q(review_request__target_people=user) |
                        Q(review_request__target_groups=None) |
                        Q(review_request__target_groups__in=[]))) &
                    Q(review_request__local_site=local_site)
                ),
            },
            {
                'distinct': True,
                'limit': 5,
                'model': Review,
                'num_joins': 4,
                'order_by': ('-timestamp',),
                'tables': {
                    'auth_user',
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest_target_people',
                },
                'values_select': ('pk',),
                'where': (
                    Q(Q(base_reply_to=None) &
                      review_local_site_q &
                      Q(user__username='grumpy') &
                      Q(public=True) &
                      Q(Q(review_request__repository=None) |
                        Q(review_request__repository__in=[])) &
                      Q(Q(review_request__target_people=user) |
                        Q(review_request__target_groups=None) |
                        Q(review_request__target_groups__in=[]))) &
                    Q(review_request__local_site=local_site)
                ),
            },
            {
                'model': Review,
                'select_related': {'review_request'},
                'where': Q(pk__in=[5, 4, 3, 2, 1]),
            },
            {
                'model': Profile,
                'where': Q(user=grumpy),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get(
                '%sreviews/' % self.get_datagrid_url(local_site=local_site))

        self.assertEqual(response.status_code, 200)

        datagrid = self._get_context_var(response, 'datagrid')
        assert datagrid is not None

        self.assertEqual(len(datagrid.rows), 5)
        self.assertEqual(datagrid.rows[0]['object'], reviews[4])
        self.assertEqual(datagrid.rows[1]['object'], reviews[3])
        self.assertEqual(datagrid.rows[2]['object'], reviews[2])
        self.assertEqual(datagrid.rows[3]['object'], reviews[1])
        self.assertEqual(datagrid.rows[4]['object'], reviews[0])
