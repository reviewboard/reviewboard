"""Tests for OAuth2 authentication with the web API."""

from __future__ import unicode_literals

from datetime import timedelta

from django.contrib.auth.models import User
from djblets.features.testing import override_feature_check
from djblets.testing.decorators import add_fixtures
from djblets.webapi.auth.backends import reset_auth_backends
from djblets.webapi.testing.testcases import WebAPITestCaseMixin

from reviewboard.admin.siteconfig import load_site_config
from reviewboard.oauth.features import oauth2_service_feature
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase
from reviewboard.webapi.tests.mimetypes import error_mimetype, session_mimetype
from reviewboard.webapi.tests.urls import get_session_url


class OAuth2TokenAuthTests(WebAPITestCaseMixin, TestCase):
    """Authentcaiton tests for OAuth2 tokens."""

    error_mimetype = error_mimetype
    fixtures = ['test_users']

    def setUp(self):
        super(OAuth2TokenAuthTests, self).setUp()

        self.owner = User.objects.get(username='doc')
        self.user = User.objects.get(username='grumpy')

    def tearDown(self):
        super(OAuth2TokenAuthTests, self).tearDown()

        load_site_config()
        reset_auth_backends()

    @classmethod
    def tearDownClass(cls):
        super(OAuth2TokenAuthTests, cls).tearDownClass()

        load_site_config()
        reset_auth_backends()

    def test_auth(self):
        """Testing OAuth2 authentication to the Web API with a valid token"""
        application = self.create_oauth_application(user=self.owner)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_mimetype=session_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

    def test_auth_disabled_app(self):
        """Testing OAuth2 authentication to the Web API with a valid token
        against a disabled app
        """
        application = self.create_oauth_application(user=self.owner,
                                                    enabled=False)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_status=401)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    def test_auth_feature_disabled(self):
        """Testing OAuth2 authentication to the Web API with a valid token
        with the feature disabled
        """
        application = self.create_oauth_application(user=self.owner)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, False):
            load_site_config()
            rsp = self.api_get(get_session_url(),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_status=401)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    def test_auth_expired(self):
        """Testing OAuth2 authentication to the Web API with an expired token
        """
        application = self.create_oauth_application(user=self.owner)
        token = self.create_oauth_token(application, self.user, 'session:read',
                                        expires=timedelta(hours=-1))

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_status=401)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    def test_auth_invalid_scope(self):
        """Testing OAuth2 authentication to the Web API with a token missing
        scopes"""
        application = self.create_oauth_application(user=self.owner)
        token = self.create_oauth_token(application, self.user)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_status=403)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_auth_local_site(self):
        """Testing OAuth2 authentication to the Web API with a token limited to
        a Local Site
        """
        local_site = LocalSite.objects.get(pk=1)
        local_site.users.add(self.user)
        application = self.create_oauth_application(user=self.owner,
                                                    local_site=local_site)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_status=401)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_auth_no_local_site(self):
        """Testing OAuth2 authentication to the Web API of a Local Site with an
        application not on that Local Site
        """
        local_site = LocalSite.objects.get(pk=1)
        local_site.users.add(self.user)
        application = self.create_oauth_application(user=self.owner)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(local_site.name),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_status=401)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_auth_no_local_site_access(self):
        """Testing OAuth2 authentication to the Web API of a Local Site with an
        application on that site without access to it
        """
        local_site = LocalSite.objects.get(pk=1)

        self.assertFalse(local_site.is_accessible_by(self.user))

        application = self.create_oauth_application(user=self.owner,
                                                    local_site=local_site)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(local_site.name),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_status=401)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_auth_local_site_public(self):
        """Testing OAuth2 authentication to the Web API of a public Local Site
        with an application on that Local Site
        """
        local_site = LocalSite.objects.get(pk=1)
        local_site.public = True
        local_site.save(update_fields=('public',))

        self.assertTrue(local_site.is_accessible_by(self.user))

        application = self.create_oauth_application(user=self.owner,
                                                    local_site=local_site)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(local_site.name),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_mimetype=session_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_auth_local_site_member(self):
        """Testing OAuth2 authentication to the Web API of a Local Site with
        with an application on a that Local Site as a member
        """
        local_site = LocalSite.objects.get(pk=1)
        local_site.users.add(self.user)
        local_site.save(update_fields=('public',))

        self.assertTrue(local_site.is_accessible_by(self.user))

        application = self.create_oauth_application(user=self.owner,
                                                    local_site=local_site)
        token = self.create_oauth_token(application, self.user, 'session:read')

        with override_feature_check(oauth2_service_feature.feature_id, True):
            load_site_config()
            rsp = self.api_get(get_session_url(local_site.name),
                               HTTP_AUTHORIZATION='Bearer %s' % token.token,
                               expected_mimetype=session_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
