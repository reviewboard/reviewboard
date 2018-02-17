"""Unit tests for reviewboard.reviews.views.ReviewFileAttachmentView."""

from __future__ import unicode_literals

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ReviewFileAttachmentViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.ReviewFileAttachmentView."""

    fixtures = ['test_users']

    def test_access_with_valid_id(self):
        """Testing ReviewFileAttachmentView access with valid attachment for
        review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_valid_id_and_draft(self):
        """Testing ReviewFileAttachmentView access with valid attachment for
        review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_invalid_id(self):
        """Testing ReviewFileAttachmentView access with invalid attachment for
        review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_with_invalid_id_and_draft(self):
        """Testing ReviewFileAttachmentView access with invalid attachment for
        review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_with_valid_inactive_id(self):
        """Testing ReviewFileAttachmentView access with valid inactive
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, active=False)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_valid_inactive_id_draft(self):
        """Testing ReviewFileAttachmentView access with valid inactive
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True,
                                                 active=False)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_invalid_inactive_id(self):
        """Testing ReviewFileAttachmentView access with invalid inactive
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, active=False)

        review_request2 = self.create_review_request(publish=True)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_invalid_inactive_id_draft(self):
        """Testing ReviewFileAttachmentView access with invalid inactive
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request, draft=True,
                                                 active=False)

        review_request2 = self.create_review_request(publish=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request2.pk,
                    'file_attachment_id': attachment.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_with_valid_diff_against_id(self):
        """Testing ReviewFileAttachmentView access with valid diff-against
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)
        attachment2 = self.create_file_attachment(review_request)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_valid_diff_against_id_draft(self):
        """Testing ReviewFileAttachmentView access with valid diff-against
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)
        attachment2 = self.create_file_attachment(review_request, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 200)

    def test_access_with_invalid_diff_against_id(self):
        """Testing ReviewFileAttachmentView access with invalid diff-against
        attachment for review request
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        review_request2 = self.create_review_request(publish=True)
        attachment2 = self.create_file_attachment(review_request2)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 404)

    def test_access_invalid_diff_against_id_draft(self):
        """Testing ReviewFileAttachmentView access with invalid diff-against
        attachment for review request draft
        """
        review_request = self.create_review_request(publish=True)
        attachment = self.create_file_attachment(review_request)

        review_request2 = self.create_review_request(publish=True)
        attachment2 = self.create_file_attachment(review_request2, draft=True)

        # Log in so that we can check against the draft.
        username = review_request.submitter.username
        self.client.login(username=username, password=username)

        response = self.client.get(
            local_site_reverse(
                'file-attachment',
                kwargs={
                    'review_request_id': review_request.pk,
                    'file_attachment_id': attachment.pk,
                    'file_attachment_diff_id': attachment2.pk,
                }))
        self.assertEqual(response.status_code, 404)
