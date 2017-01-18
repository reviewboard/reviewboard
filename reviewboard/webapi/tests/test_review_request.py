from __future__ import unicode_literals

from django.contrib import auth
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.utils import six
from django.utils.timezone import get_current_timezone
from djblets.db.query import get_object_or_none
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   INVALID_FORM_DATA,
                                   PERMISSION_DENIED)
from djblets.webapi.testing.decorators import webapi_test_template
from kgb import SpyAgency
from pytz import timezone

from reviewboard.accounts.backends import AuthBackend
from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.admin.server import build_server_url
from reviewboard.reviews.models import (BaseComment, ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.reviews.signals import (review_request_closing,
                                         review_request_publishing,
                                         review_request_reopening)
from reviewboard.reviews.errors import CloseError, PublishError, ReopenError
from reviewboard.site.models import LocalSite
from reviewboard.webapi.errors import (CLOSE_ERROR, INVALID_REPOSITORY,
                                       PUBLISH_ERROR, REOPEN_ERROR)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_request_item_mimetype,
                                                review_request_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_repository_item_url,
                                           get_review_request_draft_url,
                                           get_review_request_item_url,
                                           get_review_request_list_url,
                                           get_user_item_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(SpyAgency, ExtraDataListMixin, BaseWebAPITestCase):
    """Testing the ReviewRequestResource list API tests."""
    fixtures = ['test_users']
    basic_post_fixtures = ['test_scmtools']
    sample_api_url = 'review-requests/'
    resource = resources.review_request

    def compare_item(self, item_rsp, review_request):
        self.assertEqual(item_rsp['id'], review_request.display_id)
        self.assertEqual(item_rsp['summary'], review_request.summary)
        self.assertEqual(item_rsp['extra_data'], review_request.extra_data)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            if not with_local_site:
                LocalSite.objects.create(name=self.local_site_name)

            items = [
                self.create_review_request(
                    publish=True,
                    submitter=user,
                    with_local_site=with_local_site),
            ]

            self.create_review_request(publish=True,
                                       submitter=user,
                                       with_local_site=not with_local_site)
        else:
            items = []

        return (get_review_request_list_url(local_site_name),
                review_request_list_mimetype,
                items)

    @add_fixtures(['test_site'])
    def test_get_with_status(self):
        """Testing the GET review-requests/?status= API"""
        self.create_review_request(publish=True, status='S')
        self.create_review_request(publish=True, status='S')
        self.create_review_request(publish=True, status='D')
        self.create_review_request(publish=True, status='P')
        self.create_review_request(publish=True, status='P')
        self.create_review_request(publish=True, status='P')
        self.create_review_request(public=False, status='P')

        url = get_review_request_list_url()

        rsp = self.api_get(url, {'status': 'submitted'},
                           expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

        rsp = self.api_get(url, {'status': 'discarded'},
                           expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        rsp = self.api_get(url, {'status': 'all'},
                           expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 6)

        self._login_user(admin=True)
        rsp = self.api_get(url, {'status': 'all'},
                           expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 6)

        self._login_user(admin=True)
        rsp = self.api_get(
            url,
            {
                'status': 'all',
                'show-all-unpublished': True,
            },
            expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 7)

    def test_get_with_counts_only(self):
        """Testing the GET review-requests/?counts-only=1 API"""
        self.create_review_request(publish=True)
        self.create_review_request(publish=True)

        rsp = self.api_get(get_review_request_list_url(), {
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_with_to_groups(self):
        """Testing the GET review-requests/?to-groups= API"""
        group = self.create_review_group(name='devgroup')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        rsp = self.api_get(get_review_request_list_url(), {
            'to-groups': 'devgroup',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

    def test_get_with_to_groups_and_status(self):
        """Testing the GET review-requests/?to-groups=&status= API"""
        group = self.create_review_group(name='devgroup')

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True, status='S')
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_groups.add(group)

        url = get_review_request_list_url()

        rsp = self.api_get(url, {
            'status': 'submitted',
            'to-groups': 'devgroup',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        rsp = self.api_get(url, {
            'status': 'discarded',
            'to-groups': 'devgroup',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

    def test_get_with_to_groups_and_counts_only(self):
        """Testing the GET review-requests/?to-groups=&counts-only=1 API"""
        group = self.create_review_group(name='devgroup')

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        rsp = self.api_get(get_review_request_list_url(), {
            'to-groups': 'devgroup',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_with_to_users(self):
        """Testing the GET review-requests/?to-users= API"""
        grumpy = User.objects.get(username='grumpy')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        rsp = self.api_get(get_review_request_list_url(), {
            'to-users': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

    def test_get_with_to_users_and_status(self):
        """Testing the GET review-requests/?to-users=&status= API"""
        grumpy = User.objects.get(username='grumpy')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True, status='S')
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_people.add(grumpy)

        url = get_review_request_list_url()

        rsp = self.api_get(url, {
            'status': 'submitted',
            'to-users': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        rsp = self.api_get(url, {
            'status': 'discarded',
            'to-users': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

    def test_get_with_to_users_and_counts_only(self):
        """Testing the GET review-requests/?to-users=&counts-only=1 API"""
        grumpy = User.objects.get(username='grumpy')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        rsp = self.api_get(get_review_request_list_url(), {
            'to-users': 'grumpy',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_with_to_users_directly(self):
        """Testing the GET review-requests/?to-users-directly= API"""
        rsp = self.api_get(get_review_request_list_url(), {
            'to-users-directly': 'doc',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_with_to_users_directly_and_status(self):
        """Testing the GET review-requests/?to-users-directly=&status= API"""
        url = get_review_request_list_url()

        rsp = self.api_get(url, {
            'status': 'submitted',
            'to-users-directly': 'doc'
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='S').count())

        rsp = self.api_get(url, {
            'status': 'discarded',
            'to-users-directly': 'doc'
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='D').count())

    def test_get_with_to_users_directly_and_counts_only(self):
        """Testing the
        GET review-requests/?to-users-directly=&counts-only=1 API
        """
        rsp = self.api_get(get_review_request_list_url(), {
            'to-users-directly': 'doc',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_with_from_user(self):
        """Testing the GET review-requests/?from-user= API"""
        rsp = self.api_get(get_review_request_list_url(), {
            'from-user': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.from_user("grumpy").count())

    def test_get_with_from_user_and_status(self):
        """Testing the GET review-requests/?from-user=&status= API"""
        url = get_review_request_list_url()

        rsp = self.api_get(url, {
            'status': 'submitted',
            'from-user': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='S').count())

        rsp = self.api_get(url, {
            'status': 'discarded',
            'from-user': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='D').count())

    def test_get_with_from_user_and_counts_only(self):
        """Testing the GET review-requests/?from-user=&counts-only=1 API"""
        rsp = self.api_get(get_review_request_list_url(), {
            'from-user': 'grumpy',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.from_user("grumpy").count())

    # Tests for ?issue-dropped-count*= query parameters.
    def _setup_issue_dropped_count_tests(self):
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comments = [
            self.create_file_attachment_comment(review, file_attachment,
                                                issue_opened=True),
            self.create_file_attachment_comment(review, file_attachment,
                                                issue_opened=True),
        ]
        review.publish()

        for comment in comments:
            comment.issue_status = BaseComment.DROPPED
            comment.save()

    def test_get_with_issue_dropped_count_equals(self):
        """Testing the GET review-requests/?issue-dropped-count= API"""
        self._setup_issue_dropped_count_tests()
        self._test_get_with_field_count('issue-dropped-count', 2, 1)
        self._test_get_with_field_count('issue-dropped-count', 1, 0)

    def test_get_with_issue_dropped_count_lt(self):
        """Testing the GET review-requests/?issue-dropped-count-lt= API"""
        self._setup_issue_dropped_count_tests()
        self._test_get_with_field_count('issue-dropped-count-lt', 1, 0)
        self._test_get_with_field_count('issue-dropped-count-lt', 2, 0)
        self._test_get_with_field_count('issue-dropped-count-lt', 3, 1)

    def test_get_with_issue_dropped_count_lte(self):
        """Testing the GET review-requests/?issue-dropped-count-lte= API"""
        self._setup_issue_dropped_count_tests()
        self._test_get_with_field_count('issue-dropped-count-lte', 1, 0)
        self._test_get_with_field_count('issue-dropped-count-lte', 2, 1)
        self._test_get_with_field_count('issue-dropped-count-lte', 3, 1)

    def test_get_with_issue_dropped_count_gt(self):
        """Testing the GET review-requests/?issue-dropped-count-gt= API"""
        self._setup_issue_dropped_count_tests()
        self._test_get_with_field_count('issue-dropped-count-gt', 1, 1)
        self._test_get_with_field_count('issue-dropped-count-gt', 2, 0)
        self._test_get_with_field_count('issue-dropped-count-gt', 3, 0)

    def test_get_with_issue_dropped_count_gte(self):
        """Testing the GET review-requests/?issue-dropped-count-gte= API"""
        self._setup_issue_dropped_count_tests()
        self._test_get_with_field_count('issue-dropped-count-gte', 1, 1)
        self._test_get_with_field_count('issue-dropped-count-gte', 2, 1)
        self._test_get_with_field_count('issue-dropped-count-gte', 3, 0)

    # Tests for ?issue-open-count*= query parameters.
    def _setup_issue_open_count_tests(self):
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        self.create_file_attachment_comment(review, file_attachment,
                                            issue_opened=True)
        self.create_file_attachment_comment(review, file_attachment,
                                            issue_opened=True)
        review.publish()

    def test_get_with_issue_open_count_equals(self):
        """Testing the GET review-requests/?issue-open-count= API"""
        self._setup_issue_open_count_tests()
        self._test_get_with_field_count('issue-open-count', 2, 1)
        self._test_get_with_field_count('issue-open-count', 1, 0)

    def test_get_with_issue_open_count_lt(self):
        """Testing the GET review-requests/?issue-open-count-lt= API"""
        self._setup_issue_open_count_tests()
        self._test_get_with_field_count('issue-open-count-lt', 1, 0)
        self._test_get_with_field_count('issue-open-count-lt', 2, 0)
        self._test_get_with_field_count('issue-open-count-lt', 3, 1)

    def test_get_with_issue_open_count_lte(self):
        """Testing the GET review-requests/?issue-open-count-lte= API"""
        self._setup_issue_open_count_tests()
        self._test_get_with_field_count('issue-open-count-lte', 1, 0)
        self._test_get_with_field_count('issue-open-count-lte', 2, 1)
        self._test_get_with_field_count('issue-open-count-lte', 3, 1)

    def test_get_with_issue_open_count_gt(self):
        """Testing the GET review-requests/?issue-open-count-gt= API"""
        self._setup_issue_open_count_tests()
        self._test_get_with_field_count('issue-open-count-gt', 1, 1)
        self._test_get_with_field_count('issue-open-count-gt', 2, 0)
        self._test_get_with_field_count('issue-open-count-gt', 3, 0)

    def test_get_with_issue_open_count_gte(self):
        """Testing the GET review-requests/?issue-open-count-gte= API"""
        self._setup_issue_open_count_tests()
        self._test_get_with_field_count('issue-open-count-gte', 1, 1)
        self._test_get_with_field_count('issue-open-count-gte', 2, 1)
        self._test_get_with_field_count('issue-open-count-gte', 3, 0)

    # Tests for ?issue-resolved-count*= query parameters.
    def _setup_issue_resolved_count_tests(self):
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request)
        comments = [
            self.create_file_attachment_comment(review, file_attachment,
                                                issue_opened=True),
            self.create_file_attachment_comment(review, file_attachment,
                                                issue_opened=True),
        ]
        review.publish()

        for comment in comments:
            comment.issue_status = BaseComment.RESOLVED
            comment.save()

    def test_get_with_issue_resolved_count_equals(self):
        """Testing the GET review-requests/?issue-resolved-count= API"""
        self._setup_issue_resolved_count_tests()
        self._test_get_with_field_count('issue-resolved-count', 2, 1)
        self._test_get_with_field_count('issue-resolved-count', 1, 0)

    def test_get_with_issue_resolved_count_lt(self):
        """Testing the GET review-requests/?issue-resolved-count-lt= API"""
        self._setup_issue_resolved_count_tests()
        self._test_get_with_field_count('issue-resolved-count-lt', 1, 0)
        self._test_get_with_field_count('issue-resolved-count-lt', 2, 0)
        self._test_get_with_field_count('issue-resolved-count-lt', 3, 1)

    def test_get_with_issue_resolved_count_lte(self):
        """Testing the GET review-requests/?issue-resolved-count-lte= API"""
        self._setup_issue_resolved_count_tests()
        self._test_get_with_field_count('issue-resolved-count-lte', 1, 0)
        self._test_get_with_field_count('issue-resolved-count-lte', 2, 1)
        self._test_get_with_field_count('issue-resolved-count-lte', 3, 1)

    def test_get_with_issue_resolved_count_gt(self):
        """Testing the GET review-requests/?issue-resolved-count-gt= API"""
        self._setup_issue_resolved_count_tests()
        self._test_get_with_field_count('issue-resolved-count-gt', 1, 1)
        self._test_get_with_field_count('issue-resolved-count-gt', 2, 0)
        self._test_get_with_field_count('issue-resolved-count-gt', 3, 0)

    def test_get_with_issue_resolved_count_gte(self):
        """Testing the GET review-requests/?issue-resolved-count-gte= API"""
        self._setup_issue_resolved_count_tests()
        self._test_get_with_field_count('issue-resolved-count-gte', 1, 1)
        self._test_get_with_field_count('issue-resolved-count-gte', 2, 1)
        self._test_get_with_field_count('issue-resolved-count-gte', 3, 0)

    # Tests for ?ship-it-count*= query parameters.
    def _setup_ship_it_count_tests(self):
        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, ship_it=True, publish=True)
        self.create_review(review_request, ship_it=True, publish=True)

    def test_get_with_ship_it_count_equals(self):
        """Testing the GET review-requests/?ship-it-count= API"""
        self._setup_ship_it_count_tests()
        self._test_get_with_field_count('ship-it-count', 2, 1)
        self._test_get_with_field_count('ship-it-count', 1, 0)

    def test_get_with_ship_it_count_lt(self):
        """Testing the GET review-requests/?ship-it-count-lt= API"""
        self._setup_ship_it_count_tests()
        self._test_get_with_field_count('ship-it-count-lt', 1, 0)
        self._test_get_with_field_count('ship-it-count-lt', 2, 0)
        self._test_get_with_field_count('ship-it-count-lt', 3, 1)

    def test_get_with_ship_it_count_lte(self):
        """Testing the GET review-requests/?ship-it-count-lte= API"""
        self._setup_ship_it_count_tests()
        self._test_get_with_field_count('ship-it-count-lte', 1, 0)
        self._test_get_with_field_count('ship-it-count-lte', 2, 1)
        self._test_get_with_field_count('ship-it-count-lte', 3, 1)

    def test_get_with_ship_it_count_gt(self):
        """Testing the GET review-requests/?ship-it-count-gt= API"""
        self._setup_ship_it_count_tests()
        self._test_get_with_field_count('ship-it-count-gt', 1, 1)
        self._test_get_with_field_count('ship-it-count-gt', 2, 0)
        self._test_get_with_field_count('ship-it-count-gt', 3, 0)

    def test_get_with_ship_it_count_gte(self):
        """Testing the GET review-requests/?ship-it-count-gte= API"""
        self._setup_ship_it_count_tests()
        self._test_get_with_field_count('ship-it-count-gte', 1, 1)
        self._test_get_with_field_count('ship-it-count-gte', 2, 1)
        self._test_get_with_field_count('ship-it-count-gte', 3, 0)

    def test_get_with_ship_it_0(self):
        """Testing the GET review-requests/?ship-it=0 API"""
        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, ship_it=True, publish=True)

        rsp = self.api_get(get_review_request_list_url(), {
            'ship-it': 0,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        q = ReviewRequest.objects.public(user=self.user,
                                         status='P',
                                         extra_query=Q(shipit_count=0))
        self.assertEqual(len(rsp['review_requests']), q.count())

    def test_get_with_ship_it_1(self):
        """Testing the GET review-requests/?ship-it=1 API"""
        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, ship_it=True, publish=True)

        rsp = self.api_get(get_review_request_list_url(), {
            'ship-it': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        q = ReviewRequest.objects.public(user=self.user,
                                         status='P',
                                         extra_query=Q(shipit_count__gt=0))
        self.assertEqual(len(rsp['review_requests']), q.count())

    def test_get_with_time_added_from(self):
        """Testing the GET review-requests/?time-added-from= API"""
        start_index = 3

        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.time_added.isoformat()

        rsp = self.api_get(get_review_request_list_url(), {
            'time-added-from': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                time_added__gte=r.time_added).count())

    def test_get_with_time_added_to(self):
        """Testing the GET review-requests/?time-added-to= API"""
        start_index = 3

        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.time_added.isoformat()

        rsp = self.api_get(get_review_request_list_url(), {
            'time-added-to': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index + 1)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                time_added__lt=r.time_added).count())

    def test_get_with_last_updated_from(self):
        """Testing the GET review-requests/?last-updated-from= API"""
        start_index = 3
        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.last_updated.isoformat()

        rsp = self.api_get(get_review_request_list_url(), {
            'last-updated-from': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                last_updated__gte=r.last_updated).count())

    def test_get_with_last_updated_to(self):
        """Testing the GET review-requests/?last-updated-to= API"""
        start_index = 3
        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.last_updated.isoformat()

        rsp = self.api_get(get_review_request_list_url(), {
            'last-updated-to': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index + 1)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                last_updated__lt=r.last_updated).count())

    def test_get_with_last_updated_from_and_ambiguous_time(self):
        """Testing the GET review-requests/?last-updated-from= API with an
        ambiguous timestamp
        """
        self.spy_on(get_current_timezone,
                    call_fake=lambda: timezone('America/Chicago'))

        rsp = self.api_get(
            get_review_request_list_url(),
            {
                'last-updated-from': '2016-11-06T01:05:59',
                'counts-only': 1,
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('last-updated-from' in rsp['fields'])

    @add_fixtures(['test_scmtools'])
    def test_get_with_repository_and_changenum(self):
        """Testing the GET review-requests/?repository=&changenum= API"""
        # Create a fake first one so that we can check that the query went
        # through.
        self.create_review_request(create_repository=True, publish=True)

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review_request.changenum = 1234
        review_request.save()

        rsp = self.api_get(get_review_request_list_url(), {
            'repository': review_request.repository.id,
            'changenum': review_request.changenum,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)
        self.assertEqual(rsp['review_requests'][0]['id'],
                         review_request.display_id)
        self.assertEqual(rsp['review_requests'][0]['summary'],
                         review_request.summary)
        self.assertEqual(rsp['review_requests'][0]['changenum'],
                         review_request.changenum)
        self.assertEqual(rsp['review_requests'][0]['commit_id'],
                         review_request.commit)

    @add_fixtures(['test_scmtools'])
    def test_get_with_repository_and_commit_id(self):
        """Testing the GET review-requests/?repository=&commit-id= API
        with changenum backwards-compatibility
        """
        # Create a fake first one so that we can check that the query went
        # through.
        self.create_review_request(create_repository=True, publish=True)

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review_request.changenum = 1234
        review_request.save()

        self.assertEqual(review_request.commit_id, None)

        commit_id = six.text_type(review_request.changenum)

        rsp = self.api_get(get_review_request_list_url(), {
            'repository': review_request.repository.id,
            'commit-id': review_request.commit,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)
        self.assertEqual(rsp['review_requests'][0]['id'],
                         review_request.display_id)
        self.assertEqual(rsp['review_requests'][0]['summary'],
                         review_request.summary)
        self.assertEqual(rsp['review_requests'][0]['changenum'],
                         review_request.changenum)
        self.assertEqual(rsp['review_requests'][0]['commit_id'],
                         commit_id)

    @add_fixtures(['test_scmtools'])
    def test_get_num_queries(self):
        """Testing the GET <URL> API for number of queries"""
        repo = self.create_repository()

        review_requests = [
            self.create_review_request(repository=repo, publish=True),
            self.create_review_request(repository=repo, publish=True),
            self.create_review_request(repository=repo, publish=True),
        ]

        for review_request in review_requests:
            self.create_diffset(review_request)
            self.create_diffset(review_request)

        with self.assertNumQueries(11):
            rsp = self.api_get(get_review_request_list_url(),
                               expected_mimetype=review_request_list_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('total_results', rsp)
        self.assertEqual(rsp['total_results'], 3)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        if post_valid_data:
            repository = \
                self.create_repository(with_local_site=with_local_site)

            post_data = {
                'repository': repository.path,
            }
        else:
            post_data = {}

        return (get_review_request_list_url(local_site_name),
                review_request_item_mimetype,
                post_data,
                [])

    def check_post_result(self, user, rsp):
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    @add_fixtures(['test_scmtools'])
    def test_post_with_repository_name(self):
        """Testing the POST review-requests/ API with a repository name"""
        repository = self.create_repository()

        rsp = self.api_post(
            get_review_request_list_url(),
            {'repository': repository.name},
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['repository']['href'],
            self.base_url + get_repository_item_url(repository))

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        return ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    @add_fixtures(['test_scmtools'])
    def test_post_with_no_repository(self):
        """Testing the POST review-requests/ API with no repository"""
        rsp = self.api_post(
            get_review_request_list_url(),
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertNotIn('repository', rsp['review_request']['links'])

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])
        self.assertEqual(review_request.repository, None)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_post_with_site_invalid_repository_error(self):
        """Testing the POST review-requests/ API
        with a local site and Invalid Repository error
        """
        repository = self.create_repository()

        self._login_user(local_site=True)
        rsp = self.api_post(
            get_review_request_list_url(self.local_site_name),
            {'repository': repository.path},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    def test_post_with_invalid_repository_error(self):
        """Testing the POST review-requests/ API
        with Invalid Repository error
        """
        rsp = self.api_post(
            get_review_request_list_url(),
            {'repository': 'gobbledygook'},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_post_with_no_site_invalid_repository_error(self):
        """Testing the POST review-requests/ API with
        Invalid Repository error from a site-local repository
        """
        repository = self.create_repository(with_local_site=True)

        rsp = self.api_post(
            get_review_request_list_url(),
            {'repository': repository.path},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    @add_fixtures(['test_scmtools'])
    def test_post_with_conflicting_repos(self):
        """Testing the POST review-requests/ API with conflicting repositories
        """
        repository = self.create_repository(tool_name='Test')
        self.create_repository(tool_name='Test',
                               name='Test 2',
                               path='blah',
                               mirror_path=repository.path)

        rsp = self.api_post(
            get_review_request_list_url(),
            {'repository': repository.path},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)
        self.assertEqual(rsp['err']['msg'],
                         'Too many repositories matched "%s". Try '
                         'specifying the repository by name instead.'
                         % repository.path)
        self.assertEqual(rsp['repository'], repository.path)

    @add_fixtures(['test_scmtools'])
    def test_post_with_commit_id(self):
        """Testing the POST review-requests/ API with commit_id"""
        repository = self.create_repository()
        commit_id = 'abc123'

        rsp = self.api_post(
            get_review_request_list_url(),
            {
                'repository': repository.name,
                'commit_id': commit_id,
            },
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['commit_id'], commit_id)
        self.assertEqual(rsp['review_request']['summary'], '')

        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])
        self.assertEqual(review_request.commit, commit_id)

    @add_fixtures(['test_scmtools'])
    def test_post_with_commit_id_and_used_in_review_request(self):
        """Testing the POST review-requests/ API with commit_id used in
        another review request
        """
        repository = self.create_repository()
        commit_id = 'abc123'

        self.create_review_request(commit_id=commit_id,
                                   repository=repository,
                                   publish=True)

        self.api_post(
            get_review_request_list_url(),
            {
                'repository': repository.name,
                'commit_id': commit_id,
            },
            expected_status=409)

    @add_fixtures(['test_scmtools'])
    def test_post_with_commit_id_and_used_in_draft(self):
        """Testing the POST review-requests/ API with commit_id used in
        another review request draft
        """
        repository = self.create_repository()
        commit_id = 'abc123'

        existing_review_request = self.create_review_request(
            repository=repository,
            publish=True)
        existing_draft = ReviewRequestDraft.create(existing_review_request)
        existing_draft.commit_id = commit_id
        existing_draft.save()

        self.api_post(
            get_review_request_list_url(),
            {
                'repository': repository.name,
                'commit_id': commit_id,
            },
            expected_status=409)

    @add_fixtures(['test_scmtools'])
    def test_post_with_commit_id_empty_string(self):
        """Testing the POST review-requests/ API with commit_id=''"""
        repository = self.create_repository()

        rsp = self.api_post(
            get_review_request_list_url(),
            {
                'repository': repository.name,
                'commit_id': '',
            },
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIsNone(rsp['review_request']['commit_id'])

        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])
        self.assertIsNone(review_request.commit)

    @add_fixtures(['test_scmtools'])
    def test_post_with_commit_id_and_create_from_commit_id(self):
        """Testing the POST review-requests/ API with
        commit_id and create_from_commit_id
        """
        repository = self.create_repository(tool_name='Test')
        commit_id = 'abc123'

        rsp = self.api_post(
            get_review_request_list_url(),
            {
                'repository': repository.name,
                'commit_id': commit_id,
                'create_from_commit_id': True,
            },
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['commit_id'], 'abc123')
        self.assertEqual(rsp['review_request']['changenum'], None)
        self.assertEqual(rsp['review_request']['summary'], '')
        self.assertEqual(rsp['review_request']['description'], '')

        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])
        self.assertEqual(review_request.commit_id, 'abc123')
        self.assertEqual(review_request.summary, '')
        self.assertEqual(review_request.description, '')

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.commit_id, commit_id)
        self.assertEqual(draft.summary, 'Commit summary')
        self.assertEqual(draft.description, 'Commit description.')

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_post_with_changenum(self):
        """Testing the POST <URL> API with changenum"""
        repository = self.create_repository(tool_name='Test')

        rsp = self.api_post(
            get_review_request_list_url(),
            {
                'repository': repository.name,
                'changenum': 123,
            },
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['commit_id'], '123')
        self.assertEqual(rsp['review_request']['changenum'], 123)
        self.assertEqual(rsp['review_request']['summary'], '')
        self.assertEqual(rsp['review_request']['description'], '')

        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])
        self.assertEqual(review_request.commit_id, '123')
        self.assertEqual(review_request.changenum, 123)
        self.assertEqual(review_request.summary, '')
        self.assertEqual(review_request.description, '')

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.commit_id, '123')
        self.assertEqual(draft.summary, 'Commit summary')
        self.assertEqual(draft.description, 'Commit description.')

    def test_post_with_submit_as_and_permission(self):
        """Testing the POST review-requests/?submit_as= API
        with permission
        """
        self.user.user_permissions.add(
            Permission.objects.get(codename='can_submit_as_another_user'))

        self._test_post_with_submit_as()

    def test_post_with_submit_as_and_admin(self):
        """Testing the POST review-requests/?submit_as= API
        with administrator
        """
        self.user.is_superuser = True
        self.user.save()

        self._test_post_with_submit_as()

    @add_fixtures(['test_site'])
    def test_post_with_submit_as_and_site_permission(self):
        """Testing the POST review-requests/?submit_as= API
        with a local site and local permission
        """
        self.user = self._login_user(local_site=True)

        local_site = self.get_local_site(name=self.local_site_name)

        site_profile = LocalSiteProfile.objects.create(
            local_site=local_site,
            user=self.user,
            profile=self.user.get_profile())
        site_profile.permissions['reviews.can_submit_as_another_user'] = True
        site_profile.save()

        self._test_post_with_submit_as(local_site)

    @add_fixtures(['test_site'])
    def test_post_with_submit_as_and_site_admin(self):
        """Testing the POST review-requests/?submit_as= API
        with a local site and site admin
        """
        self._login_user(local_site=True, admin=True)

        self._test_post_with_submit_as(
            self.get_local_site(name=self.local_site_name))

    @add_fixtures(['test_scmtools'])
    def test_post_with_submit_as_and_permission_denied_error(self):
        """Testing the POST review-requests/?submit_as= API
        with Permission Denied error
        """
        repository = self.create_repository()

        rsp = self.api_post(
            get_review_request_list_url(),
            {
                'repository': repository.path,
                'submit_as': 'doc',
            },
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_or_create_user_auth_backend(self):
        """Testing the POST review-requests/?submit_as= API
        with AuthBackend.get_or_create_user failure
        """
        class SandboxAuthBackend(AuthBackend):
            backend_id = 'test-id'
            name = 'test'

            def get_or_create_user(self, username, request=None,
                                   password=None):
                raise Exception

        backend = SandboxAuthBackend()

        self.spy_on(auth.get_backends, call_fake=lambda: [backend])

        # First spy messes with User.has_perm, this lets it through
        self.spy_on(User.has_perm, call_fake=lambda x, y, z: True)
        self.spy_on(backend.get_or_create_user)

        rsp = self.api_post(
            get_review_request_list_url(None),
            {
                'submit_as': 'barry',
            },
            expected_mimetype=None,
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')

        self.assertTrue(backend.get_or_create_user.called)

    def _test_get_with_field_count(self, query_arg, value, expected_count):
        rsp = self.api_get(get_review_request_list_url(), {
            query_arg: value,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), expected_count)

    def _test_post_with_submit_as(self, local_site=None):
        submit_as_username = 'dopey'

        self.assertNotEqual(self.user.username, submit_as_username)

        if local_site:
            local_site_name = local_site.name
            local_site.users.add(User.objects.get(username=submit_as_username))
        else:
            local_site_name = None

        rsp = self.api_post(
            get_review_request_list_url(local_site_name),
            {
                'submit_as': submit_as_username,
            },
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['submitter']['href'],
            self.base_url +
            get_user_item_url(submit_as_username, local_site_name))

        ReviewRequest.objects.get(pk=rsp['review_request']['id'])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, BaseWebAPITestCase):
    """Testing the ReviewRequestResource item API tests."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/'
    resource = resources.review_request
    test_http_methods = ('DELETE', 'GET', 'PUT')

    def compare_item(self, item_rsp, review_request):
        self.assertEqual(item_rsp['id'], review_request.display_id)
        self.assertEqual(item_rsp['summary'], review_request.summary)
        self.assertEqual(item_rsp['extra_data'], review_request.extra_data)
        self.assertEqual(item_rsp['absolute_url'],
                         self.base_url + review_request.get_absolute_url())

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.assertTrue(user.has_perm('reviews.delete_reviewrequest'))

        review_request = self.create_review_request(
            submitter=user,
            with_local_site=with_local_site,
            publish=True)

        return (get_review_request_item_url(review_request.display_id,
                                            local_site_name),
                [review_request.pk])

    def check_delete_result(self, user, review_request_id):
        self.assertIsNone(get_object_or_none(ReviewRequest,
                                             pk=review_request_id))

    def test_delete_with_permission_denied_error(self):
        """Testing the DELETE review-requests/<id>/ API
        without permission and with Permission Denied error
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        rsp = self.api_delete(
            get_review_request_item_url(review_request.display_id),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_with_does_not_exist_error(self):
        """Testing the DELETE review-requests/<id>/ API
        with Does Not Exist error
        """
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assertTrue(self.user.has_perm('reviews.delete_reviewrequest'))

        rsp = self.api_delete(get_review_request_item_url(999),
                              expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_with_site_and_local_permission(self):
        """Testing the DELETE review-requests/<id>/ API
        with a local site and a local permission is not allowed
        """
        self.user = self._login_user(local_site=True)
        local_site = self.get_local_site(name=self.local_site_name)

        site_profile = LocalSiteProfile.objects.create(
            user=self.user,
            local_site=local_site,
            profile=self.user.get_profile())
        site_profile.permissions['reviews.delete_reviewrequest'] = True
        site_profile.save()

        review_request = self.create_review_request(with_local_site=True)

        self.api_delete(
            get_review_request_item_url(review_request.display_id,
                                        self.local_site_name),
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_with_site_and_site_admin(self):
        """Testing the DELETE review-requests/<id>/ API
        with a local site and a site admin is not allowed
        """
        self.user = self._login_user(local_site=True, admin=True)
        review_request = self.create_review_request(with_local_site=True)

        self.api_delete(
            get_review_request_item_url(review_request.display_id,
                                        self.local_site_name),
            expected_status=403)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            publish=True)

        return (get_review_request_item_url(review_request.display_id,
                                            local_site_name),
                review_request_item_mimetype,
                review_request)

    def test_get_with_non_public_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/ API
        with non-public and Permission Denied error
        """
        review_request = self.create_review_request(public=False)
        self.assertNotEqual(review_request.submitter, self.user)

        rsp = self.api_get(
            get_review_request_item_url(review_request.display_id),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_with_invite_only_group_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/ API
        with invite-only group and Permission Denied error
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        group = self.create_review_group(invite_only=True)

        review_request.target_groups.add(group)
        review_request.save()

        rsp = self.api_get(
            get_review_request_item_url(review_request.display_id),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_get_with_invite_only_group_and_target_user(self):
        """Testing the GET review-requests/<id>/ API
        with invite-only group and target user
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        group = self.create_review_group(invite_only=True)

        review_request.target_groups.add(group)
        review_request.target_people.add(self.user)
        review_request.save()

        rsp = self.api_get(
            get_review_request_item_url(review_request.display_id),
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    @add_fixtures(['test_site'])
    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)

        self._testHttpCaching(get_review_request_item_url(review_request.id),
                              check_etags=True)

    @add_fixtures(['test_scmtools'])
    def test_get_with_latest_diff(self):
        """Testing the GET <URL> API and checking for the latest diff"""
        repo = self.create_repository()
        review_request = self.create_review_request(repository=repo,
                                                    publish=True)

        self.create_diffset(review_request)
        latest = self.create_diffset(review_request)

        rsp = self.api_get(get_review_request_item_url(review_request.pk),
                           expected_mimetype=review_request_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertIn('review_request', rsp)
        item_rsp = rsp['review_request']

        self.assertIn('links', item_rsp)
        links = item_rsp['links']

        self.assertIn('latest_diff', links)
        diff_link = links['latest_diff']

        self.assertEqual(
            diff_link['href'],
            build_server_url(resources.diff.get_href(latest, None)))

    def test_get_with_no_latest_diff(self):
        """Testing the GET <URL> API and checking that there is no latest_diff
        link for review requests without a repository
        """
        review_request = self.create_review_request(publish=True)
        rsp = self.api_get(get_review_request_item_url(review_request.pk),
                           expected_mimetype=review_request_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertIn('review_request', rsp)
        item_rsp = rsp['review_request']

        self.assertIn('links', item_rsp)
        links = item_rsp['links']

        self.assertNotIn('latest_diff', links)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = \
            self.create_review_request(submitter=user, publish=True,
                                       with_local_site=with_local_site)

        return (get_review_request_item_url(review_request.display_id,
                                            local_site_name),
                review_request_item_mimetype,
                {
                    'extra_data.dummy': '',
                },
                review_request,
                [])

    def check_put_result(self, user, item_rsp, review_request):
        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.compare_item(item_rsp, review_request)

    @add_fixtures(['test_scmtools'])
    def test_put_changenum_for_published_request(self):
        """Testing the PUT review-requests/<id>/?changenum=<integer> API"""
        changenum = '3141592653'
        commit_id = '1234567890'
        repository = self.create_repository(tool_name='Test')
        r = self.create_review_request(submitter=self.user, publish=True,
                                       repository=repository,
                                       changenum=commit_id,
                                       commit_id=commit_id)

        rsp = self.api_put(
            get_review_request_item_url(r.display_id),
            {'changenum': changenum},
            expected_mimetype=review_request_item_mimetype)

        rr = rsp['review_request']
        self.assertEqual(rr["changenum"], int(changenum))
        self.assertEqual(rr["commit_id"], changenum)

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.changenum, int(changenum))
        self.assertEqual(r.commit_id, changenum)

    def test_put_status_legacy_description(self):
        """Testing the PUT review-requests/<id>/?status= API
        with legacy description= field
        """
        r = self.create_review_request(submitter=self.user, publish=True)

        rsp = self.api_put(
            get_review_request_item_url(r.display_id),
            {
                'status': 'discarded',
                'description': 'comment',
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'D')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'D')

    def test_put_status_discarded(self):
        """Testing the PUT review-requests/<id>/?status=discarded API"""
        r = self.create_review_request(submitter=self.user, publish=True)

        rsp = self.api_put(
            get_review_request_item_url(r.display_id),
            {
                'status': 'discarded',
                'close_description': 'comment',
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'D')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'D')

    def test_put_status_discarded_with_permission_denied(self):
        """Testing the PUT review-requests/<id>/?status=discarded API
        with Permission Denied
        """
        r = self.create_review_request()
        self.assertNotEqual(r.submitter, self.user)

        rsp = self.api_put(
            get_review_request_item_url(r.display_id),
            {'status': 'discarded'},
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_status_pending(self):
        """Testing the PUT review-requests/<id>/?status=pending API"""
        r = self.create_review_request(submitter=self.user, publish=True)
        r.close(ReviewRequest.SUBMITTED)
        r.save()

        rsp = self.api_put(
            get_review_request_item_url(r.display_id),
            {'status': 'pending'},
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'P')

    def test_put_status_submitted(self):
        """Testing the PUT review-requests/<id>/?status=submitted API"""
        r = self.create_review_request(submitter=self.user, publish=True)

        rsp = self.api_put(
            get_review_request_item_url(r.display_id),
            {
                'status': 'submitted',
                'close_description': 'comment',
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'S')

    @add_fixtures(['test_site'])
    def test_put_status_submitted_with_site(self):
        """Testing the PUT review-requests/<id>/?status=submitted API
        with a local site
        """
        self._login_user(local_site=True)
        r = self.create_review_request(submitter='doc', with_local_site=True,
                                       publish=True)

        rsp = self.api_put(
            get_review_request_item_url(r.display_id, self.local_site_name),
            {
                'status': 'submitted',
                'close_description': 'comment'
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'S')

    @add_fixtures(['test_site'])
    def test_put_status_submitted_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/?status=submitted API
        with a local site and Permission Denied error
        """
        r = self.create_review_request(submitter='doc', with_local_site=True,
                                       publish=True)

        self.api_put(
            get_review_request_item_url(r.display_id, self.local_site_name),
            {'status': 'submitted'},
            expected_status=403)

    def test_put_status_as_other_user_with_permission(self):
        """Testing the PUT review-requests/<id>/?status= API
        as another user with permission
        """
        self.user.user_permissions.add(
            Permission.objects.get(codename='can_change_status'))

        self._test_put_status_as_other_user()

    def test_put_status_as_other_user_with_admin(self):
        """Testing the PUT review-requests/<id>/?status= API
        as another user with admin
        """
        self._login_user(admin=True)

        self._test_put_status_as_other_user()

    def test_put_status_as_other_user_not_allowed(self):
        """Testing the PUT review-requests/<id>/?status=pending API
        as another user not allowed
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter.username,
                            self.user.username)

        self.api_put(
            get_review_request_item_url(review_request.display_id),
            {
                'status': 'submitted',
            },
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_status_as_other_user_with_site_and_permission(self):
        """Testing the PUT review-requests/<id>/?status=pending API
        as another user with local site and permission
        """
        self.user = self._login_user(local_site=True)

        local_site = self.get_local_site(name=self.local_site_name)

        site_profile = LocalSiteProfile.objects.create(
            local_site=local_site,
            user=self.user,
            profile=self.user.get_profile())
        site_profile.permissions['reviews.can_change_status'] = True
        site_profile.save()

        self._test_put_status_as_other_user(local_site)

    @add_fixtures(['test_site'])
    def test_put_status_as_other_user_with_site_and_admin(self):
        """Testing the PUT review-requests/<id>/?status=pending API
        as another user with local site and admin
        """
        self.user = self._login_user(local_site=True, admin=True)

        self._test_put_status_as_other_user(
            self.get_local_site(name=self.local_site_name))

    def _test_put_status_as_other_user(self, local_site=None):
        review_request = self.create_review_request(
            submitter='dopey',
            publish=True,
            with_local_site=(local_site is not None))

        if local_site:
            local_site_name = local_site.name
        else:
            local_site_name = None

        rsp = self.api_put(
            get_review_request_item_url(review_request.display_id,
                                        local_site_name),
            {
                'status': 'submitted',
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.status, 'S')


class ErrorTests(SpyAgency, BaseWebAPITestCase):
    """Tests for handling errors."""
    fixtures = ['test_users']

    def test_publishing_error(self):
        """Testing triggering a PublishError during a review request publish"""
        def callback(*args, **kwargs):
            raise PublishError('')

        self.spy_on(callback)

        review_request = self.create_review_request(submitter=self.user)
        ReviewRequestDraft.create(review_request)

        review_request_publishing.connect(callback)
        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {
                'public': 1
            },
            expected_status=PUBLISH_ERROR.http_status)
        review_request_publishing.disconnect(callback)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)

        self.assertTrue(callback.spy.called)
        self.assertFalse(review_request.public)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('err', rsp)
        self.assertIn('msg', rsp['err'])
        self.assertEqual(rsp['err']['msg'], six.text_type(PublishError('')))

    def test_reopening_error(self):
        """Testing triggering a ReopenError during a review request reopen"""
        def callback(*args, **kwargs):
            raise ReopenError('')

        self.spy_on(callback)

        review_request = self.create_review_request(submitter=self.user,
                                                    public=True)
        review_request.close(ReviewRequest.SUBMITTED, user=self.user)

        review_request_reopening.connect(callback)
        rsp = self.api_put(
            get_review_request_item_url(review_request.display_id),
            {
                'status': 'pending'
            },
            expected_status=REOPEN_ERROR.http_status)
        review_request_reopening.disconnect(callback)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)

        self.assertTrue(callback.spy.called)
        self.assertEqual(review_request.status, ReviewRequest.SUBMITTED)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('err', rsp)
        self.assertIn('msg', rsp['err'])
        self.assertEqual(rsp['err']['msg'], six.text_type(ReopenError('')))

    def test_closing_error(self):
        """Testing triggering a CloseError during a review request close"""
        def callback(*args, **kwargs):
            raise CloseError('')

        self.spy_on(callback)

        review_request = self.create_review_request(submitter=self.user,
                                                    public=True)

        review_request_closing.connect(callback)
        rsp = self.api_put(
            get_review_request_item_url(review_request.display_id),
            {
                'status': 'discarded'
            },
            expected_status=CLOSE_ERROR.http_status)
        review_request_closing.disconnect(callback)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)

        self.assertTrue(callback.spy.called)
        self.assertEqual(review_request.status, ReviewRequest.PENDING_REVIEW)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertIn('err', rsp)
        self.assertIn('msg', rsp['err'])
        self.assertEqual(rsp['err']['msg'], six.text_type(CloseError('')))
