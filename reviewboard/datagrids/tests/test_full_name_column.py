"""Unit tests for reviewboard.datagrids.columns.FullNameColumn.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser, User
from django.utils.safestring import SafeString
from djblets.testing.decorators import add_fixtures

from reviewboard.datagrids.columns import FullNameColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase
from reviewboard.site.models import LocalSite


class FullNameColumnTests(BaseColumnTestCase):
    """Testing reviewboard.datagrids.columns.FullNameColumn."""

    column = FullNameColumn()

    def test_render_anonymous(self):
        """Testing FullNameColumn.render_data when the viewing user is
        anonymous
        """
        user = User.objects.get(username='grumpy')
        self.request.user = AnonymousUser()

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    def test_render_public(self):
        """Testing FullNameColumn.render_data for a user with a public
        profile
        """
        user = User.objects.get(username='grumpy')

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            user.get_full_name())

    def test_render_private(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    def test_render_private_admin(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by an admin
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.request.user = User.objects.get(username='admin')

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_render_private_localsite(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by a fellow LocalSite member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.get(name='local-site-1')
        site.users.add(user)

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    @add_fixtures(['test_site'])
    def test_render_private_localsite_admin(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by a LocalSite admin
        """
        user = User.objects.get(username='admin')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_render_private_localsite_admin_other_site(self):
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by an admin of a LocalSite of which they are not a
        member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.create(name='local-site-3')
        site.users.add(user)
        site.users.add(self.request.user)

        self.assertEqual(
            self.column.render_data(self.stateful_column, user),
            '')

    def test_render_data_escapes_name(self):
        """Testing FullNameColumn.render_data escapes the full name"""
        user = User.objects.get(username='grumpy')
        user.first_name = '<script>alert("unsafe")</script>'
        user.last_name = '""'
        user.save(update_fields=('first_name', 'last_name'))

        rendered = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(rendered, SafeString)
        self.assertEqual(rendered,
                         '&lt;script&gt;alert(&quot;unsafe&quot;)'
                         '&lt;/script&gt; &quot;&quot;')
