"""Unit tests for StandardAuthBackend."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.backends import (StandardAuthBackend,
                                           get_enabled_auth_backends)
from reviewboard.testing import TestCase


class StandardAuthBackendTests(TestCase):
    """Unit tests for StandardAuthBackend."""

    def _get_standard_auth_backend(self):
        backend = None

        for backend in get_enabled_auth_backends():
            # We do not use isinstance here because we specifically want a
            # StandardAuthBackend and not an instance of a subclass of it.
            if type(backend) is StandardAuthBackend:
                break

        self.assertIs(type(backend), StandardAuthBackend)

        return backend

    @add_fixtures(['test_users'])
    def test_get_or_create_user_exists(self):
        """Testing StandardAuthBackend.get_or_create_user when the requested
        user already exists
        """
        original_count = User.objects.count()

        user = User.objects.get(username='doc')
        backend = self._get_standard_auth_backend()
        result = backend.get_or_create_user('doc', None)

        self.assertEqual(original_count, User.objects.count())
        self.assertEqual(user, result)

    def test_get_or_create_user_new(self):
        """Testing StandardAuthBackend.get_or_create_user when the requested
        user does not exist
        """
        backend = self._get_standard_auth_backend()
        self.assertIsInstance(backend, StandardAuthBackend)
        user = backend.get_or_create_user('doc', None)

        self.assertIsNone(user)

    @add_fixtures(['test_users'])
    def test_get_user_exists(self):
        """Testing StandardAuthBackend.get_user when the requested user already
        exists
        """
        user = User.objects.get(username='doc')
        backend = self._get_standard_auth_backend()
        result = backend.get_user(user.pk)

        self.assertEqual(user, result)

    def test_get_user_not_exists(self):
        """Testing StandardAuthBackend.get_user when the requested user does
        not exist
        """
        backend = self._get_standard_auth_backend()
        result = backend.get_user(1)

        self.assertIsNone(result)
