"""Unit tests for NISBackend."""

from unittest import SkipTest

import kgb
from django.contrib.auth.models import User

from reviewboard.accounts.backends import NISBackend
from reviewboard.testing import TestCase


class NISBackendTests(kgb.SpyAgency, TestCase):
    """Unit tests for NISBackend."""

    NIS_SITECONFIG_SETTINGS = {
        'auth_nis_email_domain': 'example.com',
    }

    def setUp(self):
        super(NISBackendTests, self).setUp()

        self.backend = NISBackend()

        if self.backend.nis is None:
            raise SkipTest('nis is not available on this build of Python.')

    def test_authenticate_with_valid_user(self):
        """Testing NISBackend.authenticate with valid user credentials"""
        self.spy_on(self.backend._nis_get_passwd, lambda _self, username: (
            'test-user', '6a6Sl/u3EOBfo', 100, 100, 'Test User,Foo Bar',
            '/home/test-user', '/bin/sh'))

        with self.siteconfig_settings(self.NIS_SITECONFIG_SETTINGS):
            user = self.backend.authenticate(request=None,
                                             username='test-user',
                                             password='test-pass')

        # Use a plain assert to help the type checker.
        assert user is not None

        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'test-user@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertSpyCalledWith(self.backend._nis_get_passwd, 'test-user')

    def test_authenticate_with_invalid_credentials(self):
        """Testing NISBackend.authenticate with bad user credentials"""

        self.spy_on(self.backend._nis_get_passwd, lambda _self, username: (
            'test-user', 'foo', 100, 100, 'Test User',
            '/home/test-user', '/bin/sh'))

        user = self.backend.authenticate(request=None,
                                         username='test-user',
                                         password='test-pass')
        self.assertIsNone(user)

    def test_authenticate_with_invalid_user(self):
        """Testing NISBackend.authenticate with bad user credentials"""
        backend = self.backend

        self.spy_on(backend._nis_get_passwd,
                    op=kgb.SpyOpRaise(backend.nis.error()))

        user = backend.authenticate(request=None,
                                    username='test-user',
                                    password='test-pass')
        self.assertIsNone(user)

    def test_get_or_create_user_with_user_in_db(self):
        """Testing NISBackend.get_or_create_user with user in database"""
        user = User.objects.create(username='test-user')

        self.assertEqual(
            self.backend.get_or_create_user(username='test-user'),
            user)

    def test_get_or_create_user_with_user_in_nis(self):
        """Testing NISBackend.get_or_create_user with user in NIS"""
        self.spy_on(self.backend._nis_get_passwd, lambda _self, username: (
            'test-user', '6a6Sl/u3EOBfo', 100, 100, 'Test User',
            '/home/test-user', '/bin/sh'))

        user = User.objects.create(username='test-user')

        self.assertEqual(
            self.backend.get_or_create_user(username='test-user'),
            user)

    def test_get_or_create_user_with_user_and_passwd(self):
        """Testing NISBackend.get_or_create_user with explicit passwd value"""
        self.spy_on(self.backend._nis_get_passwd, lambda _self, username: None)

        with self.siteconfig_settings(self.NIS_SITECONFIG_SETTINGS):
            user = self.backend.get_or_create_user(
                username='test-user',
                passwd=('test-user', '6a6Sl/u3EOBfo', 100, 100,
                        'Test User,Foo Bar', '/home/test-user', '/bin/sh'))

        # Use a plain assert to help the type checker.
        assert user is not None

        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'test-user@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertSpyNotCalled(self.backend._nis_get_passwd)
