"""Tests for reviewboard.reviews.signal_handlers.

Version Added:
    6.0
"""

from __future__ import annotations

import kgb

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.signal_handlers import \
    _on_review_request_draft_deleted
from reviewboard.testing import TestCase


class OnReviewRequestDraftDeletedTests(kgb.SpyAgency, TestCase):
    """Tests _on_review_request_draft_deleted() signal handler.

    Version Added:
        6.0
    """

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()
        self.review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        self.draft = self.create_review_request_draft(self.review_request)

    def test_with_file_attachments(self) -> None:
        """Testing _on_review_request_draft_deleted deletes new and new
        revision draft file attachments
        """
        self.spy_on(_on_review_request_draft_deleted)

        published = self.create_file_attachment(self.review_request)
        new = self.create_file_attachment(self.review_request, draft=True)
        new_revision = self.create_file_attachment(
            self.review_request,
            attachment_history=published.attachment_history,
            attachment_revision=published.attachment_revision + 1,
            draft=True)

        # 34 queries:
        #
        #   1-7. Fetch review request draft info and relations
        #  8-13. Fetch file attachments info
        # 14-17. Build file attachments data for getting states
        # 18-33. Delete the file attachments from the review request draft
        #    34. Delete the review request draft
        with self.assertNumQueries(34):
            self.draft.delete()

        all_attachments = FileAttachment.objects.all()

        self.assertSpyCalled(_on_review_request_draft_deleted)
        self.assertNotIn(new, all_attachments)
        self.assertNotIn(new_revision, all_attachments)
        self.assertIn(published, all_attachments)

    def test_with_one_file_attachment(self) -> None:
        """Testing _on_review_request_draft_deleted deletes a new file
        attachment
        """
        self.spy_on(_on_review_request_draft_deleted)

        published = self.create_file_attachment(self.review_request)
        new = self.create_file_attachment(self.review_request, draft=True)

        # 23 queries:
        #
        #   1-7. Fetch review request draft info and relations
        #  8-13. Fetch file attachments info
        # 14-17. Build file attachments data for getting states
        # 18-22. Delete the file attachment from the review request draft
        #    23. Delete the review request draft
        with self.assertNumQueries(23):
            self.draft.delete()

        all_attachments = FileAttachment.objects.all()

        self.assertSpyCalled(_on_review_request_draft_deleted)
        self.assertNotIn(new, all_attachments)
        self.assertIn(published, all_attachments)

    def test_with_no_file_attachments(self) -> None:
        """Testing _on_review_request_draft_deleted when there's no
        draft file attachments on the review request
        """
        self.spy_on(_on_review_request_draft_deleted)

        # 8 queries:
        #
        # 1-7. Fetch review request draft info and relations
        #   8. Delete the review request draft
        with self.assertNumQueries(8):
            self.draft.delete()

        self.assertSpyCalled(_on_review_request_draft_deleted)
