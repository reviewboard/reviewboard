"""Unit tests for reviewboard.reviews.views.PreviewReviewEmailView."""

from __future__ import unicode_literals

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class PreviewReviewEmailViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.PreviewReviewEmailView."""

    fixtures = ['test_users', 'test_scmtools']

    def test_access_with_debug(self):
        """Testing PreviewReviewEmailView access with DEBUG=True"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'message_format': 'text',
                    }))

        self.assertEqual(response.status_code, 200)

    def test_access_without_debug(self):
        """Testing PreviewReviewEmailView access with DEBUG=False"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        with self.settings(DEBUG=False):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'message_format': 'text',
                    }))

        self.assertEqual(response.status_code, 404)

    def test_reply_access_with_debug(self):
        """Testing PreviewReviewEmailView with reply access and DEBUG=True"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review, publish=True)

        with self.settings(DEBUG=True):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-reply-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'reply_id': reply.pk,
                        'message_format': 'text',
                    }))

        self.assertEqual(response.status_code, 200)

    def test_reply_access_without_debug(self):
        """Testing PreviewReviewEmailView with reply access and DEBUG=False"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review, publish=True)

        with self.settings(DEBUG=False):
            response = self.client.get(
                local_site_reverse(
                    'preview-review-reply-email',
                    kwargs={
                        'review_request_id': review_request.pk,
                        'review_id': review.pk,
                        'reply_id': reply.pk,
                        'message_format': 'text',
                    }))

        self.assertEqual(response.status_code, 404)
