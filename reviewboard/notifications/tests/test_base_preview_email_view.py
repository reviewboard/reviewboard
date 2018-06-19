from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.http import Http404
from django.test.client import RequestFactory
from django.test.utils import override_settings

from reviewboard.notifications.email.message import EmailMessage
from reviewboard.notifications.email.views import BasePreviewEmailView
from reviewboard.testing import TestCase


class BasePreviewEmailViewTests(TestCase):
    """Unit tests for BasePreviewEmailView."""

    @override_settings(DEBUG=True)
    def test_get_with_classmethod(self):
        """Testing BasePreviewEmailView.get with build_email as classmethod"""
        class MyPreviewEmailView(BasePreviewEmailView):
            @classmethod
            def build_email(cls, test_var):
                self.assertEqual(test_var, 'test')
                return EmailMessage(subject='Test Subject',
                                    text_body='Test Body')

            def get_email_data(view, request, test_var=None, *args, **kwargs):
                self.assertEqual(test_var, 'test')

                return {
                    'test_var': test_var,
                }

        request = RequestFactory().request()
        request.user = User.objects.create_user(username='test-user',
                                                email='user@example.com')

        view = MyPreviewEmailView.as_view()
        response = view(request, test_var='test', message_format='text')

        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=True)
    def test_get_with_staticmethod(self):
        """Testing BasePreviewEmailView.get with build_email as staticmethod"""
        class MyPreviewEmailView(BasePreviewEmailView):
            @staticmethod
            def build_email(test_var):
                self.assertEqual(test_var, 'test')
                return EmailMessage(subject='Test Subject',
                                    text_body='Test Body')

            def get_email_data(view, request, test_var=None, *args, **kwargs):
                self.assertEqual(test_var, 'test')

                return {
                    'test_var': test_var,
                }

        request = RequestFactory().request()
        request.user = User.objects.create_user(username='test-user',
                                                email='user@example.com')

        view = MyPreviewEmailView.as_view()
        response = view(request, test_var='test', message_format='text')

        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=False)
    def test_get_with_debug_false(self):
        """Testing BasePreviewEmailView.get with DEBUG=False"""
        class MyPreviewEmailView(BasePreviewEmailView):
            @classmethod
            def build_email(cls, test_var):
                self.fail('build_email should not be reached')
                return EmailMessage(subject='Test Subject',
                                    text_body='Test Body')

            def get_email_data(view, request, test_var=None, *args, **kwargs):
                self.fail('get_email_data should not be reached')

        request = RequestFactory().request()
        request.user = User.objects.create_user(username='test-user',
                                                email='user@example.com')

        view = MyPreviewEmailView.as_view()

        with self.assertRaises(Http404):
            view(request, test_var='test', message_format='text')
