"""Unit tests for reviewboard.datagrids.columns.DiffSizeColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import DiffSizeColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class DiffSizeColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.DiffSizeColumn.

    Version Added:
        8.0
    """

    column = DiffSizeColumn()
    fixtures = ['test_users', 'test_scmtools']

    def test_render_data_with_no_repository(self) -> None:
        """Testing DiffSizeColumn.render_data with no repository"""
        review_request = self.create_review_request(publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_repository_no_diff(self) -> None:
        """Testing DiffSizeColumn.render_data with repository but no diff"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_inserts_and_deletes(self) -> None:
        """Testing DiffSizeColumn.render_data with inserts and deletes"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        diffset = self.create_diffset(review_request)
        self.create_filediff(
            diffset,
            extra_data={
                'raw_insert_count': 10,
                'raw_delete_count': 5,
            })

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<span class="diff-size-column insert">+10</span>&nbsp;'
            '<span class="diff-size-column delete">-5</span>')

    def test_render_data_with_inserts_only(self) -> None:
        """Testing DiffSizeColumn.render_data with inserts only"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        diffset = self.create_diffset(review_request)
        self.create_filediff(
            diffset,
            extra_data={
                'raw_insert_count': 7,
                'raw_delete_count': 0,
            })

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<span class="diff-size-column insert">+7</span>')

    def test_render_data_with_deletes_only(self) -> None:
        """Testing DiffSizeColumn.render_data with deletes only"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        diffset = self.create_diffset(review_request)
        self.create_filediff(
            diffset,
            extra_data={
                'raw_insert_count': 0,
                'raw_delete_count': 3,
            })

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertHTMLEqual(
            value,
            '<span class="diff-size-column delete">-3</span>')

    def test_to_json_with_no_repository(self) -> None:
        """Testing DiffSizeColumn.to_json with no repository"""
        review_request = self.create_review_request(publish=True)

        self.assertIsNone(self.column.to_json(self.stateful_column,
                                              review_request))

    def test_to_json_with_diff(self) -> None:
        """Testing DiffSizeColumn.to_json with diff"""
        review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        diffset = self.create_diffset(review_request)
        self.create_filediff(
            diffset,
            extra_data={
                'raw_insert_count': 10,
                'raw_delete_count': 5,
            })

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            {
                'delete_count': 5,
                'equal_count': None,
                'insert_count': 10,
                'raw_delete_count': 5,
                'raw_insert_count': 10,
                'replace_count': None,
                'total_line_count': None,
            })
