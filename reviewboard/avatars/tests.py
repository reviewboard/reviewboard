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


# This just helps keep things less wordy, and to define some settings
# we no longer have constants for elsewhere.
AVATARS_ENABLED_KEY = AvatarServiceRegistry.AVATARS_ENABLED_KEY
DEFAULT_SERVICE_KEY = AvatarServiceRegistry.DEFAULT_SERVICE_KEY
ENABLED_SERVICES_KEY = AvatarServiceRegistry.ENABLED_SERVICES_KEY
LEGACY_AVATARS_MIGRATED_KEY = AvatarServiceRegistry.LEGACY_AVATARS_MIGRATED_KEY
LEGACY_INTEGRATION_GRAVATARS_KEY = \
    AvatarServiceRegistry.LEGACY_INTEGRATION_GRAVATARS_KEY


class AvatarServiceRegistryTests(AvatarServicesTestMixin, TestCase):
    """Tests for reviewboard.avatars."""

    _enabled_service_ids = [
        GravatarService.avatar_service_id,
        FileUploadService.avatar_service_id,
        URLAvatarService.avatar_service_id,
    ]

    _default_service_id = GravatarService.avatar_service_id

    def setUp(self):
        super(AvatarServiceRegistryTests, self).setUp()

        self.registry = AvatarServiceRegistry()
        self.siteconfig = SiteConfiguration.objects.get_current()
        self._old_siteconfig_settings = self.siteconfig.settings.copy()

    def tearDown(self):
        super(AvatarServiceRegistryTests, self).tearDown()

        if self.siteconfig.settings != self._old_siteconfig_settings:
            self.siteconfig.settings = self._old_siteconfig_settings
            self.siteconfig.save()

    def test_defaults(self):
        """Testing AvatarServiceRegistry default services state"""
        self.assertEqual(
            set(self.registry),
            {
                FileUploadService,
                GravatarService,
                URLAvatarService,
            })

        self.assertIsInstance(self.registry.default_service, GravatarService)
        self.assertEqual(
            set(self.registry.enabled_services),
            {
                FileUploadService,
                GravatarService,
                URLAvatarService,
            })

    def test_get_siteconfig_defaults(self):
        """Testing AvatarServiceRegistry.get_siteconfig_defaults"""
        self.assertEqual(
            self.registry.get_siteconfig_defaults(),
            {
                AVATARS_ENABLED_KEY: True,
                ENABLED_SERVICES_KEY: self._enabled_service_ids,
                DEFAULT_SERVICE_KEY: self._default_service_id,
            })

    def test_migrate_settings_pre_2_0_with_enabled(self):
        """Testing AvatarServiceRegistry.migrate_settings migrates pre-2.0
        settings
        """
        siteconfig_settings = self.siteconfig.settings

        self.assertNotIn(AVATARS_ENABLED_KEY, siteconfig_settings)
        self.assertNotIn(DEFAULT_SERVICE_KEY, siteconfig_settings)
        self.assertNotIn(ENABLED_SERVICES_KEY, siteconfig_settings)
        self.assertNotIn(LEGACY_AVATARS_MIGRATED_KEY, siteconfig_settings)
        self.assertNotIn(LEGACY_INTEGRATION_GRAVATARS_KEY, siteconfig_settings)

        # Perform the migration.
        self._perform_migration(expect_has_enabled_saved=False,
                                expect_migrated=False)

    def test_migrate_settings_pre_3_0_with_enabled(self):
        """Testing AvatarServiceRegistry.migrate_settings migrates pre-3.0
        avatar settings for enabled Gravatars
        """
        siteconfig_settings = self.siteconfig.settings

        self.assertNotIn(AVATARS_ENABLED_KEY, siteconfig_settings)
        self.assertNotIn(DEFAULT_SERVICE_KEY, siteconfig_settings)
        self.assertNotIn(ENABLED_SERVICES_KEY, siteconfig_settings)
        self.assertNotIn(LEGACY_AVATARS_MIGRATED_KEY, siteconfig_settings)

        self.siteconfig.set(LEGACY_INTEGRATION_GRAVATARS_KEY, True)

        # Perform the migration.
        self._perform_migration(expect_has_enabled_saved=False)

    def test_migrate_pre_3_0_disabled(self):
        """Testing AvatarServiceRegistry migrates pre-3.0 avatar settings for
        disabled Gravatars
        """
        siteconfig_settings = self.siteconfig.settings

        self.assertNotIn(AVATARS_ENABLED_KEY, siteconfig_settings)
        self.assertNotIn(DEFAULT_SERVICE_KEY, siteconfig_settings)
        self.assertNotIn(ENABLED_SERVICES_KEY, siteconfig_settings)
        self.assertNotIn(LEGACY_AVATARS_MIGRATED_KEY, siteconfig_settings)

        self.siteconfig.set(LEGACY_INTEGRATION_GRAVATARS_KEY, False)

        # Perform the migration.
        self._perform_migration(expect_enabled=False)

    def test_migrate_3_0_pre_4_disabled(self):
        """Testing AvatarServiceRegistry migrates 3.0.[0-3] avatar settings for
        migrated disabled avatars
        """
        enabled_service_ids = [
            GravatarService.avatar_service_id,
            URLAvatarService.avatar_service_id,
        ]
        default_service_id = URLAvatarService.avatar_service_id

        self.siteconfig.set(AVATARS_ENABLED_KEY, False)
        self.siteconfig.set(DEFAULT_SERVICE_KEY, default_service_id)
        self.siteconfig.set(ENABLED_SERVICES_KEY, enabled_service_ids)
        self.siteconfig.set(LEGACY_AVATARS_MIGRATED_KEY, True)
        self.siteconfig.set(LEGACY_INTEGRATION_GRAVATARS_KEY, True)

        # Perform the migration.
        self._perform_migration(expect_enabled=False,
                                expected_enabled_services=enabled_service_ids,
                                expected_default_service=default_service_id,
                                expect_has_services_saved=True)

    def test_migrate_3_0_pre_4_enabled(self):
        """Testing AvatarServiceRegistry migrates 3.0.[0-3] avatar settings for
        migrated enabled avatars
        """
        enabled_service_ids = [
            GravatarService.avatar_service_id,
            URLAvatarService.avatar_service_id,
        ]
        default_service_id = URLAvatarService.avatar_service_id

        self.siteconfig.set(AVATARS_ENABLED_KEY, True)
        self.siteconfig.set(DEFAULT_SERVICE_KEY, default_service_id)
        self.siteconfig.set(ENABLED_SERVICES_KEY, enabled_service_ids)
        self.siteconfig.set(LEGACY_AVATARS_MIGRATED_KEY, True)
        self.siteconfig.set(LEGACY_INTEGRATION_GRAVATARS_KEY, True)

        # Perform the migration.
        self._perform_migration(expected_enabled_services=enabled_service_ids,
                                expected_default_service=default_service_id,
                                expect_has_services_saved=True)

    def test_migrate_already_migrated_enabled(self):
        """Testing AvatarServiceRegistry does not migrate already-migrated
        settings with enabled avatars
        """
        siteconfig_settings = self.siteconfig.settings

        self.assertNotIn(DEFAULT_SERVICE_KEY, siteconfig_settings)
        self.assertNotIn(ENABLED_SERVICES_KEY, siteconfig_settings)

        self.siteconfig.set(AVATARS_ENABLED_KEY, True)
        self.siteconfig.set(LEGACY_AVATARS_MIGRATED_KEY, True)
        self.siteconfig.set(LEGACY_INTEGRATION_GRAVATARS_KEY, True)

        # Perform the migration.
        self._perform_migration()

    def test_migrate_already_migrated_disabled(self):
        """Testing AvatarServiceRegistry does not migrate already-migrated
        settings with disabled avatars
        """
        siteconfig_settings = self.siteconfig.settings

        self.assertNotIn(DEFAULT_SERVICE_KEY, siteconfig_settings)
        self.assertNotIn(ENABLED_SERVICES_KEY, siteconfig_settings)

        self.siteconfig.set(AVATARS_ENABLED_KEY, True)
        self.siteconfig.set(LEGACY_AVATARS_MIGRATED_KEY, True)
        self.siteconfig.set(LEGACY_INTEGRATION_GRAVATARS_KEY, True)

        # Perform the migration.
        self._perform_migration()

    def test_migrate_with_fresh_install(self):
        """Testing AvatarServiceRegistry does not migrate fresh settings
        settings with disabled avatars
        """
        siteconfig_settings = self.siteconfig.settings

        self.assertNotIn(AVATARS_ENABLED_KEY, siteconfig_settings)
        self.assertNotIn(DEFAULT_SERVICE_KEY, siteconfig_settings)
        self.assertNotIn(ENABLED_SERVICES_KEY, siteconfig_settings)
        self.assertNotIn(LEGACY_AVATARS_MIGRATED_KEY, siteconfig_settings)
        self.assertNotIn(LEGACY_INTEGRATION_GRAVATARS_KEY, siteconfig_settings)

        # Perform the migration.
        self._perform_migration(expect_migrated=False,
                                expect_has_enabled_saved=False)

    def _perform_migration(self,
                           expect_migrated=True,
                           expect_enabled=True,
                           expected_enabled_services=_enabled_service_ids,
                           expected_default_service=_default_service_id,
                           expect_has_services_saved=False,
                           expect_has_enabled_saved=True):
        """Perform an avatar settings migration test.

        This will trigger a migration of the existing settings, checking the
        final results in the database based on the expectations of the caller.
        This helps to unify all of our various migration tests.

        Args:
            expect_migrated (bool, optional):
                Whether the migration attempt is expected to have made changes
                to the stored site configuration.

            expect_enabled (bool, optional):
                Whether avatars are expected to be enabled after the migration.

            expected_enabled_services (list, optional):
                The list of avatar service IDs that are expected to be enabled
                after the migration.

            expected_default_service (unicode, optional):
                The avatar service ID that is expected to be set as the
                default.

            expect_has_services_saved (bool, optional):
                Whether the site configuration is expected to have a list of
                service IDs explicitly saved.

            expect_has_enabled_saved (bool, optional):
                Whether the site configuration is expected to have the enabled
                state explicitly saved.
        """
        migrated = self.registry.migrate_settings(self.siteconfig)
        self.assertEqual(migrated, expect_migrated)

        if migrated:
            self.siteconfig.save()

        # Make sure the default avatar and available/enabled avatars are
        # still there.
        self.assertEqual(self.registry.default_service.avatar_service_id,
                         expected_default_service)
        self.assertEqual(
            set(self.registry),
            {
                FileUploadService,
                GravatarService,
                URLAvatarService,
            })
        self.assertEqual(
            {
                avatar_service.avatar_service_id
                for avatar_service in self.registry.enabled_services
            },
            set(expected_enabled_services))

        # Verify that the saved settings reflect the correct state. These
        # checks include the defaults:
        siteconfig = SiteConfiguration.objects.get(pk=self.siteconfig.pk)
        self.assertIs(siteconfig.get(AVATARS_ENABLED_KEY), expect_enabled)
        self.assertEqual(siteconfig.get(ENABLED_SERVICES_KEY),
                         expected_enabled_services)
        self.assertEqual(siteconfig.get(DEFAULT_SERVICE_KEY),
                         expected_default_service)
        self.assertIsNone(siteconfig.get(LEGACY_AVATARS_MIGRATED_KEY))
        self.assertIsNone(siteconfig.get(LEGACY_INTEGRATION_GRAVATARS_KEY))

        # These checks are for what's actually written to siteconfig.
        siteconfig_settings = siteconfig.settings
        self.assertNotIn(LEGACY_AVATARS_MIGRATED_KEY, siteconfig_settings)
        self.assertNotIn(LEGACY_INTEGRATION_GRAVATARS_KEY, siteconfig_settings)

        if expect_has_enabled_saved:
            self.assertIs(siteconfig_settings.get(AVATARS_ENABLED_KEY),
                          expect_enabled)
        else:
            self.assertNotIn(AVATARS_ENABLED_KEY, siteconfig_settings)

        if expect_has_services_saved:
            self.assertIn(ENABLED_SERVICES_KEY, siteconfig_settings)
            self.assertIn(DEFAULT_SERVICE_KEY, siteconfig_settings)
            self.assertEqual(siteconfig_settings[ENABLED_SERVICES_KEY],
                             expected_enabled_services)
            self.assertEqual(siteconfig_settings[DEFAULT_SERVICE_KEY],
                             expected_default_service)
        else:
            self.assertNotIn(ENABLED_SERVICES_KEY, siteconfig_settings)
            self.assertNotIn(DEFAULT_SERVICE_KEY, siteconfig_settings)


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
             '"2x": "%(2x)s", '
             '"3x": "%(3x)s"'
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
            '{"1x": "", "2x": "", "3x": ""}')

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
             '"2x": "%(2x)s", '
             '"3x": "%(3x)s"'
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
             ' class="avatar djblets-o-avatar">\n'
             % self.user.username)
        )

    def test_avatar_with_string_size_valid(self):
        """Testing {% avatar %} template tag with string-encoded int size"""
        avatar_services.register(DummyAvatarService)
        avatar_services.enable_service(DummyAvatarService)

        template = Template('{% load avatars %}'
                            '{% avatar target_user "32" avatar_service_id %}')

        self.assertHTMLEqual(
            template.render(RequestContext(self.request, {
                'target_user': self.user,
                'avatar_service_id': DummyAvatarService.avatar_service_id,
            })),
            ('<img src="http://example.com/avatar.png" alt="%s" width="32"'
             ' height="32" srcset="http://example.com/avatar.png 1x"'
             ' class="avatar djblets-o-avatar">\n'
             % self.user.username))

    def test_avatar_with_string_size_invalid(self):
        """Testing {% avatar %} template tag with invalid string size"""
        avatar_services.register(DummyAvatarService)
        avatar_services.enable_service(DummyAvatarService)

        template = Template('{% load avatars %}'
                            '{% avatar target_user "ABC" avatar_service_id %}')

        self.assertEqual(
            template.render(RequestContext(self.request, {
                'target_user': self.user,
                'avatar_service_id': DummyAvatarService.avatar_service_id,
            })),
            '')

    def test_avatar_invalid_service(self):
        """Testing {% avatar %} template tag rendering with an invalid avatar
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

        self.request.user = User.objects.get(username='admin')

        user = User.objects.create_user(
            first_name='<b>Bad',
            last_name='User</b>',
            username='bad_user',
            email='bad_user@example.com')

        Profile.objects.create(user=user)

        avatar_services.register(DummyAvatarService)
        avatar_services.enable_service(DummyAvatarService)

        self.assertHTMLEqual(
            t.render(RequestContext(self.request, {
                'target_user': user,
                'avatar_service_id': DummyAvatarService.avatar_service_id,
            })),
            '<img src="http://example.com/avatar.png" alt="%s" width="32"'
            ' height="32" srcset="http://example.com/avatar.png 1x"'
            ' class="avatar djblets-o-avatar">\n'
            % '&lt;b&gt;Bad User&lt;/b&gt;')


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
                    owner=storage_cls,
                    call_fake=lambda self, name, *args, **kwargs: name)

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
