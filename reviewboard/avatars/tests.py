from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.template import Context, Template
from django.utils.html import escape
from djblets.avatars.services.file_upload import FileUploadService
from djblets.avatars.services.gravatar import GravatarService
from djblets.avatars.tests import DummyAvatarService
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.models import Profile
from reviewboard.avatars import avatar_services
from reviewboard.avatars.registry import AvatarServiceRegistry
from reviewboard.avatars.testcase import AvatarServicesTestMixin
from reviewboard.testing.testcase import TestCase


class AvatarServiceRegistryTests(AvatarServicesTestMixin, TestCase):
    """Tests for reviewboard.avatars."""

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

        self.assertqual(set(registry),
                        {FileUploadService, GravatarService})

        self.assertIs(registry.default_service, GravatarService)
        self.assertSetEqual(set(registry.enabled_services),
                            {FileUploadService, GravatarService})

        # Verify that the settings were saved correctly to the database.
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_MIGRATED_KEY))
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_ENABLED_KEY))
        self.assertListEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [GravatarService.avatar_service_id,
             FileUploadService.avatar_service_id])
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

        # Verify all services are disabled.
        self.assertSetEqual(set(registry),
                            {FileUploadService, GravatarService})
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

        self.assertHTMLEqual(
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
        avatar_services.register(DummyAvatarService)
        avatar_services.enable_service(DummyAvatarService)

        t = Template('{% load avatars %}'
                     '{% avatar user 32 avatar_service_id %}')

        self.assertHTMLEqual(
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

        user = User.objects.create(
            first_name='<b>Bad',
            last_name='User</b>',
            username='bad_user')

        Profile.objects.create(user=user)

        escaped_user = escape(user.get_full_name())

        avatar_services.register(DummyAvatarService)
        avatar_services.enable_service(DummyAvatarService)

        self.assertHTMLEqual(
            t.render(Context({
                'user': user,
                'request': self.request,
                'avatar_service_id': DummyAvatarService.avatar_service_id,
            })),
            '<img src="http://example.com/avatar.png" alt="%s" width="32"'
            ' height="32" srcset="http://example.com/avatar.png 1x"'
            ' class="avatar">\n'
            % escaped_user)
