"""Unit tests for reviewboard.datagrids.columns.SummaryColumn.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.datagrids.columns import SummaryColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase
from reviewboard.reviews.models import ReviewRequest


class SummaryColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.SummaryColumn."""

    column = SummaryColumn()

    def test_render_data(self):
        """Testing SummaryColumn.render_data"""
        review_request = self.create_review_request(summary='Summary 1',
                                                    publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '<span>Summary 1</span>')

    def test_render_data_with_draft(self):
        """Testing SummaryColumn.render_data with draft review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
                         '<label class="label-submitted">Completed</label>'
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

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value,
                         '<label class="label-discarded">Discarded</label>'
                         '<span>Summary 1</span>')

    def test_to_json(self) -> None:
        """Testing SummaryColumn.to_json"""
        review_request = self.create_review_request(summary='Summary 1',
                                                    publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [],
                'summary': 'Summary 1',
            })

    def test_to_json_with_draft(self) -> None:
        """Testing SummaryColumn.to_json with draft review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Draft',
                        'status': 'draft',
                    },
                ],
                'summary': 'Summary 1',
            })

    def test_to_json_with_draft_summary(self) -> None:
        """Testing SummaryColumn.to_json with draft summary"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = 'Draft Summary 1'
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Draft',
                        'status': 'draft',
                    },
                ],
                'summary': 'Draft Summary 1',
            })

    def test_to_json_with_draft_and_no_summary(self) -> None:
        """Testing SummaryColumn.to_json with draft and no summary"""
        review_request = self.create_review_request(
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        review_request.summary = None

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Draft',
                        'status': 'draft',
                    },
                ],
                'summary': None,
            })

    def test_to_json_with_archived(self) -> None:
        """Testing SummaryColumn.to_json with archived review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user,
            publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.ARCHIVED

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Archived',
                        'status': 'archived',
                    },
                ],
                'summary': 'Summary 1',
            })

    def test_to_json_with_muted(self) -> None:
        """Testing SummaryColumn.to_json with muted review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user,
            publish=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.MUTED

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Muted',
                        'status': 'muted',
                    },
                ],
                'summary': 'Summary 1',
            })

    def test_to_json_with_draft_and_archived(self) -> None:
        """Testing SummaryColumn.to_json with draft and archived
        review request
        """
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.ARCHIVED

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Draft',
                        'status': 'draft',
                    },
                    {
                        'label': 'Archived',
                        'status': 'archived',
                    },
                ],
                'summary': 'Summary 1',
            })

    def test_to_json_with_draft_and_muted(self) -> None:
        """Testing SummaryColumn.to_json with draft and muted
        review request
        """
        review_request = self.create_review_request(
            summary='Summary 1',
            submitter=self.request.user)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.MUTED

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Draft',
                        'status': 'draft',
                    },
                    {
                        'label': 'Muted',
                        'status': 'muted',
                    },
                ],
                'summary': 'Summary 1',
            })

    def test_to_json_with_submitted(self) -> None:
        """Testing SummaryColumn.to_json with submitted review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            status=ReviewRequest.SUBMITTED,
            submitter=self.request.user,
            public=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Completed',
                        'status': 'completed',
                    },
                ],
                'summary': 'Summary 1',
            })

    def test_to_json_with_discarded(self) -> None:
        """Testing SummaryColumn.to_json with discarded review request"""
        review_request = self.create_review_request(
            summary='Summary 1',
            status=ReviewRequest.DISCARDED,
            submitter=self.request.user,
            public=True)

        # These are generally set by the column's augment_queryset().
        review_request.draft_summary = None
        review_request.visibility = ReviewRequestVisit.VISIBLE

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'labels': [
                    {
                        'label': 'Discarded',
                        'status': 'discarded',
                    },
                ],
                'summary': 'Summary 1',
            })
