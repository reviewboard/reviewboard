"""Unit tests for reviewboard.reviews.views.ReviewScreenshotView."""

from __future__ import unicode_literals

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ReviewScreenshotViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.ReviewScreenshotView."""

    fixtures = ['test_users']

    def test_access_with_valid_id(self):
        """Testing ReviewScreenshotView access with valid screenshot for review
        request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_valid_id_and_draft(self):
        """Testing ReviewScreenshotView access with valid screenshot for review
        request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_valid_inactive_id(self):
        """Testing ReviewScreenshotView access with valid inactive screenshot
        for review request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, active=False)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_valid_inactive_id_and_draft(self):
        """Testing ReviewScreenshotView access with valid inactive screenshot
        for review request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True,
                                            active=False)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_invalid_id(self):
        """Testing ReviewScreenshotView access with invalid screenshot for
        review request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_with_invalid_id_and_draft(self):
        """Testing ReviewScreenshotView access with invalid screenshot for
        review request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_with_invalid_inactive_id(self):
        """Testing ReviewScreenshotView access with invalid inactive screenshot
        for review request
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, active=False)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_with_invalid_inactive_id_and_draft(self):
        """Testing ReviewScreenshotView access with invalid inactive screenshot
        for review request draft
        """
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request, draft=True,
                                            active=False)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'screenshot',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'screenshot_id': screenshot.pk,
                }))
        self.assertEqual(response.status_code, 404)
