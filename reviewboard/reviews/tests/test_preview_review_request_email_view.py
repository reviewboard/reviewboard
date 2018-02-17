"""Unit tests for reviewboard.reviews.views.PreviewReviewRequestEmailView."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class PreviewReviewRequestEmailViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.PreviewReviewRequestEmailView.
    """

    fixtures = ['test_users', 'test_scmtools']

    def test_access_with_debug(self):
        """Testing PreviewReviewRequestEmailView access with DEBUG=True"""
        review_request = self.create_review_request(publish=True)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'message_format': 'text',
                    }))

        self.assertEqual(response.status_code, 200)

    def test_access_without_debug(self):
        """Testing PreviewReviewRequestEmailView access with DEBUG=False"""
        review_request = self.create_review_request(publish=True)

        with self.settings(DEBUG=False):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'message_format': 'text',
                    }))

        self.assertEqual(response.status_code, 404)

    def test_with_valid_change_id(self):
        """Testing PreviewReviewRequestEmailView access with valid change ID"""
        user = User.objects.create_user('test_user')
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True,
                                                    target_people=[user])

        self.create_diffset(review_request, draft=True)
        review_request.publish(review_request.submitter)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'message_format': 'text',
                        'changedesc_id': review_request.changedescs.get().pk,
                    }))

        self.assertEqual(response.status_code, 200)

    def test_with_invalid_change_id(self):
        """Testing PreviewReviewRequestEmailView access with invalid change ID
        """
        user = User.objects.create_user('test_user')
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True,
                                                    target_people=[user])

        self.create_diffset(review_request, draft=True)
        review_request.publish(review_request.submitter)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-request-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'message_format': 'text',
                        'changedesc_id': 100,
                    }))

        self.assertEqual(response.status_code, 404)
