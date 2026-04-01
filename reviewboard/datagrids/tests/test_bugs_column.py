"""Unit tests for reviewboard.datagrids.columns.BugsColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import BugsColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class BugsColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.BugsColumn.

    Version Added:
        8.0
    """

    column = BugsColumn()

    def test_render_data_with_no_bugs(self) -> None:
        """Testing BugsColumn.render_data with no bugs"""
        review_request = self.create_review_request(publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_one_bug_no_tracker(self) -> None:
        """Testing BugsColumn.render_data with one bug and no bug tracker"""
        review_request = self.create_review_request(
            bugs_closed='1234',
            publish=True)

        html = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            '<span class="bug">1234</span>')

    def test_render_data_with_one_bug_with_tracker(self) -> None:
        """Testing BugsColumn.render_data with one bug and a bug tracker"""
        repository = self.create_repository(
            tool_name='Test',
            bug_tracker='https://bugs.example.com/%s')
        review_request = self.create_review_request(
            repository=repository,
            bugs_closed='1234',
            publish=True)

        html = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            '<a class="bug" href="/r/1/bugs/1234/">1234</a>')

    def test_render_data_with_multiple_bugs(self) -> None:
        """Testing BugsColumn.render_data with multiple bugs"""
        review_request = self.create_review_request(
            bugs_closed='1234, 5678',
            publish=True)

        html = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(html, SafeString)
        self.assertHTMLEqual(
            html,
            '<span class="bug">1234</span>, <span class="bug">5678</span>')

    def test_to_json_with_no_bugs(self) -> None:
        """Testing BugsColumn.to_json with no bugs"""
        review_request = self.create_review_request(publish=True)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            [])

    def test_to_json_with_one_bug_no_tracker(self) -> None:
        """Testing BugsColumn.to_json with one bug and no bug tracker"""
        review_request = self.create_review_request(
            bugs_closed='1234',
            publish=True)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            [{'id': '1234'}])

    def test_to_json_with_one_bug_with_tracker(self) -> None:
        """Testing BugsColumn.to_json with one bug and a bug tracker"""
        repository = self.create_repository(
            tool_name='Test',
            bug_tracker='https://bugs.example.com/%s')
        review_request = self.create_review_request(
            repository=repository,
            bugs_closed='1234',
            publish=True)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            [
                {
                    'id': '1234',
                    'url': '/r/1/bugs/1234/',
                },
            ])
