"""Unit tests for ReviewRequestPageData."""

from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.test.client import RequestFactory
from django.utils import timezone

from reviewboard.reviews.detail import (ChangeEntry,
                                        InitialStatusUpdatesEntry,
                                        ReviewEntry,
                                        ReviewRequestEntry,
                                        ReviewRequestPageData)
from reviewboard.reviews.models import BaseComment, ReviewRequestDraft
from reviewboard.testing import TestCase


class ReviewRequestPageDataTests(TestCase):
    """Unit tests for ReviewRequestPageData."""

    fixtures = ['test_scmtools', 'test_users']

    def test_query_data_pre_etag(self):
        """Testing ReviewRequestPageData.query_data_pre_etag"""
        self._test_query_data_pre_etag_with(
            expected_num_queries=6,
            expect_reviews=True,
            expect_changedescs=True,
            expect_draft=True,
            expect_status_updates=True)

    def test_query_data_pre_etag_with_only_review_request_entry(self):
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        ReviewRequestEntry in entry_classes
        """
        self._test_query_data_pre_etag_with(
            entry_classes=[ReviewRequestEntry],
            expected_num_queries=4,
            expect_reviews=True,
            expect_draft=True)

    def test_query_data_pre_etag_with_only_initial_status_updates_entry(self):
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        InitialStatusUpdatesEntry in entry_classes
        """
        self._test_query_data_pre_etag_with(
            entry_classes=[InitialStatusUpdatesEntry],
            expected_num_queries=4,
            expect_reviews=True,
            expect_status_updates=True)

    def test_query_data_pre_etag_with_only_review_entry(self):
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        ReviewEntry in entry_classes
        """
        self._test_query_data_pre_etag_with(
            entry_classes=[ReviewEntry],
            expected_num_queries=3,
            expect_reviews=True)

    def test_query_data_pre_etag_with_only_change_entry(self):
        """Testing ReviewRequestPageData.query_data_pre_etag with only
        ChangeEntry in entry_classes
        """
        self._test_query_data_pre_etag_with(
            entry_classes=[ChangeEntry],
            expected_num_queries=5,
            expect_reviews=True,
            expect_changedescs=True,
            expect_status_updates=True)

    def test_query_data_post_etag(self):
        """Testing ReviewRequestPageData.query_data_post_etag"""
        self._test_query_data_post_etag_with(
            expected_num_queries=18,
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_draft=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_review_request_entry(self):
        """Testing ReviewRequestPageData.query_data_post_etag with only
        ReviewRequestEntry in entry_classes
        """
        self._test_query_data_post_etag_with(
            entry_classes=[ReviewRequestEntry],
            expected_num_queries=18,
            expect_draft=True,
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_initial_status_updates_entry(self):
        """Testing ReviewRequestPageData.query_data_post_etag with only
        InitialStatusUpdatesEntry in entry_classes
        """
        self._test_query_data_post_etag_with(
            entry_classes=[InitialStatusUpdatesEntry],
            expected_num_queries=18,
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_review_entry(self):
        """Testing ReviewRequestPageData.query_data_post_etag with only
        ReviewEntry in entry_classes
        """
        self._test_query_data_post_etag_with(
            entry_classes=[ReviewEntry],
            expected_num_queries=18,
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_query_data_post_etag_with_only_change_entry(self):
        """Testing ReviewRequestPageData.query_data_post_etag with only
        ChangeEntry in entry_classes
        """
        self._test_query_data_post_etag_with(
            entry_classes=[ChangeEntry],
            expected_num_queries=18,
            expect_reviews=True,
            expect_file_attachments=True,
            expect_screenshots=True,
            expect_comments=True,
            expect_issues=True)

    def test_get_entries(self):
        """Testing ReviewRequestPageData.get_entries"""
        data = self._build_data()
        data.query_data_pre_etag()
        data.query_data_post_etag()

        entries = data.get_entries()

        self.assertEqual(len(entries['initial']), 1)
        self.assertEqual(len(entries['main']), 4)

        entry = entries['initial'][0]
        self.assertIsInstance(entry, InitialStatusUpdatesEntry)

        entry = entries['main'][0]
        self.assertIsInstance(entry, ReviewEntry)
        self.assertEqual(entry.review, self.review1)

        entry = entries['main'][1]
        self.assertIsInstance(entry, ChangeEntry)
        self.assertEqual(entry.changedesc, self.changedesc1)

        entry = entries['main'][2]
        self.assertIsInstance(entry, ReviewEntry)
        self.assertEqual(entry.review, self.review2)

        entry = entries['main'][3]
        self.assertIsInstance(entry, ChangeEntry)
        self.assertEqual(entry.changedesc, self.changedesc2)

    def _build_data(self, entry_classes=None):
        self._populate_review_request()

        request = RequestFactory().get('/r/1/')
        request.user = self.review_request.submitter

        return ReviewRequestPageData(review_request=self.review_request,
                                     request=request,
                                     entry_classes=entry_classes)

    def _test_query_data_pre_etag_with(self,
                                       entry_classes=None,
                                       expected_num_queries=0,
                                       expect_reviews=False,
                                       expect_changedescs=False,
                                       expect_draft=False,
                                       expect_status_updates=False):
        data = self._build_data(entry_classes=entry_classes)

        with self.assertNumQueries(expected_num_queries):
            data.query_data_pre_etag()

        if expect_reviews:
            self.assertEqual(data.reviews, [self.review2, self.review1])
            self.assertEqual(data.latest_review_timestamp,
                             self.review2.timestamp)
            self.assertEqual(data.diffsets, [self.diffset1, self.diffset2])
            self.assertEqual(
                data.diffsets_by_id,
                {
                    1: self.diffset1,
                    2: self.diffset2,
                })
        else:
            self.assertEqual(data.reviews, [])
            self.assertEqual(data.latest_review_timestamp,
                             datetime.fromtimestamp(0, timezone.utc))
            self.assertEqual(data.diffsets, [])
            self.assertEqual(data.diffsets_by_id, {})

        if expect_changedescs:
            self.assertEqual(data.changedescs, [self.changedesc2,
                                                self.changedesc1])
            self.assertEqual(data.latest_changedesc_timestamp,
                             self.changedesc2.timestamp)
        else:
            self.assertEqual(data.changedescs, [])
            self.assertIsNone(data.latest_changedesc_timestamp)

        if expect_draft:
            self.assertEqual(data.draft, self.draft)
        else:
            self.assertIsNone(data.draft)

        if expect_status_updates:
            self.assertEqual(data.all_status_updates, [self.status_update1,
                                                       self.status_update2])
        else:
            self.assertEqual(data.all_status_updates, [])

    def _test_query_data_post_etag_with(self,
                                        entry_classes=None,
                                        expected_num_queries=0,
                                        expect_draft=False,
                                        expect_reviews=False,
                                        expect_file_attachments=False,
                                        expect_screenshots=False,
                                        expect_comments=False,
                                        expect_issues=False):
        data = self._build_data(entry_classes=entry_classes)

        data.query_data_pre_etag()

        with self.assertNumQueries(expected_num_queries):
            data.query_data_post_etag()

        if expect_reviews:
            self.assertEqual(
                data.reviews_by_id,
                {
                    1: self.review1,
                    2: self.review2,
                })
        else:
            self.assertEqual(data.reviews_by_id, {})

        if expect_draft:
            self.assertEqual(data.review_request_details, self.draft)
        else:
            self.assertEqual(data.review_request_details,
                             self.review_request)

        if expect_file_attachments:
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
        else:
            self.assertEqual(data.active_file_attachments, [])
            self.assertEqual(data.all_file_attachments, [])
            self.assertEqual(data.file_attachments_by_id, {})

        if expect_screenshots:
            self.assertEqual(data.active_screenshots,
                             [self.screenshot1, self.screenshot2])
            self.assertEqual(data.all_screenshots,
                             [self.screenshot1,
                              self.screenshot2,
                              self.inactive_screenshot1])
            self.assertEqual(
                data.screenshots_by_id,
                {
                    1: self.screenshot1,
                    2: self.screenshot2,
                    3: self.inactive_screenshot1,
                })
        else:
            self.assertEqual(data.active_screenshots, [])
            self.assertEqual(data.all_screenshots, [])
            self.assertEqual(data.screenshots_by_id, {})

        if expect_comments:
            self.assertEqual(
                data.all_comments,
                [
                    self.general_comment1,
                    self.general_comment2,
                    self.screenshot_comment1,
                    self.screenshot_comment2,
                    self.file_attachment_comment1,
                    self.file_attachment_comment2,
                    self.diff_comment1,
                    self.diff_comment2,
                ])
        else:
            self.assertEqual(data.all_comments, [])

        if expect_issues:
            self.assertEqual(
                data.issues,
                [
                    self.general_comment1,
                    self.general_comment2,
                    self.file_attachment_comment1,
                    self.file_attachment_comment2,
                    self.diff_comment1,
                    self.diff_comment2,
                ])
            self.assertEqual(
                data.issue_counts,
                {
                    'total': 6,
                    'open': 2,
                    'resolved': 2,
                    'dropped': 2,
                    'verifying': 0,
                })
        else:
            self.assertEqual(data.issues, [])
            self.assertEqual(data.issue_counts, {})

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
                                          timestamp=now + timedelta(days=3),
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
            timestamp=now + timedelta(days=4),
            public=True)

        # Create some status updates.
        self.status_update1 = self.create_status_update(self.review_request)
        self.status_update2 = self.create_status_update(self.review_request)
