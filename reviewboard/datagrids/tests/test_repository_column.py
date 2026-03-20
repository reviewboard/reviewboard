"""Unit tests for reviewboard.datagrids.columns.RepositoryColumn.

Version Added:
    7.1
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import RepositoryColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class RepositoryColumnTests(BaseColumnTestCase):
    """Testing reviewboard.datagrids.columns.RepositoryColumn.

    Version Added:
        7.1
    """

    column = RepositoryColumn()

    def test_render_data_with_no_repository(self) -> None:
        """Testing RepositoryColumn.render_data with no repository"""
        review_request = self.create_review_request(publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_repository(self) -> None:
        """Testing RepositoryColumn.render_data with repository"""
        repository = self.create_repository(tool_name='Test',
                                            name='Test <Repo>')
        review_request = self.create_review_request(
            repository=repository,
            publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, 'Test &lt;Repo&gt;')

    def test_to_json_with_no_repository(self) -> None:
        """Testing RepositoryColumn.to_json with no repository"""
        review_request = self.create_review_request(publish=True)

        self.assertIsNone(
            self.column.to_json(self.stateful_column, review_request))

    def test_to_json_with_repository(self) -> None:
        """Testing RepositoryColumn.to_json with repository"""
        repository = self.create_repository(name='My Repo', tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            publish=True)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            repository)
