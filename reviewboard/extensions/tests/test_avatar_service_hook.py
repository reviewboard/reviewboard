"""Unit tests for reviewboard.extensions.hooks.AvatarServiceHook."""

from __future__ import unicode_literals

from djblets.avatars.tests import DummyAvatarService

from reviewboard.avatars import avatar_services
from reviewboard.extensions.hooks import AvatarServiceHook
from reviewboard.extensions.tests.testcases import (DummyExtension,
                                                    ExtensionManagerMixin)
from reviewboard.testing.testcase import TestCase


class AvatarServiceHookTests(ExtensionManagerMixin, TestCase):
    """Test for reviewboard.extensions.hooks.AvatarServiceHook."""

    @classmethod
    def setUpClass(cls):
        super(AvatarServiceHookTests, cls).setUpClass()
        avatar_services.reset()

    def setUp(self):
        super(AvatarServiceHookTests, self).setUp()
        self.extension = DummyExtension(extension_manager=self.manager)

    def tearDown(self):
        super(AvatarServiceHookTests, self).tearDown()
        self.extension.shutdown()
        avatar_services.reset()

    def test_register(self):
        """Testing AvatarServiceHook registers services"""
        self.assertNotIn(DummyAvatarService, avatar_services)
        AvatarServiceHook(self.extension, DummyAvatarService,
                          start_enabled=True)
        self.assertIn(DummyAvatarService, avatar_services)

        avatar_services.enable_service(DummyAvatarService, save=False)
        self.assertTrue(avatar_services.is_enabled(DummyAvatarService))

    def test_unregister(self):
        """Testing AvatarServiceHook unregisters services on shutdown"""
        self.assertNotIn(DummyAvatarService, avatar_services)
        AvatarServiceHook(self.extension, DummyAvatarService,
                          start_enabled=True)
        self.assertIn(DummyAvatarService, avatar_services)

        self.extension.shutdown()
        self.assertNotIn(DummyAvatarService, avatar_services)

