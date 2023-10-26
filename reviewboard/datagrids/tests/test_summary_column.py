"""Unit tests for reviewboard.datagrids.columns.SummaryColumn.

Version Added:
    5.0.7
"""

from __future__ import annotations

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.datagrids.columns import SummaryColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase
from reviewboard.reviews.models import ReviewRequest


class SummaryColumnTests(BaseColumnTestCase):
    """Testing reviewboard.datagrids.columns.SummaryColumn."""

    column = SummaryColumn()

    def test_render_data(self):
        """Testing SummaryColumn.render_data"""
        review_request = self.create_review_request(summary='Summary 1',
                                                    publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<span>Summary 1</span>')

    def test_render_data_with_draft(self):
        """Testing SummaryColumn.render_data with draft review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_draft_summary(self):
        """Testing SummaryColumn.render_data with draft summary"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = 'Draft Summary 1'
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<span>Draft Summary 1</span>')

    def test_render_data_with_draft_and_no_summary(self):
        """Testing SummaryColumn.render_data with draft and no summary"""
        review_request = self.create_review_request(
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        review_request.summary = None

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<span class="no-summary">No Summary</span>')

    def test_render_data_with_archived(self):
        """Testing SummaryColumn.render_data with archived review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user,
            publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.ARCHIVED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-archived">Archived</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_muted(self):
        """Testing SummaryColumn.render_data with muted review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user,
            publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.MUTED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-muted">Muted</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_draft_and_archived(self):
        """Testing SummaryColumn.render_data with draft and archived
        review request
        """
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.ARCHIVED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<label class="label-archived">Archived</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_draft_and_muted(self):
        """Testing SummaryColumn.render_data with draft and muted
        review request
        """
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.MUTED

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-draft">Draft</label>'
            '<label class="label-muted">Muted</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_submitted(self):
        """Testing SummaryColumn.render_data with submitted review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            status=ReviewRequest.SUBMITTED,
            submitter=self.request.user,
            public=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-submitted">Submitted</label>'
            '<span>Summary 1</span>')

    def test_render_data_with_discarded(self):
        """Testing SummaryColumn.render_data with discarded review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            status=ReviewRequest.DISCARDED,
            submitter=self.request.user,
            public=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<label class="label-discarded">Discarded</label>'
            '<span>Summary 1</span>')
