"""Unit tests for reviewboard.reviews.manager.ReviewManager.

Version Added:
    5.0
"""

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import Review
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ReviewManagerTests(TestCase):
    """Unit tests for reviewboard.reviews.manager.ReviewManager.

    Version Added:
        5.0
    """

    fixtures = ['test_users']

    @add_fixtures(['test_scmtools'])
    def test_duplicate_reviews(self):
        """Testing ReviewManager.get_pending_review consolidation of duplicate
        reviews
        """
        body_top = 'This is the body_top.'
        body_bottom = 'This is the body_bottom.'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'

        # Some objects we need.
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the first review.
        master_review = self.create_review(review_request, user=user,
                                           body_top=body_top,
                                           body_bottom='')
        self.create_diff_comment(master_review, filediff, text=comment_text_1,
                                 first_line=1, num_lines=1)

        # Create the second review.
        review = self.create_review(review_request, user=user,
                                    body_top='', body_bottom='')
        self.create_diff_comment(review, filediff, text=comment_text_2,
                                 first_line=1, num_lines=1)

        # Create the third review.
        review = self.create_review(review_request, user=user,
                                    body_top='',
                                    body_bottom=body_bottom)
        self.create_diff_comment(review, filediff, text=comment_text_3,
                                 first_line=1, num_lines=1)

        # Now that we've made a mess, see if we get a single review back.
        review = review_request.get_pending_review(user)
        self.assertIsNotNone(review)
        self.assertEqual(review.id, master_review.id)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)

        comments = list(review.comments.all())
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)
        self.assertEqual(comments[2].text, comment_text_3)

    @add_fixtures(['test_scmtools'])
    def test_duplicate_replies(self):
        """Testing ReviewManager.get_pending_reply consolidation of duplicate
        replies
        """
        body_top = 'This is the body_top'
        body_bottom = 'This is the body_bottom'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'
        body_top_reply = 'This is the body_top reply'
        body_bottom_reply = 'This is the body_bottom reply'
        reply_text_1 = 'Reply text 1'
        reply_text_2 = 'Reply text 2'
        reply_text_3 = 'Reply text 3'

        # Some objects we need
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the parent review
        review = self.create_review(review_request,
                                    user=user,
                                    body_top=body_top,
                                    body_bottom=body_bottom,
                                    publish=True)
        comment1 = self.create_diff_comment(review,
                                            filediff,
                                            text=comment_text_1,
                                            first_line=1,
                                            num_lines=1)
        comment2 = self.create_diff_comment(review,
                                            filediff,
                                            text=comment_text_2,
                                            first_line=2,
                                            num_lines=1)
        comment3 = self.create_diff_comment(review,
                                            filediff,
                                            text=comment_text_3,
                                            first_line=3,
                                            num_lines=1)

        # Create several replies
        reply1 = self.create_reply(review, user=user, body_top=body_top_reply)
        self.create_diff_comment(reply1, filediff, text=reply_text_1,
                                 reply_to=comment1)

        reply2 = self.create_reply(review,
                                   user=user,
                                   body_top='',
                                   body_bottom=body_bottom_reply)
        self.create_diff_comment(reply2, filediff, text=reply_text_2,
                                 reply_to=comment2)

        reply3 = self.create_reply(review, user=user, body_top='')
        self.create_diff_comment(reply3, filediff, text=reply_text_3,
                                 reply_to=comment3)

        # Now that we've made a mess, see if we get a single reply back.
        reply = review.get_pending_reply(user)
        self.assertIsNotNone(reply)
        self.assertEqual(reply.body_top, body_top_reply)
        self.assertEqual(reply.body_bottom, body_bottom_reply)

        comments = list(reply.comments.all())
        self.assertEqual(len(comments), 3)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_reviews_and_review_requests(self):
        """Testing ReviewManager.accessible returns only public reviews
        from review requests that the user has access to and unpublished
        reviews that the user owns
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

        # 1 query:
        #
        # 1. Fetch reviews
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                Review.objects.accessible(anonymous),
                [review1, review3],
                ordered=False)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch reviews
        with self.assertNumQueries(5):
            self.assertQuerysetEqual(
                Review.objects.accessible(user),
                [review1, review3, review4],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch reviews
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                Review.objects.accessible(superuser),
                [review1, review2, review3, review4, review5, review6],
                ordered=False)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_repositories(self):
        """Testing ReviewManager.accessible returns only reviews from
        repositories that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')
        user2 = self.create_user()
        group1 = self.create_review_group()
        group2 = self.create_review_group()
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

        self.assertQuerysetEqual(
            Review.objects.accessible(anonymous),
            [review1])

        self.assertQuerysetEqual(
            Review.objects.accessible(user),
            [review1, review2, review3],
            ordered=False)

        self.assertQuerysetEqual(
            Review.objects.accessible(superuser),
            [review1, review2, review3, review4, review5, review6],
            ordered=False)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_review_group(self):
        """Testing ReviewManager.accessible returns only reviews associated
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
        repo = self.create_repository(public=False)
        repo.review_groups.add(group4)

        review_request1 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request2 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request3 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request4 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo)
        review_request1.target_groups.add(group1)
        review_request2.target_groups.add(group2)
        review_request3.target_groups.add(group3)
        review_request4.target_groups.add(group4)
        review1 = self.create_review(review_request1, publish=True)
        review2 = self.create_review(review_request2, publish=True)
        review3 = self.create_review(review_request3, publish=True)
        review4 = self.create_review(review_request4, publish=True)
        review5 = self.create_review(review_request5, publish=True)

        self.assertQuerysetEqual(
            Review.objects.accessible(anonymous),
            [review1, review3],
            ordered=False)

        self.assertQuerysetEqual(
            Review.objects.accessible(user),
            [review1, review2, review3],
            ordered=False)

        self.assertQuerysetEqual(
            Review.objects.accessible(superuser),
            [review1, review2, review3, review4, review5],
            ordered=False)

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_accessible_by_local_sites(self):
        """Testing ReviewManager.accessible returns only reviews from
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

        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     create_repository=True)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     create_repository=True)
        review_request3 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review1 = self.create_review(review_request1, publish=True, user=user)
        review2 = self.create_review(review_request2, user=user2, publish=True)
        review3 = self.create_review(review_request3, publish=True)

        # Call these to load the user profiles and local site profiles
        # into the cache in order to reduce the number of queries
        user.get_profile()
        user.get_site_profile(local_site=local_site1)
        user2.get_profile()
        user2.get_site_profile(local_site=local_site2)

        self.assertQuerysetEqual(
            Review.objects.accessible(anonymous),
            [review3])

        # 6 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group's auth permissions
        # 4. Fetch user's local site permissions
        # 5. Fetch user's accessible groups
        # 6. Fetch reviews
        with self.assertNumQueries(6):
            self.assertQuerysetEqual(
                Review.objects.accessible(user,
                                          local_site=local_site1),
                [review1])

        self.assertQuerysetEqual(
            Review.objects.accessible(user2,
                                      local_site=local_site2),
            [review2])

        self.assertQuerysetEqual(
            Review.objects.accessible(superuser),
            [review3],
            ordered=False)

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_accessible_with_show_all_local_sites(self):
        """Testing Review.objects.accessible with querying for all
        LocalSites
        """
        user = User.objects.get(username='doc')

        local_site1 = self.get_local_site(self.local_site_name)
        local_site2 = self.get_local_site('local-site-2')
        local_site1.users.add(user)
        local_site2.users.add(user)

        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     create_repository=True)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     create_repository=True)
        review_request3 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review1 = self.create_review(review_request1, publish=True)
        review2 = self.create_review(review_request2, publish=True)
        review3 = self.create_review(review_request3, publish=True)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch reviews
        with self.assertNumQueries(5):
            self.assertQuerysetEqual(
                Review.objects.accessible(user, local_site=LocalSite.ALL),
                [review1, review2, review3],
                ordered=False)

    def test_accessible_with_extra_query(self):
        """Testing Review.objects.accessible with extra query parameters"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request,
                                    body_top='hello',
                                    publish=True)
        self.create_review(review_request, publish=True)
        q = Q(body_top='hello')

        self.assertQuerysetEqual(
            Review.objects.accessible(user, extra_query=q),
            [review])

    @add_fixtures(['test_scmtools'])
    def test_from_user(self):
        """Testing Review.objects.from_user"""
        user = User.objects.get(username='doc')
        user2 = self.create_user()
        repo = self.create_repository(public=True)
        review_request = self.create_review_request(publish=True,
                                                    repository=repo)
        review = self.create_review(review_request, publish=True, user=user)
        review2 = self.create_review(review_request, publish=True, user=user2)

        # 1 query:
        #
        # 1. Fetch reviews
        with self.assertNumQueries(1):
            self.assertQuerysetEqual(
                Review.objects.from_user(user),
                [review])

        self.assertQuerysetEqual(
            Review.objects.from_user(user2),
            [review2])
