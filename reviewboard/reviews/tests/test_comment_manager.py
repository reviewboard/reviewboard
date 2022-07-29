"""Unit tests for reviewboard.reviews.manager.CommentManager.

Version Added:
    5.0
"""

from django.contrib.auth.models import AnonymousUser, Permission, User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import GeneralComment, Group
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class CommentManagerTests(TestCase):
    """Unit tests for reviewboard.reviews.manager.CommentManager.

    Version Added:
        5.0
    """

    fixtures = ['test_scmtools', 'test_users']

    def test_accessible_by_reviews_and_review_requests(self):
        """Testing CommentManager.accessible returns only comments from
        public reviews and review requests that the user has access to
        and unpublished reviews that the user owns
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        # Publicly-accessible published review request.
        review_request = self.create_review_request(publish=True)

        # Comment from a published review on a publicly-accessible
        # review request.
        review1 = self.create_review(review_request, publish=True)
        comment1 = self.create_general_comment(review1)

        # Comment from an unpublished review on a publicly-accessible
        # review request.
        review2 = self.create_review(review_request, publish=False)
        comment2 = self.create_general_comment(review2)

        # Comment from a published review owned by the user on a
        # publicly-accessible review request.
        review3 = self.create_review(review_request, user=user, publish=True)
        comment3 = self.create_general_comment(review3)

        # Comment from an unpublished review owned by the user on a
        # publicly-accessible review request.
        review4 = self.create_review(review_request, user=user, publish=False)
        comment4 = self.create_general_comment(review4)

        # Published review request from a private repository the user
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True)

        # Comment from a published review on a private repository the user
        # does not have access to.
        review5 = self.create_review(review_request_inaccessible, publish=True)
        comment5 = self.create_general_comment(review5)

        # Comment from an unpublished review on a private repository the user
        # does not have access to.
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)
        comment6 = self.create_general_comment(review6)

        # An invite-only review group used to limit access for the following
        # review requests.
        group = self.create_review_group(invite_only=True)

        # Comment from a published review from a review request that has an
        # invite-only review group not accessible to the user, but the user
        # has access to through being a targeted reviewer.
        review_request_targetted = self.create_review_request(publish=True)
        review_request_targetted.target_groups.add(group)
        review_request_targetted.target_people.add(user)
        review7 = self.create_review(review_request_targetted, publish=True)
        comment7 = self.create_general_comment(review7)

        # Comment from a published review from a review request that has an
        # invite-only review group not accessible to the user, and that the
        # user does not have access to because the user is not listed as a
        # target reviewer.
        review_request_untargetted = self.create_review_request(publish=True)
        review_request_untargetted.target_groups.add(group)
        review8 = self.create_review(review_request_untargetted, publish=True)
        comment8 = self.create_general_comment(review8)

        # 1 query:
        #
        # 1. Fetch comments
        queries_anonymous = [
            {
                'model': GeneralComment,
                'num_joins': 6,
                'tables': {
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_group',
                    'reviews_generalcomment',
                    'reviews_reviewrequest',
                    'scmtools_repository',
                    'reviews_reviewrequest_target_groups',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    (Q(review__review_request__repository=None) |
                     Q(review__review_request__repository__public=True)) &
                    (Q(review__review_request__target_groups=None) |
                     Q(review__review_request__target_groups__invite_only=False
                       )) &
                    Q(review__public=True)
                ),
            },
        ]

        with self.assertQueries(queries_anonymous):
            # Testing that anonymous users can only access publicly-accessible
            # comments.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(anonymous),
                [comment1, comment3],
                ordered=False)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch comments
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': GeneralComment,
                'num_joins': 5,
                'tables': {
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_generalcomment',
                    'reviews_reviewrequest_target_people',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review_general_comments',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    (Q(review__user=user) |
                     (Q(review__public=True) &
                      (Q(review__review_request__repository=None) |
                       Q(review__review_request__repository__in=[])) &
                      (Q(review__review_request__target_people=user) |
                       Q(review__review_request__target_groups=None) |
                       Q(review__review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the user can only access publicly-accessible
            # comments and comments from reviews that they own.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user),
                [comment1, comment3, comment4, comment7],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch comments
        queries_superuser = [
            {
                'model': GeneralComment,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_generalcomment',
                },
                'where': (
                    Q(review__review_request__local_site=None)
                ),
            },
        ]

        with self.assertQueries(queries_superuser):
            # Testing that superusers can acess any comments.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(superuser),
                [
                    comment1, comment2, comment3, comment4,
                    comment5, comment6, comment7, comment8,
                ],
                ordered=False)

    def test_accessible_by_repositories(self):
        """Testing CommentManager.accessible returns only comments from
        repositories that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        # Comment from a public repository.
        repo1 = self.create_repository(name='repo1', public=True)
        review_request1 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self.create_general_comment(review1)

        # Comment from a private repository that the user has
        # access to from being listed in the repository's users list.
        repo2 = self.create_repository(name='repo2', public=False)
        repo2.users.add(user)
        review_request2 = self.create_review_request(publish=True,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)
        comment2 = self.create_general_comment(review2)

        # An invite-only review group that the user has access to.
        group_accessible = self.create_review_group(invite_only=True)
        group_accessible.users.add(user)

        # Comment from a private repository that the user has
        # access to through being a member of a targeted review group.
        repo3 = self.create_repository(name='repo3', public=False)
        repo3.review_groups.add(group_accessible)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)
        comment3 = self.create_general_comment(review3)

        # Comment from a private repository that the user does
        # not have access to.
        repo4 = self.create_repository(name='repo4', public=False)
        review_request4 = self.create_review_request(publish=True,
                                                     repository=repo4)
        review4 = self.create_review(review_request4, publish=True)
        comment4 = self.create_general_comment(review4)

        # Comment from a private repository that the user has access
        # to through being a member of a targeted review group and
        # being listed on the repository's users list.
        repo5 = self.create_repository(name='repo5', public=False)
        repo5.review_groups.add(group_accessible)
        repo5.users.add(user)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo5)
        review5 = self.create_review(review_request5, publish=True)
        comment5 = self.create_general_comment(review5)

        # An invite-only review group that the user does not have access to.
        group_inaccessible = self.create_review_group(invite_only=True)

        # Comment from a private repository that targets an invite-only review
        # group, but that the user has access to from being listed in the
        # repository's users list.
        repo6 = self.create_repository(name='repo6', public=False)
        repo6.review_groups.add(group_inaccessible)
        repo6.users.add(user)
        review_request6 = self.create_review_request(publish=True,
                                                     repository=repo6)
        review6 = self.create_review(review_request6, publish=True)
        comment6 = self.create_general_comment(review6)

        # Comment from a private repository that targets an invite-only review
        # group and that the user does not have access to.
        repo7 = self.create_repository(name='repo7', public=False)
        repo7.review_groups.add(group_inaccessible)
        review_request7 = self.create_review_request(publish=True,
                                                     repository=repo7)
        review7 = self.create_review(review_request7, publish=True)
        comment7 = self.create_general_comment(review7)

        # 1 query:
        #
        # 1. Fetch comments
        queries_anonymous = [
            {
                'model': GeneralComment,
                'num_joins': 6,
                'tables': {
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_group',
                    'reviews_generalcomment',
                    'reviews_reviewrequest',
                    'scmtools_repository',
                    'reviews_reviewrequest_target_groups',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    (Q(review__review_request__repository=None) |
                     Q(review__review_request__repository__public=True)) &
                    (Q(review__review_request__target_groups=None) |
                     Q(review__review_request__target_groups__invite_only=False
                       )) &
                    Q(review__public=True)
                ),
            },
        ]

        with self.assertQueries(queries_anonymous):
            # Testing that anonymous users can only access comments
            # from publicly-accessible repositories.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(anonymous),
                [comment1])

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch comments
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': GeneralComment,
                'num_joins': 5,
                'tables': {
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_generalcomment',
                    'reviews_reviewrequest_target_people',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review_general_comments',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    (Q(review__user=user) |
                     (Q(review__public=True) &
                      (Q(review__review_request__repository=None) |
                       Q(review__review_request__repository__in=[
                        repo1.pk, repo2.pk, repo3.pk, repo5.pk, repo6.pk,
                       ])) &
                      (Q(review__review_request__target_people=user) |
                       Q(review__review_request__target_groups=None) |
                       Q(review__review_request__target_groups__in=[
                        group_accessible.pk
                       ]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the user can only access comments
            # from repositories that they have access to.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user),
                [comment1, comment2, comment3, comment5, comment6],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch comments
        queries_superuser = [
            {
                'model': GeneralComment,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_generalcomment',
                },
                'where': (
                    Q(review__review_request__local_site=None)
                ),
            },
        ]

        with self.assertQueries(queries_superuser):
            # Testing that superusers can acess comments from any repository.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(superuser),
                [
                    comment1, comment2, comment3, comment4,
                    comment5, comment6, comment7,
                ],
                ordered=False)

    def test_accessible_by_review_group(self):
        """Testing CommentManager.accessible returns only comments associated
        with review groups that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        # Comment that the user has access to from being in a public
        # review group that is targeted by the review request.
        group1 = self.create_review_group(name='group1', invite_only=False)
        group1.users.add(user)
        review_request1 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request1.target_groups.add(group1)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self.create_general_comment(review1)

        # Comment that the user has access to from being in an invite-only
        # review group that is targeted by the review request.
        group2 = self.create_review_group(name='group2', invite_only=True)
        group2.users.add(user)
        review_request2 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request2.target_groups.add(group2)
        review2 = self.create_review(review_request2, publish=True)
        comment2 = self.create_general_comment(review2)

        # Comment that the user has access to since there is a public
        # review group that is targeted by the review request.
        group3 = self.create_review_group(name='group3', invite_only=False)
        review_request3 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request3.target_groups.add(group3)
        review3 = self.create_review(review_request3, publish=True)
        comment3 = self.create_general_comment(review3)

        # Comment that the user does not have access to since there is an
        # invite-only review group that is targeted by the review request.
        group4 = self.create_review_group(name='group4', invite_only=True)
        review_request4 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request4.target_groups.add(group4)
        review4 = self.create_review(review_request4, publish=True)
        comment4 = self.create_general_comment(review4)

        # 1 query:
        #
        # 1. Fetch comments
        queries_anonymous = [
            {
                'model': GeneralComment,
                'num_joins': 6,
                'tables': {
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_group',
                    'reviews_generalcomment',
                    'reviews_reviewrequest',
                    'scmtools_repository',
                    'reviews_reviewrequest_target_groups',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    (Q(review__review_request__repository=None) |
                     Q(review__review_request__repository__public=True)) &
                    (Q(review__review_request__target_groups=None) |
                     Q(review__review_request__target_groups__invite_only=False
                       )) &
                    Q(review__public=True)
                ),
            },
        ]

        with self.assertQueries(queries_anonymous):
            # Testing that anonymous users can only access comments
            # from review requests that target public review groups.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(anonymous),
                [comment1, comment3],
                ordered=False)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch comments
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': GeneralComment,
                'num_joins': 5,
                'tables': {
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_generalcomment',
                    'reviews_reviewrequest_target_people',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review_general_comments',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    (Q(review__user=user) |
                     (Q(review__public=True) &
                      (Q(review__review_request__repository=None) |
                       Q(review__review_request__repository__in=[
                        group1.pk, group2.pk, group3.pk, group4.pk,
                       ])) &
                      (Q(review__review_request__target_people=user) |
                       Q(review__review_request__target_groups=None) |
                       Q(review__review_request__target_groups__in=[
                        group1.pk, group2.pk, group3.pk,
                       ]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the user can only access comments
            # from review requests that target them directly or target
            # review groups they have access to.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user),
                [comment1, comment2, comment3],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch comments
        queries_superuser = [
            {
                'model': GeneralComment,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_generalcomment',
                },
                'where': (
                    Q(review__review_request__local_site=None)
                ),
            },
        ]

        with self.assertQueries(queries_superuser):
            # Testing that superusers can access any comments associated to
            # any review groups.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(superuser),
                [comment1, comment2, comment3, comment4],
                ordered=False)

    @add_fixtures(['test_site'])
    def test_accessible_by_local_sites(self):
        """Testing CommentManager.accessiblee(local_site=) returns only
        comments from the given local site
        """
        user = User.objects.get(username='doc')

        # Comment from a private local site that the user has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(user)
        repo1 = self.create_repository(local_site=local_site1)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self.create_general_comment(review1)

        # Comment from a private local site that the user does not have
        # access to.
        local_site2 = self.get_local_site('local-site-2')
        repo2 = self.create_repository(local_site=local_site2)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)
        self.create_general_comment(review2)

        # Comment from a public local site.
        local_site3 = self.create_local_site('public-local-site', public=True)
        repo3 = self.create_repository(local_site=local_site3)
        review_request3 = self.create_review_request(publish=True,
                                                     local_site=local_site3,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)
        self.create_general_comment(review3)

        # Comment from a global site.
        review_request4 = self.create_review_request(publish=True)
        review4 = self.create_review(review_request4, publish=True)
        comment4 = self.create_general_comment(review4)

        # Load the user profiles and local site profiles into the cache
        # so that these don't influence the query counts.
        user.get_profile()
        user.get_site_profile(local_site=local_site1)

        # 6 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group's auth permissions
        # 4. Fetch user's local site permissions
        # 5. Fetch user's accessible groups
        # 6. Fetch comments
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=local_site1)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': User,
                'extra': {
                    'a': ('1', [])
                },
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'site_localsite_admins',
                },
                'where': (
                    Q(local_site_admins__id=local_site1.pk) &
                    Q(pk=user.pk)
                ),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=local_site1)
                ),
            },
            {
                'model': GeneralComment,
                'num_joins': 5,
                'tables': {
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_generalcomment',
                    'reviews_reviewrequest_target_people',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review_general_comments',
                },
                'where': (
                    Q(review__review_request__local_site=local_site1) &
                    (Q(review__user=user) |
                     (Q(review__public=True) &
                      (Q(review__review_request__repository=None) |
                       Q(review__review_request__repository__in=[repo1.pk])) &
                      (Q(review__review_request__target_people=user) |
                       Q(review__review_request__target_groups=None) |
                       Q(review__review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the comments from other local sites or the global
            # site do not leak into the results from the given local site.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user,
                                                  local_site=local_site1),
                [comment1])

        # Testing that the comments from local sites
        # do not leak into the results from the global site.
        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(user),
            [comment4])

    @add_fixtures(['test_site'])
    def test_accessible_with_show_all_local_sites(self):
        """Testing CommentManager.accessible(local_site=) with querying for
        all local sites
        """
        user = User.objects.get(username='doc')

        # Comment from a private local site that the user has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(user)
        repo1 = self.create_repository(local_site=local_site1)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self.create_general_comment(review1)

        # Comment from a private local site that the user does not have
        # access to.
        local_site2 = self.get_local_site('local-site-2')
        repo2 = self.create_repository(local_site=local_site2)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)
        comment2 = self.create_general_comment(review2)

        # Comment from a public local site.
        local_site3 = self.create_local_site('public-local-site', public=True)
        repo3 = self.create_repository(local_site=local_site3)
        review_request3 = self.create_review_request(publish=True,
                                                     local_site=local_site3,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)
        comment3 = self.create_general_comment(review3)

        # Comment from a global site.
        review_request4 = self.create_review_request(publish=True)
        review4 = self.create_review(review_request4, publish=True)
        comment4 = self.create_general_comment(review4)

        # Load the user profiles and local site profiles into the cache
        # so that these don't influence the query counts.
        user.get_profile()
        user.get_site_profile(local_site=local_site1)

        # 6 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group's auth permissions
        # 4. Fetch user's local site permissions
        # 5. Fetch user's accessible groups
        # 6. Fetch comments
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    Q(public=True) |
                    Q(users__pk=user.pk) |
                    Q(review_groups__users=user.pk)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    Q(invite_only=False) |
                    Q(users=user.pk)
                ),
            },
            {
                'model': GeneralComment,
                'num_joins': 5,
                'tables': {
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_generalcomment',
                    'reviews_reviewrequest_target_people',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review_general_comments',
                },
                'where': (
                    (Q(review__user=user) |
                     (Q(review__public=True) &
                      (Q(review__review_request__repository=None) |
                       Q(review__review_request__repository__in=[
                        repo1.pk, repo2.pk, repo3.pk
                       ])) &
                      (Q(review__review_request__target_people=user) |
                       Q(review__review_request__target_groups=None) |
                       Q(review__review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that passing LocalSite.ALL returns reviews from all local
            # sites and the global site.
            #
            # Note that this does not test for local site access, since callers
            # of Review.objects.accessible are responsible for ensuring that
            # the user has access to the given local site(s).
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user,
                                                  local_site=LocalSite.ALL),
                [comment1, comment2, comment3, comment4],
                ordered=False)

    def test_accessible_with_extra_query(self):
        """Testing Comment.objects.accessible with extra query parameters"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        comment = self.create_general_comment(review, text='hello')
        self.create_general_comment(review)
        extra_query = Q(text='hello')

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch comments
        queries = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': GeneralComment,
                'num_joins': 5,
                'tables': {
                    'reviews_review',
                    'reviews_reviewrequest',
                    'reviews_generalcomment',
                    'reviews_reviewrequest_target_people',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review_general_comments',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    Q(text='hello') &
                    (Q(review__user=user) |
                     (Q(review__public=True) &
                      (Q(review__review_request__repository=None) |
                       Q(review__review_request__repository__in=[])) &
                      (Q(review__review_request__target_people=user) |
                       Q(review__review_request__target_groups=None) |
                       Q(review__review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries):
            # Testing that only comments matching the extra query are returned.
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user,
                                                  extra_query=extra_query),
                [comment])

    def test_from_user(self):
        """Testing CommentManager.from_user"""
        user = User.objects.get(username='doc')
        user2 = self.create_user()
        review_request = self.create_review_request(publish=True)

        review = self.create_review(review_request, publish=True, user=user)
        comment = self.create_general_comment(review)

        review2 = self.create_review(review_request, publish=True, user=user2)
        self.create_general_comment(review2)

        # 1 query:
        #
        # 1. Fetch comments
        queries = [
            {
                'model': GeneralComment,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_generalcomment',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    Q(review__review_request__status='P') &
                    Q(review__user=user)
                ),
            },
        ]

        with self.assertQueries(queries):
            # Testing that only comments from the given user are returned.
            self.assertQuerysetEqual(
                GeneralComment.objects.from_user(user),
                [comment])

    def test_from_user_with_public(self):
        """Testing CommentManager.from_user with filtering for comments from
        public reviews
        """
        user = User.objects.get(username='doc')
        user2 = self.create_user()
        review_request = self.create_review_request(publish=True)

        review1 = self.create_review(review_request, publish=True, user=user)
        comment1 = self.create_general_comment(review1)

        review2 = self.create_review(review_request, publish=False, user=user)
        self.create_general_comment(review2)

        review3 = self.create_review(review_request, publish=True, user=user2)
        self.create_general_comment(review3)

        # 1 query:
        #
        # 1. Fetch comments
        queries = [
            {
                'model': GeneralComment,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                    'reviews_review_general_comments',
                    'reviews_generalcomment',
                },
                'where': (
                    Q(review__review_request__local_site=None) &
                    Q(review__review_request__status='P') &
                    Q(review__user=user) &
                    Q(review__public=True)
                ),
            },
        ]

        with self.assertQueries(queries):
            # Testing that only comments from published reviews by the given
            # user are returned.
            self.assertQuerysetEqual(
                GeneralComment.objects.from_user(user, public=True),
                [comment1])
