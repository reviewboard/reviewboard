"""Unit tests for RootReviewResource."""

from datetime import timedelta
from django.utils import timezone
from djblets.testing.decorators import add_fixtures
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import review_list_mimetype
from reviewboard.webapi.tests.urls import get_root_review_list_url


class ResourceListTests(BaseWebAPITestCase):
    """Testing the RootReviewResource list APIs."""

    fixtures = ['test_users']
    sample_api_url = 'reviews/'
    resource = resources.root_review

    def compare_item(self, item_rsp, review):
        """Compare a review item to a review returned from the API.

        Args:
            item_rsp (dict):
                The serialized review returned from the API.

            review (reviewboard.reviews.models.Review):
                The review instance to compare to.
        Raises:
            AssertionError:
                The API response was not equivalent to the object.
        """
        self.assertEqual(item_rsp['id'], review.pk)
        self.assertEqual(item_rsp['ship_it'], review.ship_it)
        self.assertEqual(item_rsp['body_top'], review.body_top)
        self.assertEqual(item_rsp['body_bottom'], review.body_bottom)

        if review.body_top_rich_text:
            self.assertEqual(item_rsp['body_top_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_top_text_type'], 'plain')

        if review.body_bottom_rich_text:
            self.assertEqual(item_rsp['body_bottom_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_bottom_text_type'], 'plain')

        self.assertEqual(item_rsp['absolute_url'],
                         self.base_url + review.get_absolute_url())

    @webapi_test_template
    def test_root_review_is_same_as_canonical_review(self):
        """Testing the GET <URL>/ API returns a proper data type API"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.compare_item(rsp[self.resource.list_result_key][0], review)

    @webapi_test_template
    def test_get_with_counts_only(self):
        """Testing the GET <URL>/?counts-only=1 API returns expected
        counts
        """
        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, publish=True)
        self.create_review(review_request, publish=True)

        rsp = self.api_get(get_root_review_list_url(), {
            'counts-only': 1,
        }, expected_mimetype=review_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_without_public(self):
        """Testing the GET <URL>/ API returns both public and unpublished
        reviews that the requester has access to by default
        """
        reviews = self._setup_acl_tests()
        review1 = reviews[0]
        review3 = reviews[2]
        review4 = reviews[3]
        review7 = reviews[6]

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 4)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review3)
        self.compare_item(rsp_items[2], review4)
        self.compare_item(rsp_items[3], review7)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_public_true(self):
        """Testing the GET <URL>/?public=1 API returns only public reviews
        that the requester has access to
        """
        reviews = self._setup_acl_tests()
        review1 = reviews[0]
        review3 = reviews[2]
        review7 = reviews[6]

        rsp = self.api_get(get_root_review_list_url(), {
            'public': 1,
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 3)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review3)
        self.compare_item(rsp_items[2], review7)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_public_false(self):
        """Testing the GET <URL>/?public=0 API returns only unpublished reviews
        that the requester has access to
        """
        reviews = self._setup_acl_tests()
        review4 = reviews[3]

        rsp = self.api_get(get_root_review_list_url(), {
            'public': 0,
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review4)

    @webapi_test_template
    def test_get_by_user_without_param(self):
        """Testing the GET <URL>/ API returns reviews that the requester has
        access to from all users when the user parameter is not included
        """
        reviews = self._setup_get_by_user_tests()
        review1 = reviews[0]
        review3 = reviews[2]

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 2)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review3)

    @webapi_test_template
    def test_get_by_user_with_param(self):
        """Testing the GET <URL>/?user=name API returns reviews by user"""
        reviews = self._setup_get_by_user_tests()
        review1 = reviews[0]

        # Testing that only reviews by the given user that the requester
        # has access to are returned.
        rsp = self.api_get(get_root_review_list_url(), {
            'user': 'user1',
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review1)

        # Testing that no reviews are returned when the given user
        # doesn't exist.
        rsp = self.api_get(get_root_review_list_url(), {
            'user': 'user3',
        }, expected_mimetype=review_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_by_repo(self):
        """Testing the GET <URL>/ API returns only reviews from
        repositories that the requester has access to
        """
        reviews = self._setup_get_by_repo_tests()
        review1 = reviews[0]
        review2 = reviews[1]
        review3 = reviews[2]
        review5 = reviews[4]
        review6 = reviews[5]

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 5)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review2)
        self.compare_item(rsp_items[2], review3)
        self.compare_item(rsp_items[3], review5)
        self.compare_item(rsp_items[4], review6)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_by_repo_with_param(self):
        """Testing the GET <URL>/?repository=name API returns reviews by
        repository and only from repositories that the requester has access to
        """
        reviews = self._setup_get_by_repo_tests()
        review1 = reviews[0]

        # Testing that reviews from the given repository that the requester
        # has access to are returned.
        rsp = self.api_get(get_root_review_list_url(), {
            'repository': 'repo1',
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review1)

        # Testing that no reviews are returned from repositories that the
        # requester does not have access to.
        rsp = self.api_get(get_root_review_list_url(), {
            'repository': 'repo4',
        }, expected_mimetype=review_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_by_review_group(self):
        """Testing the GET <URL>/ API returns reviews associated with
        any review groups that the requester has access to
        """
        # Review that the requester has access to from being in a public
        # review group that is targeted by the review request.
        group1 = self.create_review_group(name='group1', invite_only=False)
        group1.users.add(self.user)
        review_request1 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request1.target_groups.add(group1)
        review1 = self.create_review(review_request1, publish=True)

        # Review that the requester has access to from being in an invite-only
        # review group that is targeted by the review request.
        group2 = self.create_review_group(name='group2', invite_only=True)
        group2.users.add(self.user)
        review_request2 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request2.target_groups.add(group2)
        review2 = self.create_review(review_request2, publish=True)

        # Review that the requester has access to since there is a public
        # review group that is targeted by the review request.
        group3 = self.create_review_group(name='group3', invite_only=False)
        review_request3 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request3.target_groups.add(group3)
        review3 = self.create_review(review_request3, publish=True)

        # Review that the requester does not have access to since there is an
        # invite-only review group that is targeted by the review request.
        group4 = self.create_review_group(name='group4', invite_only=True)
        review_request4 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request4.target_groups.add(group4)
        self.create_review(review_request4, publish=True)

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 3)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review2)
        self.compare_item(rsp_items[2], review3)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_by_review_group_with_param(self):
        """Testing the GET <URL>/?review-group=name API returns reviews from
        users in the given group and only reviews that the requester has
        access to
        """
        # Review group that the requester is in.
        group1 = self.create_review_group(name='group1')
        group1.users.add(self.user)

        # User who is in the same review group.
        user1 = self.create_user('user1')
        group1.users.add(user1)

        # Public review by a user who's in the review group.
        review_request1 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review1 = self.create_review(review_request1,
                                     user=user1,
                                     publish=True)

        # Private review by a user who's in the review group.
        self.create_review(review_request1, user=user1, publish=False)

        # Public review by the requester.
        review3 = self.create_review(review_request1,
                                     user=self.user,
                                     publish=False)

        # Another review group.
        group2 = self.create_review_group(name='group2')

        # User who is in the other review group.
        user2 = self.create_user('user2')
        group2.users.add(user2)

        # Public review by a user who's in the other review group.
        review_request2 = self.create_review_request(publish=True,
                                                     create_repository=True)
        self.create_review(review_request2, user=user2, publish=True)

        rsp = self.api_get(get_root_review_list_url(), {
            'review-group': group1.name
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 2)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review3)

    @add_fixtures(['test_site', 'test_scmtools'])
    @webapi_test_template
    def test_get_by_local_site(self):
        """Testing the GET <URL>/ API returns only reviews from
        local sites that the requester has access to
        """
        # Review from a private local site that the user has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(self.user)
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

        # Testing that only reviews from the given local site are returned.
        rsp = self.api_get(
            get_root_review_list_url(local_site_name=local_site1.name),
            {},
            expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review1)

        # Testing that the requester is not authorized to make requests
        # to a local site that they do not have access to.
        rsp = self.api_get(
            get_root_review_list_url(local_site_name=local_site2.name),
            {},
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

        # Testing that reviews from local sites do not leak into results
        # from the global site.
        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review4)

    @webapi_test_template
    def test_get_by_last_updated_from_includes_from_date(self):
        """Testing the GET <URL>/?last-updated-from=<date> API
        returns only reviews within the from date
        """
        now = timezone.now()
        review_request = self.create_review_request(publish=True)

        # Review created within the from date.
        review1 = self.create_review(review_request, publish=True,
                                     timestamp=(now + timedelta(hours=1)))

        # Review created on the from date.
        review2 = self.create_review(review_request, publish=True,
                                     timestamp=now)

        # Review created outside of the from date.
        self.create_review(review_request, publish=True,
                           timestamp=(now - timedelta(hours=1)))

        rsp = self.api_get(get_root_review_list_url(), {
            'last-updated-from': now.isoformat(),
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 2)
        self.compare_item(rsp_items[0], review2)
        self.compare_item(rsp_items[1], review1)

    @webapi_test_template
    def test_get_by_last_updated_to_includes_to_date(self):
        """Testing the GET <URL>/?last-updated-to=<date>
        API returns only reviews within the to date exclusively
        """
        now = timezone.now()
        review_request = self.create_review_request(publish=True)

        # Review created within the to date.
        review1 = self.create_review(review_request, publish=True,
                                     timestamp=(now - timedelta(hours=1)))

        # Review created on the to date.
        self.create_review(review_request, publish=True,
                           timestamp=now)

        # Review created outside of the to date.
        self.create_review(review_request, publish=True,
                           timestamp=(now + timedelta(hours=1)))

        rsp = self.api_get(get_root_review_list_url(), {
            'last-updated-to': now.isoformat(),
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review1)

    @webapi_test_template
    def test_get_by_last_updated_to_and_from_simple_date_format(self):
        """Testing the GET
        <URL>/?last-updated-from=<date>&last-updated-to=<date>
        API returns only reviews within the from and to date
        """
        timestamp_from = timezone.now()
        timestamp_to = timezone.now() + timedelta(hours=1)
        review_request = self.create_review_request(publish=True)

        # Review created within the from and to dates.
        review = self.create_review(
            review_request,
            publish=True,
            timestamp=(timestamp_from + timedelta(minutes=30)))

        # Review created before the from date.
        self.create_review(review_request, publish=True,
                           timestamp=(timestamp_from - timedelta(minutes=30)))

        # Review created after the to date.
        self.create_review(review_request, publish=True,
                           timestamp=(timestamp_to + timedelta(minutes=30)))

        rsp = self.api_get(get_root_review_list_url(), {
            'last-updated-from': timestamp_from.isoformat(),
            'last-updated-to': timestamp_to.isoformat(),
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review)

    def _setup_acl_tests(self):
        """Sets up common review objects for access control tests.

        Returns:
            tuple of reviewboard.reviews.models.Review:
            A tuple of 7 reviews that were set up.
        """
        # Publicly-accessible published review request.
        review_request = self.create_review_request(publish=True)

        # Published review on a publicly-accessible review request.
        review1 = self.create_review(review_request, publish=True)

        # Unpublished review on a publicly-accessible review request.
        review2 = self.create_review(review_request, publish=False)

        # Published review owned by the requester on a publicly-accessible
        # review request.
        review3 = self.create_review(review_request,
                                     user=self.user,
                                     publish=True)

        # Unpublished review owned by the requester on a publicly-accessible
        # review request.
        review4 = self.create_review(review_request,
                                     user=self.user,
                                     publish=False)

        # Published review request from a private repository the requester
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True)

        # Published review on a private repository the requester does
        # not have access to.
        review5 = self.create_review(review_request_inaccessible, publish=True)

        # Unpublished review on a private repository the requester does
        # not have access to.
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)

        # An invite-only review group used to limit access for the following
        # review requests.
        group = self.create_review_group(invite_only=True)

        # Published review from a review request that has an invite-only review
        # group not accessible to the requester, but the requester has access
        # to through being a targeted reviewer.
        review_request_targetted = self.create_review_request(publish=True)
        review_request_targetted.target_groups.add(group)
        review_request_targetted.target_people.add(self.user)
        review7 = self.create_review(review_request_targetted, publish=True)

        # Published review from a review request that has an invite-only review
        # group not accessible to the requester, and that the requester does
        # not have access to because the requester is not listed as a target
        # reviewer.
        review_request_untargetted = self.create_review_request(publish=True)
        review_request_untargetted.target_groups.add(group)
        review8 = self.create_review(review_request_untargetted, publish=True)

        return (
            review1, review2, review3, review4,
            review5, review6, review7, review8
        )

    def _setup_get_by_user_tests(self):
        """Sets up common review objects for getting by user tests.

        Returns:
            tuple of reviewboard.reviews.models.Review:
            A tuple of 4 reviews that were set up.
        """
        review_request = self.create_review_request(publish=True)

        user1 = self.create_user(username='user1')
        review1 = self.create_review(review_request, publish=True, user=user1)
        review2 = self.create_review(review_request, publish=False, user=user1)

        user2 = self.create_user(username='user2')
        review3 = self.create_review(review_request, publish=True, user=user2)
        review4 = self.create_review(review_request, publish=False, user=user2)

        return review1, review2, review3, review4

    def _setup_get_by_repo_tests(self):
        """Sets up common review objects for getting by repositories tests.

        Returns:
            tuple of reviewboard.reviews.models.Review:
            A tuple of 7 reviews that were set up.
        """
        # Review from a public repository.
        repo1 = self.create_repository(name='repo1', public=True)
        review_request1 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)

        # Review from a private repository that the requester has
        # access to from being listed in the repository's users list.
        repo2 = self.create_repository(name='repo2', public=False)
        repo2.users.add(self.user)
        review_request2 = self.create_review_request(publish=True,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)

        # An invite-only review group that the requester has access to.
        group_accessible = self.create_review_group(invite_only=True)
        group_accessible.users.add(self.user)

        # Review from a private repository that the user has
        # access to through being a member of a targeted review group.
        repo3 = self.create_repository(name='repo3', public=False)
        repo3.review_groups.add(group_accessible)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)

        # Review from a private repository that the requester does
        # not have access to.
        repo4 = self.create_repository(name='repo4', public=False)
        review_request4 = self.create_review_request(publish=True,
                                                     repository=repo4)
        review4 = self.create_review(review_request4, publish=True)

        # Review from a private repository that the requester has access
        # to through being a member of a targeted review group and
        # being listed on the repository's users list.
        repo5 = self.create_repository(name='repo5', public=False)
        repo5.review_groups.add(group_accessible)
        repo5.users.add(self.user)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo5)
        review5 = self.create_review(review_request5, publish=True)

        # An invite-only review group that the requester does not have
        # access to.
        group_inaccessible = self.create_review_group(invite_only=True)

        # Review from a private repository that targets an invite-only review
        # group, but that the requester has access to from being listed in the
        # repository's users list.
        repo6 = self.create_repository(name='repo6', public=False)
        repo6.review_groups.add(group_inaccessible)
        repo6.users.add(self.user)
        review_request6 = self.create_review_request(publish=True,
                                                     repository=repo6)
        review6 = self.create_review(review_request6, publish=True)

        # Review from a private repository that targets an invite-only review
        # group and that the requester does not have access to.
        repo7 = self.create_repository(name='repo7', public=False)
        repo7.review_groups.add(group_inaccessible)
        review_request7 = self.create_review_request(publish=True,
                                                     repository=repo7)
        review7 = self.create_review(review_request7, publish=True)

        return (
            review1, review2, review3, review4,
            review5, review6, review7
        )
