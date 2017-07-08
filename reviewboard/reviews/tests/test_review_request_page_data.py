"""Unit tests for ReviewRequestPageData."""

from __future__ import unicode_literals

from datetime import timedelta

from django.test.client import RequestFactory
from django.utils import timezone

from reviewboard.reviews.detail import ReviewRequestPageData
from reviewboard.reviews.models import BaseComment, ReviewRequestDraft
from reviewboard.testing import TestCase


class ReviewRequestPageDataTests(TestCase):
    """Unit tests for ReviewRequestPageData."""

    fixtures = ['test_scmtools', 'test_users']

    def test_query_data_pre_etag(self):
        """Testing ReviewRequestPageData.query_data_pre_etag"""
        self._populate_review_request()

        request = RequestFactory().get('/r/1/')
        request.user = self.review_request.submitter

        data = ReviewRequestPageData(review_request=self.review_request,
                                     request=request)
        data.query_data_pre_etag()

        self.assertEqual(data.reviews, [self.review2, self.review1])
        self.assertEqual(data.latest_review_timestamp, self.review2.timestamp)
        self.assertEqual(data.changedescs, [self.changedesc2,
                                            self.changedesc1])
        self.assertEqual(data.latest_changedesc_timestamp,
                         self.changedesc2.timestamp)
        self.assertEqual(data.draft, self.draft)
        self.assertEqual(data.diffsets, [self.diffset1, self.diffset2])
        self.assertEqual(
            data.diffsets_by_id,
            {
                1: self.diffset1,
                2: self.diffset2,
            })
        self.assertEqual(data.status_updates, [self.status_update1,
                                               self.status_update2])

    def test_query_data_post_etag(self):
        """Testing ReviewRequestPageData.query_data_post_etag"""
        self._populate_review_request()

        request = RequestFactory().get('/r/1/')
        request.user = self.review_request.submitter

        data = ReviewRequestPageData(review_request=self.review_request,
                                     request=request)
        data.query_data_pre_etag()
        data.query_data_post_etag()

        self.assertEqual(
            data.reviews_by_id,
            {
                1: self.review1,
                2: self.review2,
            })
        self.assertEqual(data.review_request_details, self.draft)
        self.assertEqual(data.active_file_attachments,
                         [self.file_attachment1, self.file_attachment2])
        self.assertEqual(data.all_file_attachments,
                         [self.file_attachment1, self.file_attachment2,
                          self.inactive_file_attachment1])
        self.assertEqual(
            data.file_attachments_by_id,
            {
                1: self.file_attachment1,
                2: self.file_attachment2,
                3: self.inactive_file_attachment1,
            })
        self.assertEqual(data.active_screenshots,
                         [self.screenshot1, self.screenshot2])
        self.assertEqual(data.all_screenshots,
                         [self.screenshot1, self.screenshot2,
                          self.inactive_screenshot1])
        self.assertEqual(
            data.screenshots_by_id,
            {
                1: self.screenshot1,
                2: self.screenshot2,
                3: self.inactive_screenshot1,
            })
        self.assertEqual(
            data.comments,
            [
                self.diff_comment1, self.diff_comment2,
                self.screenshot_comment1, self.screenshot_comment2,
                self.file_attachment_comment1, self.file_attachment_comment2,
                self.general_comment1, self.general_comment2,
            ])
        self.assertEqual(
            data.issues,
            [
                self.diff_comment1, self.diff_comment2,
                self.file_attachment_comment1, self.file_attachment_comment2,
                self.general_comment1, self.general_comment2,
            ])
        self.assertEqual(
            data.issue_counts,
            {
                'total': 6,
                'open': 2,
                'resolved': 2,
                'dropped': 2,
            })

    def _populate_review_request(self):
        now = timezone.now()

        # Create the review request, diffs, attachments, and screenshots.
        self.review_request = self.create_review_request(
            create_repository=True,
            publish=True)

        self.diffset1 = self.create_diffset(self.review_request)
        self.filediff1 = self.create_filediff(self.diffset1)

        self.diffset2 = self.create_diffset(self.review_request)
        self.filediff2 = self.create_filediff(self.diffset2)

        self.file_attachment1 = \
            self.create_file_attachment(self.review_request)
        self.file_attachment2 = \
            self.create_file_attachment(self.review_request)
        self.inactive_file_attachment1 = \
            self.create_file_attachment(self.review_request, active=False)

        self.screenshot1 = self.create_screenshot(self.review_request)
        self.screenshot2 = self.create_screenshot(self.review_request)
        self.inactive_screenshot1 = \
            self.create_screenshot(self.review_request, active=False)

        # Create a draft for this review request.
        self.draft = ReviewRequestDraft.create(self.review_request)

        # Create some reviews.
        self.review1 = self.create_review(self.review_request,
                                          timestamp=now,
                                          publish=True)
        self.general_comment1 = self.create_general_comment(
            self.review1,
            issue_opened=True,
            issue_status=BaseComment.OPEN)
        self.diff_comment1 = self.create_diff_comment(
            self.review1,
            self.filediff1,
            issue_opened=True,
            issue_status=BaseComment.RESOLVED)
        self.file_attachment_comment1 = self.create_file_attachment_comment(
            self.review1,
            self.file_attachment1,
            issue_opened=True,
            issue_status=BaseComment.DROPPED)
        self.screenshot_comment1 = self.create_screenshot_comment(
            self.review1,
            self.screenshot1,
            issue_opened=False)

        self.review2 = self.create_review(self.review_request,
                                          timestamp=now + timedelta(days=1),
                                          publish=True)
        self.general_comment2 = self.create_general_comment(
            self.review2,
            issue_opened=True,
            issue_status=BaseComment.OPEN)
        self.diff_comment2 = self.create_diff_comment(
            self.review2,
            self.filediff2,
            issue_opened=True,
            issue_status=BaseComment.RESOLVED)
        self.file_attachment_comment2 = self.create_file_attachment_comment(
            self.review2,
            self.file_attachment2,
            issue_opened=True,
            issue_status=BaseComment.DROPPED)
        self.screenshot_comment2 = self.create_screenshot_comment(
            self.review2,
            self.screenshot2,
            issue_opened=False)

        # Create some change descriptions.
        self.changedesc1 = self.review_request.changedescs.create(
            timestamp=now + timedelta(days=2),
            public=True)
        self.changedesc2 = self.review_request.changedescs.create(
            timestamp=now + timedelta(days=3),
            public=True)

        # Create some status updates.
        self.status_update1 = self.create_status_update(self.review_request)
        self.status_update2 = self.create_status_update(self.review_request)
