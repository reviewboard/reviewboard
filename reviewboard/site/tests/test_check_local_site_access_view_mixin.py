"""Unit tests for reviewboard.site.mixins.CheckLocalSiteAccessViewMixin."""

from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.base import View

from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin
from reviewboard.testing.testcase import TestCase


class CheckLocalSiteAccessViewMixinTests(TestCase):
    """Unit tests for CheckLocalSiteAccessViewMixin."""

    fixtures = ['test_users', 'test_site']

    def test_dispatch_with_local_site_and_allowed(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with LocalSite and
        access allowed
        """
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.local_site)
                self.assertEqual(view.local_site.name, 'local-site-1')

                return HttpResponse('success')

        local_site = self.get_local_site(self.local_site_name)
        request = self.create_http_request(user=local_site.users.all()[0],
                                           local_site=local_site)

        view = MyView.as_view()
        response = view(request, local_site_name=local_site.name)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')

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

        local_site = self.get_local_site(self.local_site_name)
        request = self.create_http_request(
            user=User.objects.create_user(username='test123',
                                          email='test123@example.com'),
            local_site=local_site,
            view=view)

        response = view(request, local_site_name=local_site.name)
        self.assertEqual(response.status_code, 403)

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

        local_site = self.get_local_site(self.local_site_name)
        request = self.create_http_request(local_site=local_site,
                                           view=view)

        response = view(request, local_site_name=local_site.name)
        self.assertIsInstance(response, HttpResponseRedirect)

    def test_dispatch_with_no_local_site(self):
        """Testing CheckLocalSiteAccessViewMixin.dispatch with no LocalSite"""
        class MyView(CheckLocalSiteAccessViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNone(view.local_site)

                return HttpResponse('success')

        view = MyView.as_view()

        request = self.create_http_request(
            user=User.objects.get(username='doc'),
            view=view)

        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')
