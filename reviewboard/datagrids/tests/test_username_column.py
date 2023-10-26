"""Unit tests for reviewboard.datagrids.columns.UsernameColumn.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.datagrids.columns import UsernameColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase


class UsernameColumnTests(BaseColumnTestCase):
    """Tests for reviewboard.datagrids.columns.UsernameColumn."""

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
