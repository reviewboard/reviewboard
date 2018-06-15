"""Unit tests for ActiveDirectoryBackend."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from reviewboard.accounts.backends import ActiveDirectoryBackend
from reviewboard.testing import TestCase


class ActiveDirectoryBackendTests(TestCase):
    """Unit tests for ActiveDirectoryBackend."""

    def test_get_or_create_user_without_ad_user_data_and_with_user(self):
        """Testing ActiveDirectoryBackend.get_or_create_user without
        ad_user_data and with user in database
        """
        backend = ActiveDirectoryBackend()
        user = User.objects.create(username='test')

        self.assertEqual(backend.get_or_create_user('test', None),
                         user)

    def test_get_or_create_user_without_ad_user_data_and_without_user(self):
        """Testing ActiveDirectoryBackend.get_or_create_user without
        ad_user_data and with user not in database
        """
        backend = ActiveDirectoryBackend()

        self.assertIsNone(backend.get_or_create_user('test', None))
