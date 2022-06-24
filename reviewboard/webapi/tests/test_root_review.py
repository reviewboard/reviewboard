"""Unit tests for RootReviewResource."""

from datetime import timedelta
from django.utils import timezone
from djblets.testing.decorators import add_fixtures
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_list_mimetype)
from reviewboard.webapi.tests.urls import (get_root_review_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the RootReviewResource list APIs."""

    fixtures = ['test_users']
    sample_api_url = 'reviews/'
    resource = resources.review

    def compare_item(self, item_rsp, review):
        """Compare a review item to a review returned from the API.

        Args:
            item_rsp (dict):
                The serialied review returned from the API.

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

    @webapi_test_template
    def test_get_without_public(self):
        """Testing the GET <URL>/ API returns both public and unpublished
        reviews that the requester has access to by default
        """
        review_request = self.create_review_request(publish=True)
        review1 = self.create_review(review_request, publish=True)
        review2 = self.create_review(review_request, user=self.user,
                                     publish=False)
        review3 = self.create_review(review_request, user=self.user,
                                     publish=True)
        self.create_review(review_request, publish=False)

        repo = self.create_repository(public=False)
        review_request_inaccessible = \
            self.create_review_request(repository=repo)
        self.create_review(review_request_inaccessible, publish=True)
        self.create_review(review_request_inaccessible, publish=False)

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 3)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review2)
        self.compare_item(rsp_items[2], review3)

    @webapi_test_template
    def test_get_with_public_true(self):
        """Testing the GET <URL>/?public=1 API returns only public reviews
        that the requester has access to
        """
        review_request = self.create_review_request(publish=True)
        review1 = self.create_review(review_request, publish=True)
        review2 = self.create_review(review_request, user=self.user,
                                     publish=True)
        self.create_review(review_request, user=self.user, publish=False)
        self.create_review(review_request, publish=False)

        repo = self.create_repository(public=False)
        review_request_inaccessible = \
            self.create_review_request(repository=repo)
        self.create_review(review_request_inaccessible, publish=True)
        self.create_review(review_request_inaccessible, publish=False)

        rsp = self.api_get(get_root_review_list_url(), {
            'public': 1,
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 2)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review2)

    @webapi_test_template
    def test_get_with_public_false(self):
        """Testing the GET <URL>/?public=0 API returns only unpublished reviews
        that the requester has access to
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, user=self.user,
                                    publish=False)
        self.create_review(review_request, user=self.user, publish=True)
        self.create_review(review_request, publish=True)
        self.create_review(review_request, publish=False)

        review_request_inaccessible = \
            self.create_review_request(create_repository=True)
        review_request_inaccessible.repository.public = False
        self.create_review(review_request_inaccessible, publish=True)
        self.create_review(review_request_inaccessible, publish=False)

        rsp = self.api_get(get_root_review_list_url(), {
            'public': 0,
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review)

    @webapi_test_template
    def test_get_by_user_without_param(self):
        """Testing the GET <URL>/ API returns reviews from all users
        when the user parameter is not included
        """
        review_request = self.create_review_request(publish=True)
        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        review1 = self.create_review(review_request, publish=True, user=user1)
        review2 = self.create_review(review_request, publish=True, user=user2)
        self.create_review(review_request, publish=False, user=user2)

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 2)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review2)

    @webapi_test_template
    def test_get_by_user_with_param(self):
        """Testing the GET <URL>/?user=name API returns reviews by user"""
        review_request = self.create_review_request(publish=True)
        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')

        review1 = self.create_review(review_request, publish=True, user=user1)
        self.create_review(review_request, publish=True, user=user2)
        self.create_review(review_request, publish=False, user=user2)

        rsp = self.api_get(get_root_review_list_url(), {
            'user': 'user1',
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review1)

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
        group1 = self.create_review_group()
        group2 = self.create_review_group()
        group1.users.add(self.user)
        user = self.create_user()

        repo1 = self.create_repository(name='repo1', public=True)
        repo2 = self.create_repository(name='repo2', public=False)
        repo3 = self.create_repository(name='repo3', public=False)
        repo4 = self.create_repository(name='repo4', public=False)
        repo5 = self.create_repository(name='repo2', public=False)
        repo6 = self.create_repository(name='repo3', public=False)
        repo2.users.add(self.user)
        repo3.review_groups.add(group1)
        repo5.users.add(user)
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
        self.create_review(review_request4, publish=True)
        self.create_review(review_request5, publish=True)
        self.create_review(review_request6, publish=True)

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
    def test_get_by_repo_with_param(self):
        """Testing the GET <URL>/?repository=name API returns reviews by
        repository and only from repositories that the requester has access to
        """
        group1 = self.create_review_group()
        group2 = self.create_review_group()
        group1.users.add(self.user)
        user = self.create_user()

        repo1 = self.create_repository(name='repo1', public=True)
        repo2 = self.create_repository(name='repo2', public=False)
        repo3 = self.create_repository(name='repo3', public=False)
        repo4 = self.create_repository(name='repo4', public=False)
        repo5 = self.create_repository(name='repo2', public=False)
        repo6 = self.create_repository(name='repo3', public=False)
        repo2.users.add(self.user)
        repo3.review_groups.add(group1)
        repo5.users.add(user)
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
        self.create_review(review_request2, publish=True)
        self.create_review(review_request3, publish=True)
        self.create_review(review_request4, publish=True)
        self.create_review(review_request5, publish=True)
        self.create_review(review_request6, publish=True)

        rsp = self.api_get(get_root_review_list_url(), {
            'repository': 'repo1',
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review1)

        rsp = self.api_get(get_root_review_list_url(), {
            'repository': 'repo4',
        }, expected_mimetype=review_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_by_review_group(self):
        """Testing the GET <URL>/ API returns only reviews associated
        with review groups that the requester has access to
        """
        group1 = self.create_review_group(name='group1', invite_only=False)
        group2 = self.create_review_group(name='group2', invite_only=True)
        group3 = self.create_review_group(name='group3', invite_only=False)
        group4 = self.create_review_group(name='group4', invite_only=True)
        group1.users.add(self.user)
        group2.users.add(self.user)
        repo = self.create_repository(public=False)
        repo.review_groups.add(group4)

        review_request1 = self.create_review_request(publish=True)
        review_request2 = self.create_review_request(publish=True)
        review_request3 = self.create_review_request(publish=True)
        review_request4 = self.create_review_request(publish=True)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo)
        review_request1.target_groups.add(group1)
        review_request2.target_groups.add(group2)
        review_request3.target_groups.add(group3)
        review_request4.target_groups.add(group4)

        review1 = self.create_review(review_request1, publish=True)
        review2 = self.create_review(review_request2, publish=True)
        review3 = self.create_review(review_request3, publish=True)
        self.create_review(review_request4, publish=True)
        self.create_review(review_request5, publish=True)

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 3)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review2)
        self.compare_item(rsp_items[2], review3)

    @webapi_test_template
    def test_get_by_review_group_with_param(self):
        """Testing the GET <URL>/?review-group=name API returns reviews from
        users in the given group and only reviews associated with review groups
        that the requester has access to
        """
        user = self.create_user()
        group1 = self.create_review_group(name='group1', invite_only=False)
        group2 = self.create_review_group(name='group2', invite_only=True)
        group3 = self.create_review_group(name='group3', invite_only=False)
        group4 = self.create_review_group(name='group4', invite_only=True)
        group1.users.add(self.user)
        group2.users.add(self.user)
        group2.users.add(user)
        repo = self.create_repository(public=False)
        repo.review_groups.add(group4)

        review_request1 = self.create_review_request(publish=True)
        review_request2 = self.create_review_request(publish=True)
        review_request3 = self.create_review_request(publish=True)
        review_request4 = self.create_review_request(publish=True)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo)
        review_request1.target_groups.add(group1)
        review_request2.target_groups.add(group2)
        review_request3.target_groups.add(group3)
        review_request4.target_groups.add(group4)

        review1 = self.create_review(review_request1, user=self.user,
                                     publish=True)
        review2 = self.create_review(review_request2, user=user,
                                     publish=True)
        self.create_review(review_request3, publish=True)
        self.create_review(review_request4, publish=True)
        self.create_review(review_request5, publish=True)

        rsp = self.api_get(get_root_review_list_url(), {
            'review-group': group1.name
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review1)

        rsp = self.api_get(get_root_review_list_url(), {
            'review-group': group2.name
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 2)
        self.compare_item(rsp_items[0], review1)
        self.compare_item(rsp_items[1], review2)

        rsp = self.api_get(get_root_review_list_url(), {
            'review-group': group4.name
        }, expected_mimetype=review_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_by_local_site(self):
        """Testing the GET <URL>/ API returns only reviews from
        local sites that the requester has access to
        """
        local_site1 = self.get_local_site(self.local_site_name)
        local_site2 = self.get_local_site('local-site-2')
        local_site2.users.add(self.user)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2)
        review_request3 = self.create_review_request(publish=True)

        self.create_review(review_request1, publish=True, user='doc')
        review2 = self.create_review(review_request2, user=self.user,
                                     publish=True)
        review3 = self.create_review(review_request3, publish=True)

        rsp = self.api_get(
            get_root_review_list_url(local_site_name=local_site1.name),
            {},
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

        rsp = self.api_get(
            get_root_review_list_url(local_site_name=local_site2.name),
            {},
            expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review2)

        rsp = self.api_get(get_root_review_list_url(), {},
                           expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review3)

    @webapi_test_template
    def test_get_by_last_updated_from_includes_from_date(self):
        """Testing the GET <URL>/?last-updated-from=<date> API
        returns only reviews within the from date
        """
        now = timezone.now()
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True,
                                    timestamp=(now + timedelta(hours=1)))
        self.create_review(review_request, publish=True,
                           timestamp=(now - timedelta(hours=1)))

        rsp = self.api_get(get_root_review_list_url(), {
            'last-updated-from': now.isoformat(),
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review)

    @webapi_test_template
    def test_get_by_last_updated_from_includes_inclusive(self):
        """Testing the GET <URL>/?last-updated-from=<date> API
        returns only reviews within the from date inclusively
        """
        now = timezone.now()
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True,
                                    timestamp=now)

        rsp = self.api_get(get_root_review_list_url(), {
            'last-updated-from': now.isoformat(),
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review)

    @webapi_test_template
    def test_get_by_last_updated_to_includes_to_date(self):
        """Testing the GET <URL>/?last-updated-to=<date>
        API returns only reviews within the to date exclusively
        """
        now = timezone.now()
        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, publish=True,
                           timestamp=now)
        review = self.create_review(review_request, publish=True,
                                    timestamp=(now - timedelta(hours=1)))

        rsp = self.api_get(get_root_review_list_url(), {
            'last-updated-to': now.isoformat(),
        }, expected_mimetype=review_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], review)

    @webapi_test_template
    def test_get_by_last_updated_to_and_from_simple_date_format(self):
        """Testing the GET
        <URL>/?last-updated-from=<date>&last-updated-to=<date>
        API returns only reviews within the from and to date
        """
        timestamp_from = timezone.now()
        timestamp_to = timezone.now() + timedelta(hours=1)
        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, publish=True,
                           timestamp=(timestamp_from - timedelta(minutes=30)))
        review = self.create_review(
            review_request,
            publish=True,
            timestamp=(timestamp_from + timedelta(minutes=30)))
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
