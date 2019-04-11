"""Unit tests for reviewboard.accounts.mixins.LoginRequiredViewMixin."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse, HttpResponseRedirect
from django.test.client import RequestFactory
from django.views.generic.base import View

from reviewboard.accounts.mixins import LoginRequiredViewMixin
from reviewboard.testing import TestCase


class LoginRequiredViewMixinTests(TestCase):
    """Unit tests for reviewboard.accounts.mixins.LoginRequiredViewMixin."""

    def test_dispatch_authenticated_user(self):
        """Testing LoginRequiredViewMixin.dispatch with authenticated user"""
        class MyView(LoginRequiredViewMixin, View):
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

    def test_dispatch_anonymous_user(self):
        """Testing LoginRequiredViewMixin.dispatch with anonymous user"""
        class MyView(LoginRequiredViewMixin, View):
            def get(view, *args, **kwargs):
                self.fail('Should not be reached')

        request = RequestFactory().request()
        request.user = AnonymousUser()

        view = MyView.as_view()
        response = view(request)

        self.assertIsInstance(response, HttpResponseRedirect)
