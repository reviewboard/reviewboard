"""Unit tests for reviewboard.accounts.mixins.UserProfileRequiredViewMixin."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.test.client import RequestFactory
from django.views.generic.base import View

from reviewboard.accounts.mixins import UserProfileRequiredViewMixin
from reviewboard.accounts.models import Profile
from reviewboard.testing import TestCase


class UserProfileRequiredViewMixinTests(TestCase):
    """Unit tests for reviewboard.accounts.mixins.UserProfileRequiredViewMixin.
    """

    def test_dispatch_with_no_profile(self):
        """Testing UserProfileRequiredViewMixin.dispatch with authenticated
        user without a profile
        """
        class MyView(UserProfileRequiredViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.request.user.get_profile())

                return HttpResponse('success')

        request = RequestFactory().request()
        request.user = User.objects.create_user(username='doc',
                                                email='doc@example.com')

        view = MyView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')

    def test_dispatch_with_profile(self):
        """Testing UserProfileRequiredViewMixin.dispatch with authenticated
        user with a profile
        """
        class MyView(UserProfileRequiredViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsNotNone(view.request.user.get_profile())

                return HttpResponse('success')

        request = RequestFactory().request()
        request.user = User.objects.create_user(username='doc',
                                                email='doc@example.com')
        Profile.objects.create(user=request.user)

        view = MyView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')

    def test_dispatch_with_anonymous(self):
        """Testing UserProfileRequiredViewMixin.dispatch with anonymous user"""
        class MyView(UserProfileRequiredViewMixin, View):
            def get(view, *args, **kwargs):
                self.assertIsInstance(view.request.user, AnonymousUser)

                return HttpResponse('success')

        request = RequestFactory().request()
        request.user = AnonymousUser()

        view = MyView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'success')
