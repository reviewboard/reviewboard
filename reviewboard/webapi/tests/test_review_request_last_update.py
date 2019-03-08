"""Tests for the ReviewRequestLastUpdateResource."""

from __future__ import unicode_literals

from dateutil.parser import parse as parse_date
from django.contrib.auth.models import User
from django.utils import six
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import (Review, ReviewRequest,
                                        ReviewRequestDraft)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    review_request_last_update_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_review_request_last_update_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing ReviewRequestLastUpdateResource APIs."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/last-update/'
    test_http_methods = ('GET',)
    resource = resources.review_request_last_update

    def compare_item(self, item_rsp, review_request, expected_user=None):
        """Compare a response to a review request.

        Args:
            item_rsp (dict):
                A dictionary of serialized data from the resource.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request whose latest activity will be used for
                comparison.

            expected_user (django.contrib.auth.models.User, optional):
                The user we expected to be serialized in ``item_rsp``.

                If not provided, this defaults to ``review_request.submitter``.

        Raises:
            AssertionError:
                The serialized response does not correspond with the given
                review request or user.
        """
        if expected_user is None:
            expected_user = review_request.submitter

        item_type = item_rsp['type']
        last_updated = review_request.last_updated.replace(microsecond=0)

        last_activity = review_request.get_last_activity_info()
        updated_object = last_activity['updated_object']
        changedesc = last_activity['changedesc']

        rsp_timestamp = parse_date(item_rsp['timestamp']).replace(
            microsecond=0)

        if item_type == 'review-request':
            self.assertIsInstance(updated_object, ReviewRequest)
            self.assertEqual(updated_object, review_request)
            object_timestamp = updated_object.last_updated
        elif item_type == 'diff':
            self.assertIsInstance(updated_object, DiffSet)
            object_timestamp = updated_object.timestamp
        elif item_type in ('review', 'reply'):
            self.assertIsInstance(updated_object, Review)
            object_timestamp = updated_object.timestamp

            self.assertIsNone(last_activity['changedesc'])
        else:
            self.fail('Unknown item type "%s"' % item_type)

        object_timestamp = object_timestamp.replace(microsecond=0)

        self.assertEqual(last_updated, object_timestamp)
        self.assertEqual(last_updated, rsp_timestamp)

        if changedesc:
            self.assertEqual(expected_user,
                             changedesc.get_user(review_request))

        self.assertEqual(expected_user.pk,
                         item_rsp['user']['id'])

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site=False,
                             local_site_name=None, update_review_request=False,
                             update_diffset=False, update_review=False,
                             update_reply=False, publish_user=None):
        """Setup a basic HTTP GET test.

        Args:
            user (django.contrib.auth.models.User):
                The user that will be used to retrieve the resource.

                They will also be the submitter/author of all objects (although
                not necessary the publisher).

            with_local_site (boolean, optional):
                Whether or not a LocalSite-specific resource will be used.

            local_site_name (unicode, optional):
                The name of the LocalSite to use.

            update_review_request (boolean, optional):
                Whether or not the review request should be updated after
                publishing.

            update_diffset (boolean, optional):
                Whether or not the review request should be updated with a diff
                after publishing.

            update_review (boolean, optional):
                Whether or not the review request should be reviewed after
                publishing.

            update_reply (boolean, optional):
                Whther or not to create a reply.

                This implies ``update_review``.

            publish_user (django.contrib.auth.models.User, optional):
                The user that will trigger the update (i.e., they will publish
                all requested objects).

                If not provided, ``user`` will be used.

        Returns:
            tuple:
            A 3-tuple of:

            * The URL to request.
            * The expected mimetype.
            * The review request to use for comparison.
        """
        update_review = update_review or update_reply
        publish_user = publish_user or user
        review_request = self.create_review_request(
            create_repository=True,
            submitter=user,
            with_local_site=with_local_site,
            target_people=[user])

        review_request.publish(user=publish_user)

        if update_review_request:
            draft = ReviewRequestDraft.create(review_request)
            draft.summary = '%s updated' % review_request.summary
            draft.save()

            review_request.publish(user=publish_user)

        if update_diffset:
            self.create_diffset(review_request=review_request, draft=True)
            review_request.publish(user=publish_user)

        if update_review:
            review = self.create_review(review_request=review_request,
                                        user=user,
                                        publish=False)
            review.publish(user=publish_user)

            if update_reply:
                reply = self.create_reply(review, user=user)
                reply.publish(user=publish_user)

        return (
            get_review_request_last_update_url(local_site_name=local_site_name,
                                               review_request=review_request),
            review_request_last_update_mimetype,
            review_request,
        )

    @webapi_test_template
    def test_get_other_user(self):
        """Testing the GET <URL> API when the review request has been published
        by another user
        """
        publish_user = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            publish_user=publish_user)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'review-request')

        # We have no way of knowing what user published based on only the
        # model, so it will always be the submitter.
        self.compare_item(item_rsp, review_request, expected_user=self.user)

    @webapi_test_template
    def test_get_review_request_updated(self):
        """Testing the GET <URL> API when the review request has been updated
        """
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_review_request=True)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'review-request')
        self.compare_item(item_rsp, review_request)

    @webapi_test_template
    def test_get_review_request_updated_other_user(self):
        """Testing the GET <URL> API when a review request has been updated
        by a different user
        """
        publish_user = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_review_request=True,
            publish_user=publish_user)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'review-request')
        self.compare_item(item_rsp, review_request, expected_user=publish_user)

    @webapi_test_template
    def test_get_diff_updated(self):
        """Testing the GET <URL> API when a new diff has been published"""
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_diffset=True)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'diff')
        self.compare_item(rsp['last_update'], review_request)

    @webapi_test_template
    def test_get_diff_updated_other_user(self):
        """Testing the GET <URL> API when a new diff has been published by
        another user
        """
        publish_user = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_diffset=True,
            publish_user=publish_user)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'diff')
        self.compare_item(item_rsp, review_request, expected_user=publish_user)

    @webapi_test_template
    def test_get_review_published(self):
        """Testing the GET <URL> API when a review has been published"""
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_review=True)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'review')
        self.compare_item(item_rsp, review_request)

    @webapi_test_template
    def test_get_review_published_other_user(self):
        """Testing the GET <URL> API when a review has been published by
        another user
        """
        publish_user = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_review=True,
            publish_user=publish_user)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'review')

        # We have no way of knowing what user published based on only the
        # model, so it will always be the review author.
        self.compare_item(item_rsp, review_request, expected_user=self.user)

    @webapi_test_template
    def test_get_review_published_not_submitter(self):
        """Testing the GET <URL> API when a review has been published by
        an user that is not the submitter
        """
        submitter = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            submitter)
        self.create_review(review_request=review_request,
                           user=self.user,
                           publish=True)

        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'review')
        self.compare_item(item_rsp, review_request, expected_user=self.user)

    @webapi_test_template
    def test_get_reply_published(self):
        """Testing the GET <URL> API when a review reply has been published"""
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_reply=True)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'reply')
        self.compare_item(item_rsp, review_request)

    @webapi_test_template
    def test_get_reply_published_other_user(self):
        """Testing the GET <URL> API when a review reply has been published by
        another user
        """
        publish_user = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_reply=True,
            publish_user=publish_user)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'reply')

        # We have no way of knowing what user published based on only the
        # model, so it will always be the review author.
        self.compare_item(item_rsp, review_request, expected_user=self.user)

    @webapi_test_template
    def test_get_reply_published_not_submitter(self):
        """Testing the GET <URL> API when a review reply has been published by
        an user that is not the submitter
        """
        submitter = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            submitter)
        review = self.create_review(review_request=review_request,
                                    user=self.user,
                                    publish=True)
        self.create_reply(review, user=self.user, publish=True)

        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'reply')
        self.compare_item(item_rsp, review_request, expected_user=self.user)

    @webapi_test_template
    def test_get_review_request_updated_review_published_other_user(self):
        """Testing the GET <URL> API when a review request has been updated
        and a review request has been published
        """
        publish_user = User.objects.get(username='admin')
        url, expected_mimetype, review_request = self.setup_basic_get_test(
            self.user,
            update_review_request=True,
            update_review=True,
            publish_user=publish_user)
        rsp = self.api_get(url, expected_mimetype=expected_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['last_update']

        self.assertEqual(item_rsp['type'], 'review')

        # We have no way of knowing what user published based on only the
        # model, so it will always be the review author.
        self.compare_item(item_rsp, review_request, expected_user=self.user)
