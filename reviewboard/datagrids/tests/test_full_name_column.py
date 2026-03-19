"""Unit tests for reviewboard.datagrids.columns.FullNameColumn.

Version Added:
    5.0.7
"""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.utils.safestring import SafeString
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import User
from reviewboard.datagrids.columns import FullNameColumn
from reviewboard.datagrids.tests.base import BaseColumnTestCase
from reviewboard.site.models import LocalSite


class FullNameColumnTests(BaseColumnTestCase):
    """Unit tests for reviewboard.datagrids.columns.FullNameColumn."""

    column = FullNameColumn()

    def test_render_data_as_anonymous(self) -> None:
        """Testing FullNameColumn.render_data when the viewing user is
        anonymous
        """
        user = User.objects.get(username='grumpy')
        self.request.user = AnonymousUser()

        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_public_profile(self) -> None:
        """Testing FullNameColumn.render_data for a user with a public
        profile
        """
        user = User.objects.get(username='grumpy')

        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, user.get_full_name())

    def test_render_data_with_private_profile(self) -> None:
        """Testing FullNameColumn.render_data for a user with a private
        profile
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_with_private_profile_as_admin(self) -> None:
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by an admin
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.request.user = User.objects.get(username='admin')

        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, user.get_full_name())

    @add_fixtures(['test_site'])
    def test_render_data_with_private_profile_and_localsite(self) -> None:
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by a fellow LocalSite member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.get(name='local-site-1')
        site.users.add(user)

        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    @add_fixtures(['test_site'])
    def test_render_data_with_private_profile_as_localsite_admin(self) -> None:
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by a LocalSite admin
        """
        user = User.objects.get(username='admin')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, user.get_full_name())

    @add_fixtures(['test_site'])
    def test_render_data_with_private_profile_localsite_admin_other_site(
        self,
    ) -> None:
        """Testing FullNameColumn.render_data for a user with a private
        profile viewed by an admin of a LocalSite of which they are not a
        member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.create(name='local-site-3')
        site.users.add(user, self.request.user)

        value = self.column.render_data(self.stateful_column, user)

        self.assertIsInstance(value, SafeString)
        self.assertEqual(value, '')

    def test_render_data_escapes_name(self) -> None:
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

    def test_to_json_as_anonymous(self) -> None:
        """Testing FullNameColumn.to_json when the viewing user is anonymous"""
        user = User.objects.get(username='grumpy')
        self.request.user = AnonymousUser()

        self.assertIsNone(self.column.to_json(self.stateful_column, user))

    def test_to_json_with_public_profile(self) -> None:
        """Testing FullNameColumn.render_data for a user with a public
        profile
        """
        user = User.objects.get(username='grumpy')

        self.assertEqual(
            self.column.to_json(self.stateful_column, user),
            user.get_full_name())

    def test_to_json_with_private_profile(self) -> None:
        """Testing FullNameColumn.to_json for a user with a private profile"""
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertIsNone(self.column.to_json(self.stateful_column, user))

    def test_to_json_with_private_profile_as_admin(self) -> None:
        """Testing FullNameColumn.to_json for a user with a private profile
        viewed by an admin
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.request.user = User.objects.get(username='admin')

        self.assertEqual(
            self.column.to_json(self.stateful_column, user),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_to_json_with_private_profile_and_localsite(self) -> None:
        """Testing FullNameColumn.to_json for a user with a private
        profile viewed by a fellow LocalSite member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.get(name='local-site-1')
        site.users.add(user)

        self.assertIsNone(self.column.to_json(self.stateful_column, user))

    @add_fixtures(['test_site'])
    def test_to_json_with_private_profile_as_localsite_admin(self) -> None:
        """Testing FullNameColumn.to_json for a user with a private
        profile viewed by a LocalSite admin
        """
        user = User.objects.get(username='admin')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        self.assertEqual(
            self.column.to_json(self.stateful_column, user),
            user.get_full_name())

    @add_fixtures(['test_site'])
    def test_to_json_with_private_profile_localsite_admin_other_site(
        self,
    ) -> None:
        """Testing FullNameColumn.to_json for a user with a private
        profile viewed by an admin of a LocalSite of which they are not a
        member
        """
        user = User.objects.get(username='grumpy')

        profile = user.get_profile()
        profile.is_private = True
        profile.save(update_fields=('is_private',))

        site = LocalSite.objects.create(name='local-site-3')
        site.users.add(user, self.request.user)

        self.assertIsNone(self.column.to_json(self.stateful_column, user))

    def test_to_json_does_not_escape_name(self) -> None:
        """Testing FullNameColumn.to_json does not escape the full name"""
        user = User.objects.get(username='grumpy')
        user.first_name = '<script>alert("unsafe")</script>'
        user.last_name = '""'
        user.save(update_fields=('first_name', 'last_name'))

        result = self.column.to_json(self.stateful_column, user)

        self.assertEqual(result, '<script>alert("unsafe")</script> ""')
