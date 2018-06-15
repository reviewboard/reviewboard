"""Unit tests for AuthBackendRegistry."""

from __future__ import unicode_literals

from reviewboard.accounts.backends import (AuthBackend,
                                           auth_backends,
                                           register_auth_backend,
                                           unregister_auth_backend)
from reviewboard.testing import TestCase


class DummyAuthBackend(AuthBackend):
    backend_id = 'dummy'


class AuthBackendRegistryTests(TestCase):
    """Unit tests for AuthBackendRegistry."""

    @classmethod
    def setUpClass(cls):
        super(AuthBackendRegistryTests, cls).setUpClass()

        auth_backends.reset()

    def tearDown(self):
        super(AuthBackendRegistryTests, self).tearDown()

        auth_backends.reset()

    def test_register_auth_backend(self):
        """Testing register_auth_backend"""
        starting_set = set(auth_backends)
        register_auth_backend(DummyAuthBackend)

        self.assertSetEqual(set(auth_backends),
                            starting_set | {DummyAuthBackend})

    def test_unregister_auth_backend(self):
        """Testing unregister_auth_backend"""
        starting_set = set(auth_backends)
        register_auth_backend(DummyAuthBackend)
        unregister_auth_backend(DummyAuthBackend)
        self.assertSetEqual(set(auth_backends), starting_set)
