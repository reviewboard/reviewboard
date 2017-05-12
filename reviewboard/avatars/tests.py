from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.core.files.storage import get_storage_class
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import RequestContext, Template
from django.test.client import RequestFactory
from django.utils.html import escape
from djblets.avatars.services import (GravatarService,
                                      URLAvatarService)
from djblets.avatars.tests import DummyAvatarService, DummyHighDPIAvatarService
from djblets.siteconfig.models import SiteConfiguration
from kgb import SpyAgency

from reviewboard.accounts.forms.pages import AvatarSettingsForm
from reviewboard.accounts.models import Profile
from reviewboard.avatars import avatar_services
from reviewboard.avatars.registry import AvatarServiceRegistry
from reviewboard.avatars.services import FileUploadService
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

        self.assertSetEqual(
            set(registry),
            {
                FileUploadService,
                GravatarService,
                URLAvatarService,
            })

        self.assertIsInstance(registry.default_service, GravatarService)
        self.assertSetEqual(
            set(registry.enabled_services),
            {
                FileUploadService,
                GravatarService,
                URLAvatarService,
            })

        # Verify that the settings were saved correctly to the database.
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_MIGRATED_KEY))
        self.assertTrue(
            siteconfig.get(AvatarServiceRegistry.AVATARS_ENABLED_KEY))
        self.assertListEqual(
            siteconfig.get(AvatarServiceRegistry.ENABLED_SERVICES_KEY),
            [
                GravatarService.avatar_service_id,
                FileUploadService.avatar_service_id,
                URLAvatarService.avatar_service_id,
            ])
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
        self.assertSetEqual(
            set(registry),
            {
                FileUploadService,
                GravatarService,
                URLAvatarService,
            })
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


class TemplateTagTests(AvatarServicesTestMixin, TestCase):
    """Tests for reviewboard.avatars.templatetags."""

    fixtures = ['test_users']

    def setUp(self):
        super(TemplateTagTests, self).setUp()

        avatar_services.enable_service(GravatarService, save=False)
        avatar_services.set_default_service(GravatarService, save=False)

        self.user = User.objects.get(username='doc')
        self.request = RequestFactory().get('/')
        self.request.user = AnonymousUser()

    def test_avatar_urls(self):
        """Testing {% avatar_urls %} template tag"""
        service = avatar_services.default_service
        self.assertIsNotNone(service)

        t = Template(
            '{% load avatars %}'
            '{% avatar_urls u 32 %}'
        )

        self.assertEqual(
            t.render(RequestContext(self.request, {
                'u': self.user,
                'service_id': service.avatar_service_id,
            })),
            ('{'
             '"1x": "%(1x)s", '
             '"3x": "%(3x)s", '
             '"2x": "%(2x)s"'
             '}'
             % service.get_avatar_urls_uncached(self.user, 32))
        )

    def test_avatar_urls_with_service(self):
        """Testing {% avatar_urls %} template tag with avatar_service_id"""
        avatar_services.register(DummyHighDPIAvatarService)
        avatar_services.enable_service(DummyHighDPIAvatarService)

        service = avatar_services.get_avatar_service(
            DummyHighDPIAvatarService.avatar_service_id)

        t = Template(
            '{% load avatars %}'
            '{% avatar_urls u 32 service_id %}'
        )

        self.assertEqual(
            t.render(RequestContext(self.request, {
                'u': self.user,
                'service_id': DummyHighDPIAvatarService.avatar_service_id,
            })),
            ('{'
             '"1x": "%(1x)s", '
             '"2x": "%(2x)s"'
             '}'
             % service.get_avatar_urls_uncached(self.user, 32))
        )

    def test_avatar_urls_no_service(self):
        """Testing {% avatar_urls %} template tag with no available services"""
        services = list(avatar_services)

        for service in services:
            avatar_services.unregister(service)

        t = Template(
            '{% load avatars %}'
            '{% avatar_urls u 32 %}'
        )

        self.assertEqual(
            t.render(RequestContext(self.request, {
                'u': self.user,
            })),
            '{}')

    def test_avatar_urls_service_not_found(self):
        """Testing {% avatar_urls %} template tag with an invalid service"""
        service = avatar_services.default_service

        self.assertIsNotNone(service)
        self.assertIsNone(avatar_services.get_avatar_service(
            DummyAvatarService.avatar_service_id))

        t = Template(
            '{% load avatars %}'
            '{% avatar_urls u 32 service_id %}'
        )

        self.assertEqual(
            t.render(RequestContext(self.request, {
                'u': self.user,
                'service_id': DummyAvatarService.avatar_service_id,
            })),
            ('{'
             '"1x": "%(1x)s", '
             '"3x": "%(3x)s", '
             '"2x": "%(2x)s"'
             '}'
             % service.get_avatar_urls_uncached(self.user, 32))
        )

    def test_avatar_default_service(self):
        """Testing {% avatar %} template tag with the default avatar service"""
        default_avatar_template = Template('{% load avatars %}'
                                           '{% avatar target_user 32 %}')
        service_template = Template(
            '{% load avatars %}'
            '{% avatar target_user 32 avatar_service_id %}')

        self.assertIsNotNone(avatar_services.default_service)

        self.assertHTMLEqual(
            default_avatar_template.render(RequestContext(self.request, {
                'target_user': self.user,
            })),
            service_template.render(RequestContext(self.request, {
                'target_user': self.user,
                'avatar_service_id': GravatarService.avatar_service_id,
            })))

    def test_avatar_specific_service(self):
        """Testing {% avatar %} template tag using a specific avatar service"""

        avatar_services.register(DummyAvatarService)
        avatar_services.enable_service(DummyAvatarService)

        t = Template('{% load avatars %}'
                     '{% avatar target_user 32 avatar_service_id %}')

        self.assertHTMLEqual(
            t.render(RequestContext(self.request, {
                'target_user': self.user,
                'avatar_service_id': DummyAvatarService.avatar_service_id,

            })),
            ('<img src="http://example.com/avatar.png" alt="%s" width="32"'
             ' height="32" srcset="http://example.com/avatar.png 1x"'
             ' class="avatar">\n'
             % self.user.get_full_name() or self.user.username)
        )

    def test_avatar_invalid_service(self):
        """Test {% avatar %} template tag rendering with an invalid avatar
        service
        """
        t = Template('{% load avatars %}'
                     '{% avatar target_user 32 avatar_service_id %}')

        self.assertEqual(
            t.render(RequestContext(self.request, {
                'target_user': self.user,
                'avatar_service_id': 'INVALID_ID',
            })),
            t.render(RequestContext(self.request, {
                'target_user': self.user,
                'avatar_service_id': None,
            })))

    def test_username_unsafe(self):
        """Testing avatar template tag rendering with an unsafe username"""
        t = Template('{% load avatars %}'
                     '{% avatar target_user 32 avatar_service_id %}')

        user = User.objects.create(
            first_name='<b>Bad',
            last_name='User</b>',
            username='bad_user')

        Profile.objects.create(user=user)

        escaped_user = escape(user.get_full_name())

        avatar_services.register(DummyAvatarService)
        avatar_services.enable_service(DummyAvatarService)

        self.assertHTMLEqual(
            t.render(RequestContext(self.request, {
                'target_user': user,
                'avatar_service_id': DummyAvatarService.avatar_service_id,
            })),
            '<img src="http://example.com/avatar.png" alt="%s" width="32"'
            ' height="32" srcset="http://example.com/avatar.png 1x"'
            ' class="avatar">\n'
            % escaped_user)


class FileUploadServiceTests(SpyAgency, AvatarServicesTestMixin, TestCase):
    fixtures = ['test_users']

    @classmethod
    def setUpClass(cls):
        super(FileUploadServiceTests, cls).setUpClass()

        cls.request_factory = RequestFactory()

    def test_absolute_urls(self):
        """Testing FileUploadService.get_avatar_urls_uncached returns absolute
        URLs
        """
        user = User.objects.get(username='doc')
        avatar = SimpleUploadedFile('filename.png', content=b' ',
                                    content_type='image/png')

        service = avatar_services.get_avatar_service(
            FileUploadService.avatar_service_id)
        storage_cls = get_storage_class()

        self.spy_on(storage_cls.save,
                    call_fake=lambda self, filename, data: filename)

        form = AvatarSettingsForm(
            None,
            self.request_factory.post('/'),
            user,
            data={
                'avatar_service_id': FileUploadService.avatar_service_id,
            })

        service_form = \
            form.avatar_service_forms[FileUploadService.avatar_service_id]

        form.files = service_form.files = {
            service_form.add_prefix('avatar_upload'): avatar,
        }

        self.assertTrue(form.is_valid())
        form.save()

        file_path = storage_cls.save.spy.last_call.args[0]

        self.assertEqual(service.get_avatar_urls_uncached(user, None),
                         {'1x': 'http://example.com/media/%s' % file_path})
