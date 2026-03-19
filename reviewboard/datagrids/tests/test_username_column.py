"""Unit tests for reviewboard.datagrids.columns.UsernameColumn.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.utils.safestring import SafeString
from djblets.testing.decorators import add_fixtures

from reviewboard.datagrids.columns import UsernameColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class UsernameColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.UsernameColumn."""

    column = UsernameColumn()

    @add_fixtures(['test_site'])
    def test_render(self):
        """Testing UsernameColumn.render_cell"""
        user = User.objects.get(username='doc')
        self.assertIn(
            'href="/users/doc/"',
            self.column.render_cell(self.stateful_column, user, None))

    @add_fixtures(['test_site'])
    def test_render_local_site(self):
        """Testing UsernameColumn.render_cell on a LocalSite"""
        self.request._local_site_name = self.local_site_name
        user = User.objects.get(username='doc')

        self.assertIn(
            'href="/s/%s/users/doc/"' % self.local_site_name,
            self.column.render_cell(self.stateful_column, user, None))

    def test_render_data(self) -> None:
        """Testing UsernameColumn.render_data"""
        user = User.objects.get(username='doc')

        # The output includes the username along with avatar HTML. We verify
        # the username appears correctly; the full avatar HTML is dynamic.
        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertIn('doc', value)

    def test_to_json(self) -> None:
        """Testing UsernameColumn.to_json"""
        user = User.objects.get(username='doc')

        # UsernameColumn uses db_field (not field_name), so the default
        # Column.to_json() via get_raw_object_value() returns None.
        self.assertIsNone(self.column.to_json(self.stateful_column, user))
