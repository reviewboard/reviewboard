"""Tests for OAuth2 Applications."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from djblets.testing.decorators import add_fixtures

from reviewboard.oauth.forms import (ApplicationChangeForm,
                                     ApplicationCreationForm,
                                     UserApplicationChangeForm,
                                     UserApplicationCreationForm)
from reviewboard.oauth.models import Application
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ApplicationChangeFormTests(TestCase):
    """Tests for the ApplicationChangeForm."""

    fixtures = ['test_users']

    def test_reassign_client_id(self):
        """Testing ApplicationChangeForm cannot re-assign client_id"""
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        original_id = application.client_id
        form = ApplicationChangeForm(
            data=dict(
                model_to_dict(
                    instance=application,
                    fields=ApplicationChangeForm.base_fields,
                    exclude=('client_id', 'client_secret')
                ),
                client_id='foo',
            ),
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.client_id, original_id)

    def test_reassign_client_secret(self):
        """Testing ApplicationChangeForm cannot re-assign client_secret"""
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        original_secret = application.client_secret
        form = ApplicationChangeForm(
            data=dict(
                model_to_dict(
                    instance=application,
                    fields=ApplicationChangeForm.base_fields,
                    exclude=('client_id', 'client_secret')
                ),
                client_secret='bar',
            ),
            instance=application,
        )
        form.is_valid()
        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.client_secret, original_secret)

    def test_grant_implicit_no_uris(self):
        """Testing ApplicationChangeForm.clean() with GRANT_IMPLICIT and no
        URIs matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_IMPLICIT, False)

    def test_grant_implicit_uris(self):
        """Testing ApplicationChangeForm.clean() with GRANT_IMPLICIT and URIs
        matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            'http://example.com/', Application.GRANT_IMPLICIT, True)

    def test_grant_authorization_code_no_uris(self):
        """Testing ApplicationChangeForm.clean() with
        GRANT_AUTHORIZATION_CODE and no URIs matches
        AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_AUTHORIZATION_CODE, False)

    def test_grant_authorization_code_uris(self):
        """Testing ApplicationChangeForm.clean() with
        GRANT_AUTHORIZATION_CODE and URIS matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            'http://example.com/', Application.GRANT_AUTHORIZATION_CODE, True)

    def test_grant_password_no_uris(self):
        """Testing ApplicationChangeForm.clean() with GRANT_PASSWORD and no
        URIs matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_PASSWORD, True)

    def test_grant_password_uris(self):
        """Testing ApplicationChangeForm.clean() with GRANT_PASSWORD and URIs
        matches AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            'http://example.com/', Application.GRANT_PASSWORD, True)

    def test_grant_client_credentials_no_uris(self):
        """Testing ApplicationChangeForm.clean() with
        GRANT_CLIENT_CREDENTIALS and no URIs matches
        AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_CLIENT_CREDENTIALS, True)

    def test_grant_client_credentials_uris(self):
        """Testing ApplicationChangeForm.clean() with
        GRANT_CLIENT_CREDENTIALS and no URIs matches
        AbstractApplication.clean()
        """
        self._test_redirect_uri_grant_combination(
            '', Application.GRANT_CLIENT_CREDENTIALS, True)

    @add_fixtures(['test_site'])
    def test_enable_disabled_for_security(self):
        """Testing ApplicationChangeForm will not enable an application
        disabled for security
        """
        local_site = LocalSite.objects.get(pk=1)
        admin = User.objects.get(username='admin')
        owner = User.objects.get(username='doc')
        local_site.users.remove(owner)

        application = self.create_oauth_application(user=admin,
                                                    local_site=local_site,
                                                    enabled=False,
                                                    original_user=owner)

        self.assertTrue(application.is_disabled_for_security)
        self.assertEqual(application.original_user, owner)

        form = ApplicationChangeForm(
            data=dict(model_to_dict(application),
                      enabled=True),
            instance=application,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                         [ApplicationCreationForm.DISABLED_FOR_SECURITY_ERROR])

    def _test_redirect_uri_grant_combination(self, redirect_uris, grant_type,
                                             is_valid):
        doc = User.objects.get(username='doc')
        common_fields = {
            'authorization_grant_type': grant_type,
            'redirect_uris': redirect_uris,
        }

        application = self.create_oauth_application(user=doc)

        # This should always succeed.
        super(Application, application).clean()

        form = ApplicationChangeForm(
            data=dict(model_to_dict(application), **common_fields),
            instance=application,
        )

        self.assertEqual(form.is_valid(), is_valid)

        application = Application(user=doc, **common_fields)

        # Ensure that the error cases of AbstractApplication.clean() matches
        # our implementation.
        if is_valid:
            super(Application, application).clean()
        else:
            self.assertIn('redirect_uris', form.errors)

            with self.assertRaises(ValidationError):
                super(Application, application).clean()


class ApplicationCreationFormTests(TestCase):
    """Tests for the ApplicationCreationForm."""

    fixtures = ['test_users']

    def test_valid_client_id_and_secret(self):
        """Testing ApplicationCreationForm sets a valid client_id and
        client_secret
        """
        form = ApplicationCreationForm(data={
            'authorization_grant_type': Application.GRANT_CLIENT_CREDENTIALS,
            'client_id': 'foo',
            'client_type': Application.CLIENT_PUBLIC,
            'client_secret': 'bar',
            'enabled': True,
            'name': 'Test Application',
            'redirect_uris': '',
            'user': 1,
        })

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertNotEqual(application.client_id, form.data['client_id'])
        self.assertNotEqual(application.client_secret,
                            form.data['client_secret'])
        self.assertGreater(len(application.client_id), 0)
        self.assertGreater(len(application.client_secret), 0)


class UserApplicationCreationFormTests(TestCase):
    """Tests for the UserApplicationCreationForm."""

    fixtures = ['test_users']

    def test_set_user(self):
        """Testing UserApplicationCreationForm cannot assign different user"""
        user = User.objects.get(username='doc')
        form = UserApplicationCreationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'user': 2,
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.user, user)

    @add_fixtures(['test_site'])
    def test_assign_local_site(self):
        """Testing UserApplicationCreationForm with Local Site"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.get(name=self.local_site_name)

        form = UserApplicationCreationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'local_site': local_site.pk
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.local_site, local_site)

    def test_assign_local_site_inacessible(self):
        """Testing UserApplicationCreationForm with an inaccessible Local Site
        """
        local_site = LocalSite.objects.create(name='inacessible')
        user = User.objects.get(username='doc')

        form = UserApplicationCreationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'local_site': local_site.pk
            },
        )

        self.assertFalse(form.is_valid())

    def test_set_extra_data(self):
        """Testing UserApplicationCreationForm cannot assign extra_data"""
        user = User.objects.get(username='doc')
        form = UserApplicationCreationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'extra_data': 1,
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.extra_data, {})

    def test_set_skip_authorization(self):
        """Testing UserApplicationCreationForm cannot assign
        skip_authorization
        """
        user = User.objects.get(username='doc')
        form = UserApplicationCreationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
                'extra_data': 1,
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.skip_authorization, False)

    def test_set_client_id(self):
        """Testing UserApplicationCreationForm cannot assign client_id
        """
        user = User.objects.get(username='doc')
        form = UserApplicationCreationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_id': 'foo',
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertNotEqual(application.client_id, 'foo')
        self.assertNotEqual(len(application.client_id), 0)

    def test_set_client_secret(self):
        """Testing UserApplicationCreationForm cannot assign client_secret
        """
        user = User.objects.get(username='doc')
        form = UserApplicationCreationForm(
            user,
            data={
                'authorization_grant_type': Application.GRANT_IMPLICIT,
                'client_secret': 'bar',
                'client_type': Application.CLIENT_PUBLIC,
                'name': 'test',
                'redirect_uris': 'http://example.com',
            },
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertNotEqual(application.client_secret, 'bar')
        self.assertNotEqual(len(application.client_secret), 0)


class UserApplicationChangeFormTests(TestCase):
    """Tests for the UserApplicationChangeForm."""

    fixtures = ['test_users']

    def test_reassign_user(self):
        """Testing UserApplicationChangeForm cannot re-assign different user"""
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        form = UserApplicationChangeForm(
            user,
            data=dict(
                model_to_dict(
                    instance=application,
                    fields=UserApplicationChangeForm.base_fields,
                    exclude=('client_id', 'client_secret'),
                ),
                user=2,
            ),
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.user, user)

    @add_fixtures(['test_site'])
    def test_reassign_local_site(self):
        """Testing UserApplicationChangeForm cannot re-assign Local Site"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.get(pk=1)
        application = self.create_oauth_application(user, local_site)

        form = UserApplicationChangeForm(
            user,
            data=dict(
                model_to_dict(
                    instance=application,
                    fields=UserApplicationChangeForm.base_fields,
                    exclude=('client_id', 'client_secret'),
                ),
                local_site=2,
            ),
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.local_site, local_site)

    def test_reassign_extra_data(self):
        """Testing UserApplicationChangeForm cannot re-assign extra_data"""
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        form = UserApplicationChangeForm(
            user,
            data=dict(
                model_to_dict(
                    instance=application,
                    fields=UserApplicationChangeForm.base_fields,
                    exclude=('client_id', 'client_secret'),
                ),
                extra_data=1,
            ),
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.extra_data, {})

    def test_reassign_skip_authorization(self):
        """Testing UserApplicationChangeForm cannot re-assign
        skip_authorization
        """
        user = User.objects.get(username='doc')
        application = self.create_oauth_application(user)
        form = UserApplicationChangeForm(
            user,
            data=dict(
                model_to_dict(
                    instance=application,
                    fields=UserApplicationChangeForm.base_fields,
                    exclude=('client_id', 'client_secret'),
                ),
                skip_authorization=True,
            ),
            instance=application,
        )

        self.assertTrue(form.is_valid())
        application = form.save()
        self.assertEqual(application.skip_authorization, False)
