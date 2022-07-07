"""Unit tests for reviewboard.reviews.manager.CommentManager.

Version Added:
    5.0
"""

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import GeneralComment
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

        repo = self.create_repository(public=False)
        review_request_inaccessible = \
            self.create_review_request(repository=repo)
        review_request = self.create_review_request(publish=True)
        review1 = self.create_review(review_request, publish=True)
        review2 = self.create_review(review_request, publish=False)
        review3 = self.create_review(review_request, user=user, publish=True)
        review4 = self.create_review(review_request, user=user, publish=False)
        review5 = self.create_review(review_request_inaccessible, publish=True)
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)

        comment1 = self.create_general_comment(review1)
        comment2 = self.create_general_comment(review2)
        comment3 = self.create_general_comment(review3)
        comment4 = self.create_general_comment(review4)
        comment5 = self.create_general_comment(review5)
        comment6 = self.create_general_comment(review6)

        # 1 query:
        #
        # 1. Fetch comments
        with self.assertNumQueries(1):
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
        with self.assertNumQueries(5):
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user),
                [comment1, comment3, comment4],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch comments
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(superuser),
                [comment1, comment2, comment3, comment4, comment5, comment6],
                ordered=False)

    def test_accessible_by_repositories(self):
        """Testing CommentManager.accessible returns only comments from
        repositories that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')
        user2 = self.create_user()

        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')
        group1.users.add(user)

        repo1 = self.create_repository(name='repo1', public=True)
        repo2 = self.create_repository(name='repo2', public=False)
        repo3 = self.create_repository(name='repo3', public=False)
        repo4 = self.create_repository(name='repo4', public=False)
        repo5 = self.create_repository(name='repo5', public=False)
        repo6 = self.create_repository(name='repo6', public=False)
        repo2.users.add(user)
        repo3.review_groups.add(group1)
        repo5.users.add(user2)
        repo6.review_groups.add(group2)

        review_request1 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review_request2 = self.create_review_request(publish=True,
                                                     repository=repo2)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo3)
        review_request4 = self.create_review_request(publish=True,
                                                     repository=repo4)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo5)
        review_request6 = self.create_review_request(publish=True,
                                                     repository=repo6)
        review1 = self.create_review(review_request1, publish=True)
        review2 = self.create_review(review_request2, publish=True)
        review3 = self.create_review(review_request3, publish=True)
        review4 = self.create_review(review_request4, publish=True)
        review5 = self.create_review(review_request5, publish=True)
        review6 = self.create_review(review_request6, publish=True)

        comment1 = self.create_general_comment(review1)
        comment2 = self.create_general_comment(review2)
        comment3 = self.create_general_comment(review3)
        comment4 = self.create_general_comment(review4)
        comment5 = self.create_general_comment(review5)
        comment6 = self.create_general_comment(review6)

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(anonymous),
            [comment1])

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(user),
            [comment1, comment2, comment3],
            ordered=False)

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(superuser),
            [comment1, comment2, comment3, comment4, comment5, comment6],
            ordered=False)

    def test_accessible_by_review_group(self):
        """Testing CommentManager.accessible returns only comments associated
        with review groups that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        group1 = self.create_review_group(name='group1', invite_only=False)
        group2 = self.create_review_group(name='group2', invite_only=True)
        group3 = self.create_review_group(name='group3', invite_only=False)
        group4 = self.create_review_group(name='group4', invite_only=True)
        group1.users.add(user)
        group2.users.add(user)

        repo1 = self.create_repository(name='repo1',)

        repo2 = self.create_repository(name='repo2',
                                       public=False)
        repo2.review_groups.add(group4)

        review_request1 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review_request2 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review_request4 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo2)

        review_request1.target_groups.add(group1)
        review_request2.target_groups.add(group2)
        review_request3.target_groups.add(group3)
        review_request4.target_groups.add(group4)

        review1 = self.create_review(review_request1, publish=True)
        review2 = self.create_review(review_request2, publish=True)
        review3 = self.create_review(review_request3, publish=True)
        review4 = self.create_review(review_request4, publish=True)
        review5 = self.create_review(review_request5, publish=True)

        comment1 = self.create_general_comment(review1)
        comment2 = self.create_general_comment(review2)
        comment3 = self.create_general_comment(review3)
        comment4 = self.create_general_comment(review4)
        comment5 = self.create_general_comment(review5)

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(anonymous),
            [comment1, comment3],
            ordered=False)

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(user),
            [comment1, comment2, comment3],
            ordered=False)

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(superuser),
            [comment1, comment2, comment3, comment4, comment5],
            ordered=False)

    @add_fixtures(['test_site'])
    def test_accessible_by_local_sites(self):
        """Testing CommentManager.accessible returns only comments from
        local sites that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        user2 = self.create_user()
        superuser = User.objects.get(username='admin')

        local_site1 = self.get_local_site(self.local_site_name)
        local_site2 = self.get_local_site('local-site-2')
        local_site1.users.add(user)
        local_site2.users.add(user2)

        repo1 = self.create_repository(name='repo1',
                                       local_site=local_site1)
        repo2 = self.create_repository(name='repo2',
                                       local_site=local_site2)
        repo3 = self.create_repository(name='repo3')

        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo3)

        review1 = self.create_review(review_request1, publish=True, user=user)
        review2 = self.create_review(review_request2, user=user2, publish=True)
        review3 = self.create_review(review_request3, publish=True)
        comment1 = self.create_general_comment(review1)
        comment2 = self.create_general_comment(review2)
        comment3 = self.create_general_comment(review3)

        # Call these to load the user profiles and local site profiles
        # into the cache in order to reduce the number of queries
        user.get_profile()
        user.get_site_profile(local_site=local_site1)
        user2.get_profile()
        user2.get_site_profile(local_site=local_site2)

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(anonymous),
            [comment3])

        # 6 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group's auth permissions
        # 4. Fetch user's local site permissions
        # 5. Fetch user's accessible groups
        # 6. Fetch comments
        with self.assertNumQueries(6):
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user,
                                                  local_site=local_site1),
                [comment1])

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(user2,
                                              local_site=local_site2),
            [comment2])

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(superuser),
            [comment3],
            ordered=False)

    @add_fixtures(['test_site'])
    def test_accessible_with_show_all_local_sites(self):
        """Testing CommentManager.accessible with querying for all
        LocalSites
        """
        user = User.objects.get(username='doc')

        local_site1 = self.get_local_site(self.local_site_name)
        local_site2 = self.get_local_site('local-site-2')
        local_site1.users.add(user)
        local_site2.users.add(user)

        repo1 = self.create_repository(name='repo1',
                                       local_site=local_site1)
        repo2 = self.create_repository(name='repo2',
                                       local_site=local_site2)
        repo3 = self.create_repository(name='repo3')

        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo3)

        review1 = self.create_review(review_request1, publish=True)
        review2 = self.create_review(review_request2, publish=True)
        review3 = self.create_review(review_request3, publish=True)

        comment1 = self.create_general_comment(review1)
        comment2 = self.create_general_comment(review2)
        comment3 = self.create_general_comment(review3)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch comments
        with self.assertNumQueries(5):
            self.assertQuerysetEqual(
                GeneralComment.objects.accessible(user,
                                                  local_site=LocalSite.ALL),
                [comment1, comment2, comment3],
                ordered=False)

    def test_accessible_with_extra_query(self):
        """Testing Comment.objects.accessible with extra query parameters"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        general_comment = self.create_general_comment(review, text='hello')
        self.create_general_comment(review)
        q = Q(text='hello')

        self.assertQuerysetEqual(
            GeneralComment.objects.accessible(user, extra_query=q),
            [general_comment])

    def test_from_user(self):
        """Testing CommentManager.from_user"""
        user = User.objects.get(username='doc')
        user2 = self.create_user()
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True, user=user)
        general_comment = self.create_general_comment(review)
        review2 = self.create_review(review_request, publish=True, user=user2)
        general_comment2 = self.create_general_comment(review2)

        # 1 query:
        #
        # 1. Fetch comments
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                GeneralComment.objects.from_user(user),
                [general_comment])

        self.assertQuerysetEqual(
            GeneralComment.objects.from_user(user2),
            [general_comment2])
