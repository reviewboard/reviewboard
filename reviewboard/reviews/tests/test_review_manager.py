"""Unit tests for reviewboard.reviews.manager.ReviewManager.

Version Added:
    5.0
"""

from __future__ import annotations

from typing import List, Optional, Sequence, TYPE_CHECKING

from django_assert_queries.testing import assert_queries
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import Review
from reviewboard.reviews.testing.queries.reviews import (
    get_reviews_accessible_equeries,
    get_reviews_from_user_equeries,
)
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from typelets.funcs import KwargsDict


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

        # Some objects we need.
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the parent review.
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

        # Create several replies.
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
        self._test_accessible_by_reviews_and_review_request()

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_by_reviews_and_review_requests_local_site_in_db(self):
        """Testing ReviewManager.accessible returns only public reviews
        from review requests that the user has access to and unpublished
        reviews that the user owns, with Local Sites in the database
        """
        self._test_accessible_by_reviews_and_review_request(
            local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_by_reviews_and_review_requests_local_site(self):
        """Testing ReviewManager.accessible returns only public reviews
        from review requests that the user has access to and unpublished
        reviews that the user owns, with a Local Site
        """
        self._test_accessible_by_reviews_and_review_request(
            with_local_site=True,
            local_sites_in_db=True)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_repositories(self):
        """Testing ReviewManager.accessible returns only reviews from
        repositories that the user has access to
        """
        self._test_accessible_by_repositories()

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_by_repositories_local_site_in_db(self):
        """Testing ReviewManager.accessible returns only reviews from
        repositories that the user has access to, with Local Sites in the
        database
        """
        self._test_accessible_by_repositories(local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_by_repositories_local_site(self):
        """Testing ReviewManager.accessible returns only reviews from
        repositories that the user has access to, with Local Site
        """
        self._test_accessible_by_repositories(with_local_site=True,
                                              local_sites_in_db=True)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_review_group(self):
        """Testing ReviewManager.accessible returns only reviews associated
        with review groups that the user has access to
        """
        self._test_accessible_by_review_group()

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_by_review_group_local_site_in_db(self):
        """Testing ReviewManager.accessible returns only reviews associated
        with review groups that the user has access to, with Local Sites in
        the database
        """
        self._test_accessible_by_review_group(local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_by_review_group_local_site(self):
        """Testing ReviewManager.accessible returns only reviews associated
        with review groups that the user has access to, with Local Site
        """
        self._test_accessible_by_review_group(with_local_site=True,
                                              local_sites_in_db=True)

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_accessible_by_local_sites(self):
        """Testing ReviewManager.accessible(local_site=) returns only reviews
        from the given local site
        """
        user = User.objects.get(username='doc')

        # Review from a private local site that the user has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(user)
        repo1 = self.create_repository(local_site=local_site1)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)

        # Review from a private local site that the user does not have
        # access to.
        local_site2 = self.get_local_site('local-site-2')
        repo2 = self.create_repository(local_site=local_site2)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        self.create_review(review_request2, publish=True)

        # Review from a public local site.
        local_site3 = self.create_local_site('public-local-site', public=True)
        repo3 = self.create_repository(local_site=local_site3)
        review_request3 = self.create_review_request(publish=True,
                                                     local_site=local_site3,
                                                     repository=repo3)
        self.create_review(review_request3, publish=True)

        # Review from a global site.
        review_request4 = self.create_review_request(publish=True)
        review4 = self.create_review(review_request4, publish=True)

        self._prime_caches(user=user,
                           local_site=local_site1)

        equeries = get_reviews_accessible_equeries(
            user=user,
            local_site=local_site1,
            has_local_sites_in_db=True,
            accessible_repository_ids=[repo1.pk])

        with assert_queries(equeries):
            # Testing that the reviews from other local sites or the global
            # site do not leak into the results from the given local site.
            self.assertQuerySetEqual(
                Review.objects.accessible(user, local_site=local_site1),
                [review1])

        # Testing that the reviews from local sites
        # do not leak into the results from the global site.
        self.assertQuerySetEqual(
            Review.objects.accessible(user),
            [review4])

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_accessible_with_show_all_local_sites(self):
        """Testing Review.objects.accessible(local_site=) with querying for
        all local sites
        """
        user = User.objects.get(username='doc')

        # Review from a private local site that the user has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(user)
        repo1 = self.create_repository(local_site=local_site1)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)

        # Review from another private local site that the user has access to.
        local_site2 = self.get_local_site('local-site-2')
        local_site2.users.add(user)
        repo2 = self.create_repository(local_site=local_site2)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)

        # Review from a public local site.
        local_site3 = self.create_local_site('public-local-site', public=True)
        repo3 = self.create_repository(local_site=local_site3)
        review_request3 = self.create_review_request(publish=True,
                                                     local_site=local_site3,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)

        # Review from a global site.
        review_request4 = self.create_review_request(publish=True)
        review4 = self.create_review(review_request4, publish=True)

        equeries = get_reviews_accessible_equeries(
            user=user,
            local_site=LocalSite.ALL,
            has_local_sites_in_db=True,
            accessible_repository_ids=[
                repo1.pk,
                repo2.pk,
                repo3.pk,
            ])

        with assert_queries(equeries):
            # Testing that passing LocalSite.ALL returns reviews from all local
            # sites and the global site.
            #
            # Note that this does not test for local site access, since callers
            # of Review.objects.accessible are responsible for ensuring that
            # the user has access to the given local site(s).
            self.assertQuerySetEqual(
                Review.objects.accessible(user, local_site=LocalSite.ALL),
                [review1, review2, review3, review4])

    @add_fixtures(['test_scmtools'])
    def test_accessible_with_public_true(self):
        """Testing ReviewManager.accessible(public=True) returns only public
        reviews from review requests that the user has access to and no
        unpublished reviews
        """
        self._test_accessible_with_public(expected_public=True)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_with_public_true_local_sites_in_db(self):
        """Testing ReviewManager.accessible(public=True) returns only
        unpublished reviews that the user owns and no public reviews, with
        Local Sites in the database
        """
        self._test_accessible_with_public(expected_public=True,
                                          local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_with_public_true_local_site(self):
        """Testing ReviewManager.accessible(public=True) returns only
        unpublished reviews that the user owns and no public reviews, with
        Local Site
        """
        self._test_accessible_with_public(expected_public=True,
                                          with_local_site=True,
                                          local_sites_in_db=True)

    @add_fixtures(['test_scmtools'])
    def test_accessible_with_public_false(self):
        """Testing ReviewManager.accessible(public=False) returns only
        unpublished reviews that the user owns and no public reviews
        """
        self._test_accessible_with_public(expected_public=False)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_with_public_false_local_sites_in_db(self):
        """Testing ReviewManager.accessible(public=False) returns only
        unpublished reviews that the user owns and no public reviews, with
        Local Sites in the database
        """
        self._test_accessible_with_public(expected_public=False,
                                          local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_accessible_with_public_false_local_site(self):
        """Testing ReviewManager.accessible(public=False) returns only
        unpublished reviews that the user owns and no public reviews, with
        Local Site
        """
        self._test_accessible_with_public(expected_public=False,
                                          with_local_site=True,
                                          local_sites_in_db=True)

    def test_accessible_with_extra_query(self):
        """Testing Review.objects.accessible with extra query parameters"""
        self._test_accessible_with_extra_query()

    @add_fixtures(['test_site'])
    def test_accessible_with_extra_query_local_site_in_db(self):
        """Testing Review.objects.accessible with extra query parameters,
        with Local Sites in the database
        """
        self._test_accessible_with_extra_query(local_sites_in_db=True)

    @add_fixtures(['test_site'])
    def test_accessible_with_extra_query_local_site(self):
        """Testing Review.objects.accessible with extra query parameters,
        with Local Site
        """
        self._test_accessible_with_extra_query(with_local_site=True,
                                               local_sites_in_db=True)

    @add_fixtures(['test_scmtools'])
    def test_from_user(self) -> None:
        """Testing Review.objects.from_user with local_site=None"""
        self._test_accessible_with_from_user()

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_from_user_local_site_in_db(self) -> None:
        """Testing Review.objects.from_user with local_site=None, with
        Local Sites in the database
        """
        self._test_accessible_with_from_user(local_sites_in_db=True)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_from_user_local_site(self) -> None:
        """Testing Review.objects.from_user with local_site=None, with
        Local Sites
        """
        self._test_accessible_with_from_user(with_local_site=True,
                                             local_sites_in_db=True)

    def _test_accessible_by_repositories(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Helper for repository-related review accessibility tests.

        This tests that ReviewManager.accessible() returns only reviews
        associated with repositories that the user has access to.

        Args:
            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        # Review from a public repository.
        repo1 = self.create_repository(
            name='repo1',
            public=True,
            local_site=local_site)
        review_request1 = self.create_review_request(
            publish=True,
            repository=repo1,
            local_site=local_site,
            local_id=1)
        review1 = self.create_review(review_request1, publish=True)

        # Review from a private repository that the user has
        # access to from being listed in the repository's users list.
        repo2 = self.create_repository(
            name='repo2',
            public=False,
            local_site=local_site)
        repo2.users.add(user)
        review_request2 = self.create_review_request(
            publish=True,
            repository=repo2,
            local_site=local_site,
            local_id=2)
        review2 = self.create_review(review_request2, publish=True)

        # An invite-only review group that the user has access to.
        group_accessible = self.create_review_group(
            name='group1',
            invite_only=True,
            local_site=local_site)
        group_accessible.users.add(user)

        # Review from a private repository that the user has
        # access to through being a member of a targeted review group.
        repo3 = self.create_repository(
            name='repo3',
            public=False,
            local_site=local_site)
        repo3.review_groups.add(group_accessible)
        review_request3 = self.create_review_request(
            publish=True,
            repository=repo3,
            local_site=local_site,
            local_id=3)
        review3 = self.create_review(review_request3, publish=True)

        # Review from a private repository that the user does
        # not have access to.
        repo4 = self.create_repository(
            name='repo4',
            public=False,
            local_site=local_site)
        review_request4 = self.create_review_request(
            publish=True,
            repository=repo4,
            local_site=local_site,
            local_id=4)
        review4 = self.create_review(review_request4, publish=True)

        # Review from a private repository that the user has access
        # to through being a member of a targeted review group and
        # being listed on the repository's users list.
        repo5 = self.create_repository(
            name='repo5',
            public=False,
            local_site=local_site)
        repo5.review_groups.add(group_accessible)
        repo5.users.add(user)
        review_request5 = self.create_review_request(
            publish=True,
            repository=repo5,
            local_site=local_site,
            local_id=5)
        review5 = self.create_review(review_request5, publish=True)

        # An invite-only review group that the user does not have access to.
        group_inaccessible = self.create_review_group(
            name='group2',
            invite_only=True,
            local_site=local_site)

        # Review from a private repository that targets an invite-only review
        # group, but that the user has access to from being listed in the
        # repository's users list.
        repo6 = self.create_repository(
            name='repo6',
            public=False,
            local_site=local_site)
        repo6.review_groups.add(group_inaccessible)
        repo6.users.add(user)
        review_request6 = self.create_review_request(
            publish=True,
            repository=repo6,
            local_site=local_site,
            local_id=6)
        review6 = self.create_review(review_request6, publish=True)

        # Review from a private repository that targets an invite-only review
        # group and that the user does not have access to.
        repo7 = self.create_repository(
            name='repo7',
            public=False,
            local_site=local_site)
        repo7.review_groups.add(group_inaccessible)
        review_request7 = self.create_review_request(
            publish=True,
            repository=repo7,
            local_site=local_site,
            local_id=7)
        review7 = self.create_review(review_request7, publish=True)

        self._prime_caches(user=user,
                           local_site=local_site)

        # Testing that anonymous users can only access reviews
        # from publicly-accessible repositories.
        self._check_anonymous_accessible_queries(
            user=anonymous,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            expected_reviews=[review1])

        # Testing that the user can only access reviews
        # from repositories that they have access to.
        self._check_user_accessible_queries(
            user=user,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            accessible_repository_ids=[
                repo1.pk,
                repo2.pk,
                repo3.pk,
                repo5.pk,
                repo6.pk,
            ],
            accessible_review_group_ids=[
                group_accessible.pk,
            ],
            expected_reviews=[
                review1,
                review2,
                review3,
                review5,
                review6,
            ])

        # Testing that superusers can access any reviews.
        self._check_superuser_accessible_queries(
            user=superuser,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            expected_reviews=[
                review1, review2, review3, review4,
                review5, review6, review7,
            ])

    def _test_accessible_by_review_group(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Helper for review group-related review accessibility tests.

        This tests that ReviewManager.accessible() returns only reviews
        associated with review groups that the user has access to.

        Args:
            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        # Review that the user has access to from being in a public
        # review group that is targeted by the review request.
        repo1 = self.create_repository(
            name='repo1',
            public=True,
            local_site=local_site)
        group1 = self.create_review_group(
            name='group1',
            invite_only=False,
            local_site=local_site)
        group1.users.add(user)
        review_request1 = self.create_review_request(
            publish=True,
            repository=repo1,
            local_site=local_site,
            local_id=1)
        review_request1.target_groups.add(group1)
        review1 = self.create_review(review_request1, publish=True)

        # Review that the user has access to from being in an invite-only
        # review group that is targeted by the review request.
        repo2 = self.create_repository(
            name='repo2',
            public=True,
            local_site=local_site)
        group2 = self.create_review_group(
            name='group2',
            invite_only=True,
            local_site=local_site)
        group2.users.add(user)
        review_request2 = self.create_review_request(
            publish=True,
            repository=repo2,
            local_site=local_site,
            local_id=2)
        review_request2.target_groups.add(group2)
        review2 = self.create_review(review_request2, publish=True)

        # Review that the user has access to since there is a public
        # review group that is targeted by the review request.
        repo3 = self.create_repository(
            name='repo3',
            public=True,
            local_site=local_site)
        group3 = self.create_review_group(
            name='group3',
            invite_only=False,
            local_site=local_site)
        review_request3 = self.create_review_request(
            publish=True,
            repository=repo3,
            local_site=local_site,
            local_id=3)
        review_request3.target_groups.add(group3)
        review3 = self.create_review(review_request3, publish=True)

        # Review that the user does not have access to since there is an
        # invite-only review group that is targeted by the review request.
        repo4 = self.create_repository(
            name='repo4',
            public=True,
            local_site=local_site)
        group4 = self.create_review_group(
            name='group4',
            invite_only=True,
            local_site=local_site)
        review_request4 = self.create_review_request(
            publish=True,
            repository=repo4,
            local_site=local_site,
            local_id=4)
        review_request4.target_groups.add(group4)
        review4 = self.create_review(review_request4, publish=True)

        self._prime_caches(user=user,
                           local_site=local_site)

        # Testing that anonymous users can only access reviews
        # from review requests that target public review groups.
        self._check_anonymous_accessible_queries(
            user=anonymous,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            expected_reviews=[review1, review3])

        # Testing that the user can only access reviews
        # from review requests that target them directly or target
        # review groups they have access to.
        self._check_user_accessible_queries(
            user=user,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            accessible_repository_ids=[
                repo1.pk,
                repo2.pk,
                repo3.pk,
                repo4.pk,
            ],
            accessible_review_group_ids=[
                group1.pk,
                group2.pk,
                group3.pk,
            ],
            expected_reviews=[
                review1,
                review2,
                review3,
            ])

        # Testing that superusers can access any reviews.
        self._check_superuser_accessible_queries(
            user=superuser,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            expected_reviews=[
                review1, review2, review3, review4,
            ])

    def _test_accessible_by_reviews_and_review_request(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Helper for reviews/review requests accessibility tests.

        This tests that ReviewManager.accessible() returns only public reviews
        from review requests that the user access to, and unpublished reviews
        that the user owns.

        Args:
            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        # Prime the user caches.
        user.get_site_profile(local_site)

        # Publicly-accessible published review request.
        review_request = self.create_review_request(
            publish=True,
            local_site=local_site,
            local_id=1)

        # Published review on a publicly-accessible review request.
        review1 = self.create_review(review_request, publish=True)

        # Unpublished review on a publicly-accessible review request.
        review2 = self.create_review(review_request, publish=False)

        # Published review owned by the user on a publicly-accessible
        # review request.
        review3 = self.create_review(review_request, user=user, publish=True)

        # Unpublished review owned by the user on a publicly-accessible
        # review request.
        review4 = self.create_review(review_request, user=user, publish=False)

        # Published review request from a private repository the user
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True,
            local_site=local_site,
            local_id=2)

        # Published review on a private repository the user does not have
        # access to.
        review5 = self.create_review(review_request_inaccessible, publish=True)

        # Unpublished review on a private repository the user does not have
        # access to.
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)

        # An invite-only review group used to limit access for the following
        # review requests.
        group = self.create_review_group(invite_only=True,
                                         local_site=local_site)

        # Published review from a review request that has an invite-only review
        # group not accessible to the user, but the user has access to through
        # being a targeted reviewer.
        review_request_targeted = self.create_review_request(
            publish=True,
            local_site=local_site,
            local_id=3)
        review_request_targeted.target_groups.add(group)
        review_request_targeted.target_people.add(user)
        review7 = self.create_review(review_request_targeted, publish=True)

        # Published review from a review request that has an invite-only review
        # group not accessible to the user, and that the user does not have
        # access to because the user is not listed as a target reviewer.
        review_request_untargeted = self.create_review_request(
            publish=True,
            local_site=local_site,
            local_id=4)
        review_request_untargeted.target_groups.add(group)
        review8 = self.create_review(review_request_untargeted, publish=True)

        self._prime_caches(user=user,
                           local_site=local_site)

        # Testing that anonymous users can only access publicly-accessible
        # reviews.
        self._check_anonymous_accessible_queries(
            user=anonymous,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            expected_reviews=[review1, review3])

        # Testing that the user can only access publicly-accessible
        # reviews and reviews that they own.
        self._check_user_accessible_queries(
            user=user,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            expected_reviews=[
                review1,
                review3,
                review4,
                review7,
            ])

        # Testing that superusers can access any reviews.
        self._check_superuser_accessible_queries(
            user=superuser,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            expected_reviews=[
                review1, review2, review3, review4,
                review5, review6, review7, review8,
            ])

    def _test_accessible_with_public(
        self,
        *,
        expected_public: bool,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Helper for public review accessibility tests.

        This tests that ReviewManager.accessible(public=expected_public) only
        returns reviews whose ``publish`` field that match the expected
        public state.

        Args:
            expected_public (bool):
                The ``public`` value that should be set on the ``publish``
                field of matching reviews.

            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        # Publicly-accessible published review request.
        review_request = self.create_review_request(
            publish=True,
            local_site=local_site,
            local_id=1)

        # Published/unpublished reviews on a publicly-accessible
        # review request.
        review1 = self.create_review(review_request, publish=expected_public)
        self.create_review(review_request, publish=not expected_public)

        # Published/unpublished reviews owned by the user on a
        # publicly-accessible review request.
        review3 = self.create_review(review_request,
                                     user=user,
                                     publish=expected_public)
        self.create_review(review_request,
                           user=user,
                           publish=not expected_public)

        # Published review request from a private repository the user
        # does not have access to.
        repo = self.create_repository(
            public=False,
            local_site=local_site)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True,
            local_site=local_site,
            local_id=2)

        # Published/unpublished reviews on a private repository the user does
        # not have access to.
        review5 = self.create_review(review_request_inaccessible,
                                     publish=expected_public)
        self.create_review(review_request_inaccessible,
                           publish=not expected_public)

        self._prime_caches(user=user,
                           local_site=local_site)

        if expected_public:
            # Testing that anonymous users can only access publicly-accessible
            # reviews and no drafts.
            self._check_anonymous_accessible_queries(
                user=anonymous,
                local_site=local_site,
                has_local_sites_in_db=local_sites_in_db,
                expected_reviews=[review1, review3])
        else:
            # 0 queries.
            with self.assertNumQueries(0):
                self.assertQuerySetEqual(
                    Review.objects.accessible(anonymous,
                                              public=False),
                    [])

        if expected_public:
            self._check_user_accessible_queries(
                user=user,
                local_site=local_site,
                local_sites_in_db=local_sites_in_db,
                expected_reviews=[review1, review3],
                accessible_kwargs={
                    'public': True,
                })
        else:
            self._check_user_accessible_queries(
                user=user,
                local_site=local_site,
                local_sites_in_db=local_sites_in_db,
                expected_reviews=[review3],
                accessible_kwargs={
                    'public': False,
                })

        # Testing that superusers can access any reviews.
        self._check_superuser_accessible_queries(
            user=superuser,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            expected_reviews=[review1, review3, review5],
            accessible_kwargs={
                'public': expected_public,
            })

    def _test_accessible_with_from_user(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Helper for from-user review accessibility tests.

        This tests that ReviewManager.from_user(...) only returns accessible
        reviews.

        Args:
            expected_public (bool):
                The ``public`` value that should be set on the ``publish``
                field of matching reviews.

            with_local_site (bool, optional):
                Whether to test with a Local Site for the query and objects.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        user = User.objects.get(username='doc')

        local_site: Optional[LocalSite]

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None


        user2 = self.create_user()
        repo = self.create_repository(
            public=True,
            local_site=local_site)
        review_request = self.create_review_request(
            publish=True,
            repository=repo,
            local_site=local_site,
            local_id=1)

        review = self.create_review(review_request, publish=True, user=user)
        self.create_review(review_request, publish=True, user=user2)

        self._prime_caches(user=user)

        equeries = get_reviews_from_user_equeries(
            user=AnonymousUser(),
            from_user=user,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            status='P')

        with assert_queries(equeries):
            # Testing that only reviews from the given user are returned.
            self.assertQuerySetEqual(
                Review.objects.from_user(user, local_site=local_site),
                [review])

    def _test_accessible_with_extra_query(
        self,
        *,
        with_local_site: bool = False,
        local_sites_in_db: bool = False,
    ) -> None:
        """Helper for testing ReviewManager.accessible(extra_query=...).

        Args:
            expected_public (bool):
                The ``public`` value that should be set on the ``publish``
                field of matching reviews.

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

        user = User.objects.get(username='doc')
        review_request = self.create_review_request(
            publish=True,
            local_site=local_site)

        review = self.create_review(review_request,
                                    body_top='hello',
                                    publish=True)
        self.create_review(review_request, publish=True)

        self._prime_caches(user=user,
                           local_site=local_site)

        self._check_user_accessible_queries(
            user=user,
            local_site=local_site,
            local_sites_in_db=local_sites_in_db,
            expected_reviews=[review],
            accessible_kwargs={
                'extra_query': Q(body_top='hello'),
            })

    def _check_anonymous_accessible_queries(
        self,
        *,
        user: AnonymousUser,
        local_site: Optional[LocalSite],
        has_local_sites_in_db: bool,
        expected_reviews: List[Review],
    ) -> None:
        """Check the accessible queries for a standard user.

        Version Added:
            5.0.7

        Args:
            user (django.contrib.auth.models.AnonymousUser):
                The anonymous user performing the query.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site the query is bound to.

            has_local_sites_in_db (bool):
                Whether to expect Local Sites in the database.

            expected_reviews (list of
                              reviewboard.reviews.models.review.Review):
                The reviews expected to be returned.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        self.assertTrue(user.is_anonymous)

        equeries = get_reviews_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=has_local_sites_in_db)

        with assert_queries(equeries):
            self.assertQuerySetEqual(
                Review.objects.accessible(user, local_site=local_site),
                expected_reviews)

    def _check_user_accessible_queries(
        self,
        *,
        user: User,
        local_site: Optional[LocalSite],
        local_sites_in_db: bool,
        expected_reviews: List[Review],
        accessible_repository_ids: Sequence[int] = [],
        accessible_review_group_ids: Sequence[int] = [],
        accessible_kwargs: KwargsDict = {},
    ) -> None:
        """Check the accessible queries for a standard user.

        Version Added:
            5.0.7

        Args:
            user (django.contrib.auth.models.User):
                The user performing the query.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site the query is bound to.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

            expected_reviews (list of
                              reviewboard.reviews.models.review.Review):
                The reviews expected to be returned.

            accessible_repository_ids (list of int):
                A list of IDs for accessible repositories.

            accessible_review_group_ids (list of int):
                A list of IDs for accessible review groups.

            accessible_kwargs (dict, optional):
                Additional keyword arguments to pass for the accessibility
                query.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        self.assertTrue(user.is_authenticated)
        self.assertFalse(user.is_superuser)

        equeries = get_reviews_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            accessible_repository_ids=accessible_repository_ids,
            accessible_review_group_ids=accessible_review_group_ids,
            **accessible_kwargs)

        with assert_queries(equeries):
            # Testing that the user can only access reviews
            # from repositories that they have access to.
            self.assertQuerySetEqual(
                Review.objects.accessible(user,
                                          local_site=local_site,
                                          **accessible_kwargs),
                expected_reviews)

    def _check_superuser_accessible_queries(
        self,
        *,
        user: User,
        local_site: Optional[LocalSite],
        local_sites_in_db: bool,
        expected_reviews: List[Review],
        accessible_kwargs: KwargsDict = {},
    ) -> None:
        """Check the accessible queries for a superuser.

        Version Added:
            5.0.7

        Args:
            user (django.contrib.auth.models.User):
                The superuser performing the query.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site the query is bound to.

            local_sites_in_db (bool, optional):
                Whether to expect Local Sites in the database.

            expected_reviews (list of
                              reviewboard.reviews.models.review.Review):
                The reviews expected to be returned.

            accessible_kwargs (dict, optional):
                Additional keyword arguments to pass for the accessibility
                query.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        self.assertTrue(user.is_superuser)

        equeries = get_reviews_accessible_equeries(
            user=user,
            local_site=local_site,
            has_local_sites_in_db=local_sites_in_db,
            **accessible_kwargs)

        with assert_queries(equeries):
            # Testing that superusers can acesss any reviews.
            self.assertQuerySetEqual(
                Review.objects.accessible(user,
                                          local_site=local_site,
                                          **accessible_kwargs),
                expected_reviews)

    def _prime_caches(
        self,
        *,
        user: User,
        local_site: Optional[LocalSite] = None,
    ) -> None:
        """Prime the caches before checking for queries.

        This will load commonly-cached state relevant to review queries,
        in order to test the queries specific to accessibility checks, so
        they don't influence query counts.

        Version Added:
            5.0.7

        Args:
            user (django.contrib.auth.models.User):
                The user that will be performing the accessibility query.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site the query is bound to.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        user.get_profile()
        user.get_site_profile(local_site)
        LocalSite.objects.has_local_sites()
