from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.template import Context, Template
from django.utils.html import escape
from djblets.avatars.services.gravatar import GravatarService
from djblets.avatars.tests import DummyAvatarService
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.avatars import avatar_services
from reviewboard.avatars.registry import AvatarServiceRegistry
from reviewboard.testing.testcase import TestCase


class AvatarServiceRegistryTests(TestCase):
    """Tests for reviewboard.avatars."""

    @classmethod
    def setUpClass(cls):
        siteconfig = SiteConfiguration.objects.get_current()
        cls._original_settings = siteconfig.settings.copy()

    @classmethod
    def tearDownClass(cls):
        super(AvatarServiceRegistryTests, cls).tearDownClass()
        cls._reset_siteconfig()

    def setUp(self):
        super(AvatarServiceRegistryTests, self).setUp()
        self._reset_siteconfig()

    @classmethod
    def _reset_siteconfig(cls):
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.settings = cls._original_settings.copy()
        siteconfig.save(update_fields=('settings',))

    def test_migrate_enabled(self):
        """Testing AvatarServiceRegistry migrates avatar settings for enabled
        gravatars
        """
        # Verify the pre-conditions.
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertFalse(
            siteconfig.get(AvatarServiceRegistry.AVATARS_MIGRATED_KEY))
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_ENABLED_KEY))
        self.assertListEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])

        registry = AvatarServiceRegistry()

        # Verify that the Gravatar service is the only service and it is
        # enabled and default.
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)
        self.assertIsNotNone(gravatar_service)
        self.assertIs(type(gravatar_service), GravatarService)
        self.assertSetEqual(set(registry), set([gravatar_service]))

        self.assertIs(registry.default_service, gravatar_service)
        self.assertSetEqual(set(registry.enabled_services),
                            {gravatar_service})

        # Verify that the settings were saved correctly to the database.
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_MIGRATED_KEY))
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_ENABLED_KEY))
        self.assertListEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [GravatarService.avatar_service_id])
        self.assertEqual(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY),
            GravatarService.avatar_service_id)

    def test_migrate_disabled(self):
        """Testing AvatarServiceRegistry migrates avatar settings for disabled
        gravatars
        """
        # Verify the pre-conditions.
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertFalse(
            siteconfig.get(AvatarServiceRegistry.AVATARS_MIGRATED_KEY))
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_ENABLED_KEY))

        siteconfig.set('integration_gravatars', False)
        siteconfig.save()

        registry = AvatarServiceRegistry()

        # Verify the GravatarService is the only service and that is disabled.
        gravatar_service = registry.get('avatar_service_id',
                                        GravatarService.avatar_service_id)
        self.assertIsNotNone(gravatar_service)
        self.assertIs(type(gravatar_service), GravatarService)
        self.assertSetEqual(set(registry), set([gravatar_service]))

        self.assertIsNone(registry.default_service)
        self.assertSetEqual(set(registry.enabled_services), set())

        # Verify the settings were correctly saved to the database.
        siteconfig = SiteConfiguration.objects.get_current()
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_MIGRATED_KEY))
        self.assertFalse(
            siteconfig.get(AvatarServiceRegistry.AVATARS_ENABLED_KEY))
        self.assertListEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [])
        self.assertIsNone(
            siteconfig.get(AvatarServiceRegistry.DEFAULT_SERVICE_KEY))


class TemplateTagTests(TestCase):
    """Tests for reviewboard.accounts.templatetags.avatars."""

    fixtures = ['test_users']

    def setUp(self):
        super(TemplateTagTests, self).setUp()
        self.request = HttpRequest()
        self.user = User.objects.get(username='doc')

    def tearDown(self):
        avatar_services.reset()

    def test_default_avatar_service(self):
        """Test avatar template tag rendering the default avatar service"""
        default_avatar_template = Template('{% load avatars %}'
                                           '{% avatar user 32 %}')
        gravatar_template = Template('{% load avatars %}'
                                     '{% avatar user 32 avatar_service_id %}')

        self.assertIsNotNone(avatar_services.default_service)

        default_service = avatar_services.default_service

        self.assertEqual(
            default_avatar_template.render(Context({
                'user': self.user,
                'request': self.request,
            })),
            gravatar_template.render(Context({
                'user': self.user,
                'avatar_service_id': default_service.avatar_service_id,
                'request': self.request,
            })))

    def test_custom_avatar_service(self):
        """Test avatar template tag rendering a specific avatar service"""
        avatar_services.register(DummyAvatarService())
        avatar_services.enable_service(DummyAvatarService.avatar_service_id)

        t = Template('{% load avatars %}'
                     '{% avatar user 32 avatar_service_id %}')

        self.assertEqual(
            t.render(Context({
                'user': self.user,
                'avatar_service_id': DummyAvatarService.avatar_service_id,
                'request': self.request,
            })),
            '<img src="http://example.com/avatar.png" alt="%s" width="32"'
            ' height="32" srcset="http://example.com/avatar.png 1x"'
            ' class="avatar">\n'
            % self.user.get_full_name() or self.user.username
        )

    def test_no_avatar_service(self):
        """Test avatar template tag rendering with invalid avatar service"""
        t = Template('{% load avatars %}'
                     '{% avatar user 32 avatar_service_id %}')

        self.assertEqual(
            t.render(Context({
                'user': self.user,
                'avatar_service_id': 'INVALID_ID',
                'request': self.request,
            })),
            t.render(Context({
                'user': self.user,
                'avatar_service_id': None,
                'request': self.request,
            })))

    def test_username_unsafe(self):
        """Testing avatar template tag rendering with an unsafe username"""
        t = Template('{% load avatars %}'
                     '{% avatar user 32 avatar_service_id %}')

        user = User(first_name='<b>Bad',
                    last_name='User</b>',
                    username='bad_user')

        escaped_user = escape(user.get_full_name())

        avatar_services.register(DummyAvatarService())
        avatar_services.enable_service(DummyAvatarService.avatar_service_id)

        self.assertEqual(
            t.render(Context({
                'user': user,
                'request': self.request,
                'avatar_service_id': DummyAvatarService.avatar_service_id,
            })),
            '<img src="http://example.com/avatar.png" alt="%s" width="32"'
            ' height="32" srcset="http://example.com/avatar.png 1x"'
            ' class="avatar">\n'
            % escaped_user)
