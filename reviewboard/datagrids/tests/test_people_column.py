"""Unit tests for reviewboard.datagrids.columns.PeopleColumn.

Version Added:
    8.0
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.utils.safestring import SafeString

from reviewboard.datagrids.columns import PeopleColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class PeopleColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.PeopleColumn.

    Version Added:
        8.0
    """

    column = PeopleColumn()

    def test_render_data_with_no_people(self) -> None:
        """Testing PeopleColumn.render_data with no people"""
        review_request = self.create_review_request(publish=True)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_one_person(self) -> None:
        """Testing PeopleColumn.render_data with one person"""
        review_request = self.create_review_request(publish=True)
        user = User.objects.get(username='grumpy')
        review_request.target_people.add(user)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, 'grumpy')

    def test_render_data_with_multiple_people(self) -> None:
        """Testing PeopleColumn.render_data with multiple people"""
        review_request = self.create_review_request(publish=True)
        grumpy = User.objects.get(username='grumpy')
        admin = User.objects.get(username='admin')
        review_request.target_people.add(grumpy, admin)

        value = self.column.render_data(self.stateful_column, review_request)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, 'admin grumpy')

    def test_to_json_with_no_people(self) -> None:
        """Testing PeopleColumn.to_json with no people"""
        review_request = self.create_review_request(publish=True)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            [])

    def test_to_json_with_people(self) -> None:
        """Testing PeopleColumn.to_json with people"""
        review_request = self.create_review_request(publish=True)
        grumpy = User.objects.get(username='grumpy')
        admin = User.objects.get(username='admin')
        review_request.target_people.add(grumpy, admin)

        self.assertEqual(
            self.column.to_json(self.stateful_column, review_request),
            [admin, grumpy])
