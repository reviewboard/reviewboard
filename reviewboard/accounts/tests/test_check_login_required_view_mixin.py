"""Unit tests for reviewboard.accounts.mixins.CheckLoginRequiredViewMixin."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse, HttpResponseRedirect
from django.test.client import RequestFactory
from django.views.generic.base import View
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.mixins import CheckLoginRequiredViewMixin
from reviewboard.testing import TestCase


class CheckLoginRequiredViewMixinTests(TestCase):
    """Unit tests for reviewboard.accounts.mixins.CheckLoginRequiredViewMixin.
    """

    def test_dispatch_authenticated_user(self):
        """Testing CheckLoginRequiredViewMixin.dispatch with authenticated user
        """
        class MyView(CheckLoginRequiredViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertTrue(view.request.user.is_authenticated())

                return HttpResponse('success')

        request = RequestFactory().request()
        request.user = User.objects.create_user(username='doc',
                                                email='doc@example.com')

        view = MyView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')

    def test_dispatch_anonymous_user_and_login_not_required(self):
        """Testing CheckLoginRequiredViewMixin.dispatch with anonymous user
        and login not required
        """
        class MyView(CheckLoginRequiredViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertTrue(view.request.user.is_anonymous())

                return HttpResponse('success')

        request = RequestFactory().request()
        request.user = AnonymousUser()

        with self.siteconfig_settings({'auth_require_sitewide_login': False},
                                      reload_settings=False):
            view = MyView.as_view()
            response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')

    def test_dispatch_anonymous_user_and_login_required(self):
        """Testing CheckLoginRequiredViewMixin.dispatch with anonymous user
        and login required
        """
        class MyView(CheckLoginRequiredViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertTrue(view.request.user.is_anonymous())

                return HttpResponse('success')

        request = RequestFactory().request()
        request.user = AnonymousUser()

        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            view = MyView.as_view()
            response = view(request)

        self.assertIsInstance(response, HttpResponseRedirect)
