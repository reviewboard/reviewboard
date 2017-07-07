"""Tests for OAuth2 Applications."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from djblets.testing.decorators import add_fixtures
from oauth2_provider.generators import (generate_client_id,
                                        generate_client_secret)
from oauth2_provider.models import AbstractApplication

from reviewboard.oauth.forms import ApplicationForm, UserApplicationForm
from reviewboard.oauth.models import Application
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ApplicationFormTests(TestCase):
    """Tests for the ApplicationForm."""

    fixtures = ['test_users']

    def test_grant_implicit_no_uris(self):
        """Testing ApplicationForm.clean() with GRANT_IMPLICIT and no URIs
        matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_IMPLICIT, False)

    def test_grant_implicit_uris(self):
        """Testing ApplicationForm.clean() with GRANT_IMPLICIT and URIs
        matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            'http://example.com/', Application.GRANT_IMPLICIT, True)

    def test_grant_authorization_code_no_uris(self):
        """Testing ApplicationForm.clean() with GRANT_AUTHORIZATION_CODE and no
        URIs matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_AUTHORIZATION_CODE, False)

    def test_grant_authorization_code_uris(self):
        """Testing ApplicationForm.clean() with GRANT_AUTHORIZATION_CODE and
        URIS matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            'http://example.com/', Application.GRANT_AUTHORIZATION_CODE, True)

    def test_grant_password_no_uris(self):
        """Testing ApplicationForm.clean() with GRANT_PASSWORD and no URIs
        matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_PASSWORD, True)

    def test_grant_password_uris(self):
        """Testing ApplicationForm.clean() with GRANT_PASSWORD and URIs
        matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            'http://example.com/', Application.GRANT_PASSWORD, True)

    def test_grant_client_credentials_no_uris(self):
        """Testing ApplicationForm.clean() with GRANT_CLIENT_CREDENTIALS and no
        URIs matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_CLIENT_CREDENTIALS, True)

    def test_grant_client_credentials_uris(self):
        """Testing ApplicationForm.clean() with GRANT_CLIENT_CREDENTIALS and no
        URIs matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_CLIENT_CREDENTIALS, True)

    def _test_redirect_uri_grant_combination(self, redirect_uris, grant_type,
                                             is_valid):
        common_fields = {
            'authorization_grant_type': grant_type,
            'client_id': generate_client_id(),
            'client_secret': generate_client_secret(),
            'client_type': Application.CLIENT_PUBLIC,
            'name': 'test',
            'redirect_uris': redirect_uris,
        }
        form_data = common_fields.copy()
        form_data['user'] = 1
        form = ApplicationForm(data=form_data)

        self.assertEqual(form.is_valid(), is_valid)
        app = Application(user=User.objects.get(username='doc'),
                          **common_fields)

        # Ensure that the error cases of AbstractApplication.clean() matches
        # our implementation.
        if is_valid:
            AbstractApplication.clean(app)
        else:
            self.assertIn('redirect_uris', form.errors)

            with self.assertRaises(ValidationError):
                AbstractApplication.clean(app)


class UserApplicationFormTests(TestCase):
    """Tests for the UserApplicationForm."""

    fixtures = ['test_users']

    def test_set_user(self):
        """Testing UserApplicationForm cannot assign different user"""
        user = User.objects.get(username='doc')
        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_id': generate_client_id(),
                'client_secret': generate_client_secret(),
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'user': 2,
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.user, user)

    def test_reassign_user(self):
        """Testing UserApplicationForm cannot re-assign different user"""
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type':
                    application.authorization_grant_type,
                'client_id': application.client_id,
                'client_secret': application.client_secret,
                'client_type': application.client_type,
                'name': application.name,
                'redirect_uris': application.redirect_uris,
                'user': 2,
            },
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.user, user)

    @add_fixtures(['test_site'])
    def test_assign_local_site(self):
        """Testing UserApplicationForm cannot assign Local Site"""
        user = User.objects.get(username='doc')

        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_id': generate_client_id(),
                'client_secret': generate_client_secret(),
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'local_site': 'local-site-1',
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.local_site, None)

    @add_fixtures(['test_site'])
    def test_reassign_local_site(self):
        """Testing UserApplicationForm cannot re-assign Local Site"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.get(pk=1)
        application = self.create_oauth_application(user, local_site)

        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type':
                    application.authorization_grant_type,
                'client_id': application.client_id,
                'client_secret': application.client_secret,
                'client_type': application.client_type,
                'name': application.name,
                'redirect_uris': application.redirect_uris,
                'local_site': '',
            },
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.local_site, local_site)

    def test_set_extra_data(self):
        """Testing UserApplicationForm cannot assign extra_data"""
        user = User.objects.get(username='doc')
        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_id': generate_client_id(),
                'client_secret': generate_client_secret(),
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'extra_data': 1,
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.extra_data, {})

    def test_reassign_extra_data(self):
        """Testing UserApplicationForm cannot re-assign extra_data"""
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type':
                    application.authorization_grant_type,
                'client_id': application.client_id,
                'client_secret': application.client_secret,
                'client_type': application.client_type,
                'name': application.name,
                'redirect_uris': application.redirect_uris,
                'extra_data': 1,
            },
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.extra_data, {})

    def test_set_skip_authorization(self):
        """Testing UserApplicationForm cannot assign skip_authorization"""
        user = User.objects.get(username='doc')
        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_id': generate_client_id(),
                'client_secret': generate_client_secret(),
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'extra_data': 1,
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.skip_authorization, False)

    def test_reassign_skip_authorization(self):
        """Testing UserApplicationForm cannot re-assign skip_authorization"""
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        form = UserApplicationForm(
            user,
            data={
                'authorization_grant_type':
                    application.authorization_grant_type,
                'client_id': application.client_id,
                'client_secret': application.client_secret,
                'client_type': application.client_type,
                'name': application.name,
                'redirect_uris': application.redirect_uris,
                'skip_authorization': True,
            },
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.skip_authorization, False)
