"""Unit tests for reviewboard.datagrids.columns.ShipItColumn.

Version Added:
    5.0.7
"""

from __future__ import annotations

from datetime import timedelta

from reviewboard.datagrids.columns import ShipItColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class ShipItColumnTests(BaseColumnTestCase):
    """Testing reviewboard.datagrids.columns.ShipItColumn."""

    column = ShipItColumn()

    def test_render_data_with_none(self):
        """Testing ShipItColumn.render_data with 0 Ship It!'s, 0 issues"""
        review_request = self.create_review_request(publish=True)

        self.assertEqual(
            self.column.render_data(self.stateful_column, review_request),
            '')

    def test_render_data_with_one_shipit(self):
        """Testing ShipItColumn.render_data with 1 Ship It!"""
        review_request = self.create_review_request(publish=True)
        review_request.shipit_count = 1
        review_request.last_review_activity_timestamp = (
            review_request.last_updated + timedelta(hours=1))

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="shipit-count-container"'
            '     title="1 Ship It!"'
            '     aria-label="1 Ship It!">'
            ' <span aria-hidden="true" class="shipit-count">'
            '  <span class="rb-icon rb-icon-datagrid-shipit"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_shipits(self):
        """Testing ShipItColumn.render_data with many Ship It!'s"""
        review_request = self.create_review_request(publish=True)
        review_request.shipit_count = 2
        review_request.last_review_activity_timestamp = (
            review_request.last_updated + timedelta(hours=1))

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="shipit-count-container"'
            '     title="2 Ship It\'s!"'
            '     aria-label="2 Ship It\'s!">'
            ' <span aria-hidden="true" class="shipit-count">'
            '  <span class="rb-icon rb-icon-datagrid-shipit"></span>'
            '  2'
            ' </span>'
            '</div>')

    def test_render_data_with_shipit_stale(self):
        """Testing ShipItColumn.render_data with Ship It!'s and stale"""
        review_request = self.create_review_request(publish=True)
        review_request.shipit_count = 1
        review_request.last_review_activity_timestamp = (
            review_request.last_updated - timedelta(hours=1))

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="shipit-count-container -is-stale"'
            '     title="1 Ship It! (New updates to review)"'
            '     aria-label="1 Ship It! (New updates to review)">'
            ' <span aria-hidden="true" class="shipit-count">'
            '  <span class="rb-icon rb-icon-datagrid-shipit"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_one_open_issue(self):
        """Testing ShipItColumn.render_data with one open issue"""
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="1 issue opened"'
            '     aria-label="1 issue opened">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_open_issues(self):
        """Testing ShipItColumn.render_data with many open issues"""
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 2
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="2 issues opened"'
            '     aria-label="2 issues opened">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  2'
            ' </span>'
            '</div>')

    def test_render_data_with_one_issue_pending_verification(self):
        """Testing ShipItColumn.render_data with one issue pending verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_verifying_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="1 issue requiring verification"'
            '     aria-label="1 issue requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_pending_verification(self):
        """Testing ShipItColumn.render_data with many issues pending
        verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_verifying_count = 2
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="2 issues requiring verification"'
            '     aria-label="2 issues requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  2'
            ' </span>'
            '</div>')

    def test_render_data_with_one_issue_and_one_pending_verification(self):
        """Testing ShipItColumn.render_data with 1 open issue and pending
        verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 1
        review_request.issue_verifying_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="1 issue opened, 1 requiring verification"'
            '     aria-label="1 issue opened, 1 requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  1'
            ' </span>'
            ' <span aria-hidden="true" class="issue-verifying-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_issues_and_one_pending_verification(self):
        """Testing ShipItColumn.render_data with many open issues and 1
        pending verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 5
        review_request.issue_verifying_count = 1
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="5 issues opened, 1 requiring verification"'
            '     aria-label="5 issues opened, 1 requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  5'
            ' </span>'
            ' <span aria-hidden="true" class="issue-verifying-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  1'
            ' </span>'
            '</div>')

    def test_render_data_with_many_issues_and_many_pending_verification(self):
        """Testing ShipItColumn.render_data with many open issues and many
        pending verification
        """
        review_request = self.create_review_request(publish=True)
        review_request.issue_open_count = 5
        review_request.issue_verifying_count = 3
        review_request.shipit_count = 1

        self.assertHTMLEqual(
            self.column.render_data(self.stateful_column, review_request),
            '<div class="issue-count-container"'
            '     title="5 issues opened, 3 requiring verification"'
            '     aria-label="5 issues opened, 3 requiring verification">'
            ' <span aria-hidden="true" class="issue-count">'
            '  <span class="rb-icon rb-icon-datagrid-open-issues"></span>'
            '  5'
            ' </span>'
            ' <span aria-hidden="true" class="issue-verifying-count">'
            '  <span class="rb-icon rb-icon-datagrid-issue-verifying"></span>'
            '  3'
            ' </span>'
            '</div>')
