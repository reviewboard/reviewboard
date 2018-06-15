"""Unit tests for reviewboard.accounts.views.UserInfoboxView."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class UserInfoboxViewTests(TestCase):
    """Unit tests for reviewboard.accounts.views.UserInfoboxView."""

    def test_unicode(self):
        """Testing UserInfoboxView with a user with non-ascii characters"""
        user = User.objects.create_user('test', 'test@example.com')
        user.first_name = 'Test\u21b9'
        user.last_name = 'User\u2729'
        user.save()

        self.client.get(local_site_reverse('user-infobox', args=['test']))
