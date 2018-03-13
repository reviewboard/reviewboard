from __future__ import unicode_literals

import importlib

from django.contrib.auth.models import AnonymousUser, Permission, User
from django.core.urlresolvers import ResolverMatch
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template import Context, Template
from django.test.client import RequestFactory
from django.views.generic.base import View
from djblets.features.testing import override_feature_check
from djblets.testing.decorators import add_fixtures

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.oauth.features import oauth2_service_feature
from reviewboard.oauth.models import Application
from reviewboard.site.context_processors import AllPermsWrapper
from reviewboard.site.middleware import LocalSiteMiddleware
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing.testcase import TestCase


class BasicTests(TestCase):
    """Tests basic LocalSite functionality"""
    fixtures = ['test_users', 'test_site']

    def test_access(self):
        """Test LocalSite.is_accessible_by"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")

        self.assertTrue(site.is_accessible_by(doc))
        self.assertFalse(site.is_accessible_by(dopey))

    def test_access_with_public(self):
        """Test LocalSite.is_accessible_by with public LocalSites"""
        doc = User.objects.get(username="doc")
        dopey = User.objects.get(username="dopey")
        site = LocalSite.objects.get(name="local-site-1")
        site.public = True

        self.assertTrue(site.is_accessible_by(doc))
        self.assertTrue(site.is_accessible_by(dopey))

    def test_local_site_reverse_with_no_local_site(self):
        """Testing local_site_reverse with no local site"""
        request = HttpRequest()

        self.assertEqual(local_site_reverse('dashboard'),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('dashboard', request=request),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('user', args=['sample-user']),
                         '/users/sample-user/')
        self.assertEqual(
            local_site_reverse('user', kwargs={'username': 'sample-user'}),
            '/users/sample-user/')

    def test_local_site_reverse_with_local_site(self):
        """Testing local_site_reverse with a local site"""
        request = HttpRequest()
        request.GET['local_site_name'] = 'test'

        self.assertEqual(local_site_reverse('dashboard', request=request),
                         '/dashboard/')
        self.assertEqual(local_site_reverse('user', args=['sample-user'],
                                            request=request),
                         '/users/sample-user/')
        self.assertEqual(
            local_site_reverse('user', kwargs={'username': 'sample-user'},
                               request=request),
            '/users/sample-user/')


class LocalSiteMiddlewareTests(TestCase):
    """Unit tests for reviewboard.site.middleware.LocalSiteMiddleware."""

    def setUp(self):
        super(LocalSiteMiddlewareTests, self).setUp()

        self.middleware = LocalSiteMiddleware()

    def test_request_local_site_empty(self):
        """Testing LocalSiteMiddleware's request.local_site with no LocalSite
        """
        request = HttpRequest()
        self.middleware.process_view(request=request, view_func=None,
                                     view_args=None, view_kwargs={})

        self.assertTrue(hasattr(request, '_local_site_name'))
        self.assertTrue(hasattr(request, 'local_site'))
        self.assertIsNone(request._local_site_name)
        self.assertIsNone(request.local_site)

    def test_request_local_site_not_empty(self):
        """Testing LocalSiteMiddleware's request.local_site with a LocalSite"""
        local_site = LocalSite.objects.create(name='test-site')

        request = HttpRequest()
        self.middleware.process_view(
            request=request,
            view_func=None,
            view_args=None,
            view_kwargs={
                'local_site_name': local_site.name,
            })

        self.assertTrue(hasattr(request, '_local_site_name'))
        self.assertTrue(hasattr(request, 'local_site'))
        self.assertEqual(request._local_site_name, 'test-site')
        self.assertEqual(request.local_site, local_site)


class PermissionWrapperTests(TestCase):
    """Testing the LocalSite-aware permissions wrapper."""
    def setUp(self):
        super(PermissionWrapperTests, self).setUp()

        self.user = User.objects.get(username='doc')
        self.assertFalse(self.user.is_superuser)

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_global_permission(self):
        """Testing AllPermsWrapper with global permission lookup"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.delete_reviewrequest', perms)
        self.assertNotIn('reviews.fake_permission', perms)

    @add_fixtures(['test_users', 'test_site'])
    def test_lookup_site_permission(self):
        """Testing AllPermsWrapper with site permission lookup"""
        local_site = LocalSite.objects.get(name=self.local_site_name)

        local_site_profile = LocalSiteProfile.objects.create(
            user=self.user,
            profile=self.user.get_profile(),
            local_site=local_site)
        local_site_profile.permissions['reviews.can_change_status'] = True
        local_site_profile.save()

        perms = AllPermsWrapper(self.user, self.local_site_name)

        self.assertIn('reviews.can_change_status', perms)
        self.assertNotIn('reviews.fake_permission', perms)


class AdminPermissionTests(TestCase):
    fixtures = ['test_users', 'test_site']

    def setUp(self):
        super(AdminPermissionTests, self).setUp()

        self.user = User.objects.get(username='doc')
        self.assertFalse(self.user.is_superuser)

        self.local_site = LocalSite.objects.get(name=self.local_site_name)
        self.local_site.admins.add(self.user)

    def test_assigned_permissions(self):
        """Testing LocalSite assigned admin permissions"""
        self.assertTrue(self.user.has_perm(
            'hostingsvcs.change_hostingserviceaccount', self.local_site))
        self.assertTrue(self.user.has_perm(
            'hostingsvcs.create_hostingserviceaccount', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_change_status', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_edit_reviewrequest', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.can_submit_as_another_user', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.change_default_reviewer', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.add_group', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.change_group', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.delete_file', self.local_site))
        self.assertTrue(self.user.has_perm(
            'reviews.delete_screenshot', self.local_site))
        self.assertTrue(self.user.has_perm(
            'scmtools.add_repository', self.local_site))
        self.assertTrue(self.user.has_perm(
            'scmtools.change_repository', self.local_site))

    def test_invalid_permissions(self):
        """Testing LocalSite invalid admin permissions"""
        self.assertFalse(self.user.has_perm(
            'reviews.delete_reviewrequest', self.local_site))
        self.assertFalse(self.user.has_perm(
            'dummy.permission', self.local_site))


class TemplateTagTests(TestCase):
    def test_local_site_url_with_no_local_site(self):
        """Testing localsite's {% url %} with no local site"""
        context = Context({})

        t = Template('{% url "dashboard" %}')
        self.assertEqual(t.render(context), '/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEqual(t.render(context), '/users/sample-user/')

    def test_local_site_url_with_local_site(self):
        """Testing localsite's {% url %} with local site"""

        # Make sure that {% url %} is registered as a built-in tag.
        importlib.import_module('reviewboard.site.templatetags')

        context = Context({
            'local_site_name': 'test',
        })

        t = Template('{% url "dashboard" %}')
        self.assertEqual(t.render(context), '/s/test/dashboard/')

        t = Template('{% url "user" "sample-user" %}')
        self.assertEqual(t.render(context), '/s/test/users/sample-user/')


class CheckLocalSiteAccessViewMixinTests(TestCase):
    """Unit tests for CheckLocalSiteAccessViewMixin."""

    @add_fixtures(['test_site', 'test_users'])
    def test_dispatch_with_local_site_and_allowed(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with LocalSite and
        access allowed
        """
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.local_site)
                self.assertEqual(view.local_site.name, 'local-site-1')

                return HttpResponse('success')

        request = RequestFactory().request()
        request.local_site = LocalSite.objects.get(name='local-site-1')
        request.user = request.local_site.users.all()[0]

        view = MyView.as_view()
        response = view(request, local_site_name='local-site-1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'success')

    @add_fixtures(['test_site', 'test_users'])
    def test_dispatch_with_local_site_and_not_allowed(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with LocalSite and
        access not allowed
        """
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.local_site)
                self.assertEqual(view.local_site.name, 'local-site-1')

                return HttpResponse('success')

        view = MyView.as_view()

        request = RequestFactory().request()
        request.resolver_match = ResolverMatch(view, [], {})
        request.local_site = LocalSite.objects.get(name='local-site-1')
        request.user = User.objects.create_user(username='test123',
                                                email='test123@example.com')

        response = view(request, local_site_name='local-site-1')
        self.assertEqual(response.status_code, 403)

    @add_fixtures(['test_site'])
    def test_dispatch_with_local_site_and_anonymous(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with LocalSite and
        anonymous user
        """
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.local_site)
                self.assertEqual(view.local_site.name, 'local-site-1')

                return HttpResponse('success')

        view = MyView.as_view()

        request = RequestFactory().request()
        request.resolver_match = ResolverMatch(view, [], {})
        request.local_site = LocalSite.objects.get(name='local-site-1')
        request.user = AnonymousUser()

        response = view(request, local_site_name='local-site-1')
        self.assertIsInstance(response, HttpResponseRedirect)

    @add_fixtures(['test_site', 'test_users'])
    def test_dispatch_with_no_local_site(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with no LocalSite"""
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNone(view.local_site)

                return HttpResponse('success')

        view = MyView.as_view()

        request = RequestFactory().request()
        request.resolver_match = ResolverMatch(view, [], {})
        request.local_site = None
        request.user = User.objects.get(username='doc')

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'success')


class OAuth2ApplicationTests(TestCase):
    """Testing Applicications assigned to a Local Site."""

    fixtures = ['test_users', 'test_site']

    def test_disable_reassign_to_admin(self):
        """Testing an Application is disabled and re-assigned to a Local Site
        admin when its owner is removed from a Local Site
        """
        with override_feature_check(oauth2_service_feature.feature_id, True):
            local_site = LocalSite.objects.get(pk=1)
            user = User.objects.get(username='doc')
            admin = User.objects.get(username='admin')
            application = self.create_oauth_application(user=user,
                                                        local_site=local_site)

            local_site.users.remove(user)

            application = Application.objects.get(pk=application.pk)
            self.assertTrue(application.is_disabled_for_security)
            self.assertEqual(application.original_user_id, user.pk)
            self.assertEqual(application.user_id, admin.pk)
            self.assertFalse(application.enabled)
