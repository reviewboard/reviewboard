from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.auth.signals import user_registered
from kgb import SpyAgency

from reviewboard.accounts.models import _add_default_groups
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class DefaultGroupTest(SpyAgency, TestCase):
    """Unit tests for default group memberships."""

    fixtures = ['test_users', 'test_site']

    def test_user_registration(self):
        """Testing default group computation on user_registered signal"""
        self.spy_on(_add_default_groups)

        user = User.objects.create_user(username='reviewboard',
                                        email='user@example.com',
                                        password='password')

        user_registered.send(sender=None, user=user)

        self.assertTrue(_add_default_groups.called)
        self.assertTrue(_add_default_groups.last_called_with(user=user,
                                                             local_site=None))

    def test_local_site_add_user(self):
        """Testing default group computation when adding user to LocalSite
        users list
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(pk=3)

        self.spy_on(_add_default_groups)

        local_site.users.add(user)

        self.assertTrue(_add_default_groups.called)
        self.assertTrue(_add_default_groups.last_called_with(
            user=user,
            local_site=local_site))

    def test_user_add_local_site(self):
        """Testing default group computation when adding LocalSite to user's
        LocalSite list
        """
        local_site = LocalSite.objects.create(name='test')
        user = User.objects.get(pk=3)

        self.spy_on(_add_default_groups)

        user.local_site.add(local_site)

        self.assertTrue(_add_default_groups.spy.called)
        self.assertTrue(_add_default_groups.spy.last_called_with(
            user=user,
            local_site=local_site))

    def test_add_default_groups(self):
        """Testing default group computation without LocalSite"""
        user = User.objects.get(pk=1)
        group_count_before = user.review_groups.count()

        _add_default_groups(sender=None, user=user)

        self.assertEqual(group_count_before,
                         User.objects.get(pk=user.id).review_groups.count())

        self.create_review_group(is_default_group=True)

        _add_default_groups(sender=None, user=user)

        self.assertEqual(group_count_before + 1,
                         User.objects.get(pk=user.id).review_groups.count())

    def test_add_default_groups_with_local_site(self):
        """Testing default group computation with LocalSite"""
        user = User.objects.get(pk=3)
        local_site = LocalSite.objects.create(name='test')
        self.create_review_group(is_default_group=True, local_site=local_site)

        group_count_before = user.review_groups.count()

        _add_default_groups(sender=None, user=user, local_site=local_site)

        self.assertEqual(group_count_before + 1,
                         User.objects.get(pk=user.id).review_groups.count())
