from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest
from django.template import RequestContext, Template
from djblets.avatars.services.gravatar import GravatarService

from reviewboard.testing import TestCase
from reviewboard.avatars import avatar_services
from reviewboard.avatars.testcase import AvatarServicesTestMixin
from reviewboard.avatars.tests import DummyAvatarService


class TemplateTagTests(AvatarServicesTestMixin, TestCase):
    """Tests for reviewboard.avatars.templatetags."""

    fixtures = ['test_users']

    @classmethod
    def setUpClass(cls):
        super(TemplateTagTests, cls).setUpClass()
        avatar_services.enable_service(GravatarService.avatar_service_id,
                                       save=False)

    def setUp(self):
        super(TemplateTagTests, self).setUp()

        gravatar_service = avatar_services.get_avatar_service(
            GravatarService.avatar_service_id)
        avatar_services.enable_service(gravatar_service.avatar_service_id,
                                       save=False)
        avatar_services.set_default_service(gravatar_service, save=False)

        self.user = User.objects.get(username='doc')
        self.request = HttpRequest()
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
            '{'
            '"1x": "%(1x)s", '
            '"3x": "%(3x)s", '
            '"2x": "%(2x)s"'
            '}'
            % service.get_avatar_urls_uncached(self.user, 32)
        )

    def test_avatar_urls_with_service(self):
        """Testing {% avatar_urls %} template tag with avatar_service_id"""
        service = DummyAvatarService(use_2x=True)
        avatar_services.register(service)
        avatar_services.enable_service(service.avatar_service_id)

        t = Template(
            '{% load avatars %}'
            '{% avatar_urls u 32 service_id %}'
        )

        self.assertEqual(
            t.render(RequestContext(self.request, {
                'u': self.user,
                'service_id': service.avatar_service_id,
            })),
            '{'
            '"1x": "%(1x)s", '
            '"2x": "%(2x)s"'
            '}'
            % service.get_avatar_urls_uncached(self.user, 32)
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
            '{'
            '"1x": "%(1x)s", '
            '"3x": "%(3x)s", '
            '"2x": "%(2x)s"'
            '}'
            % service.get_avatar_urls_uncached(self.user, 32)
        )
