"""Tests for the OAuthTokenResource."""

from __future__ import unicode_literals

from django.utils import six
from djblets.db.query import get_object_or_none
from djblets.features.testing import override_feature_check
from djblets.testing.decorators import add_fixtures
from djblets.webapi.testing.decorators import webapi_test_template
from djblets.webapi.errors import DOES_NOT_EXIST
from oauth2_provider.models import AccessToken

from reviewboard.oauth.features import oauth2_service_feature
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (oauth_token_item_mimetype,
                                                oauth_token_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_oauth_token_item_url,
                                           get_oauth_token_list_url)


def _compare_item(self, item_rsp, access_token):
    self.assertEqual(item_rsp['application'], access_token.application.name)
    self.assertEqual(item_rsp['expires'], access_token.expires.isoformat())
    self.assertEqual(set(item_rsp['scope']), set(access_token.scope.split()))
    self.assertEqual(item_rsp['token'], access_token.token)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the OAuthTokenResource list APIs."""

    fixtures = ['test_users']
    resource = resources.oauth_token
    sample_api_url = 'oauth-tokens/'

    test_api_token_access = False
    test_oauth_token_access = False

    compare_item = _compare_item

    def setup_http_not_allowed_list_test(self, user):
        return get_oauth_token_list_url()

    #
    # HTTP GET tests
    #
    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            application = self.create_oauth_application(
                user=user,
                with_local_site=with_local_site,
            )

            items = [
                self.create_oauth_token(user=user, application=application),
            ]
        else:
            items = []

        return (get_oauth_token_list_url(local_site_name=local_site_name),
                oauth_token_list_mimetype,
                items)

    @webapi_test_template
    def test_get_superuser(self):
        """Testing the GET <URL> API as a superuser"""
        url, mimetype, tokens = self.setup_basic_get_test(self.user, False,
                                                          None, True)
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            rsp = self.api_get(url, expected_mimetype=mimetype)

        self.assertIn('oauth_tokens', rsp)
        self.assertEqual(len(rsp['oauth_tokens']), 1)
        self.compare_item(rsp['oauth_tokens'][0], tokens[0])

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_superuser_local_site(self):
        """Testing the GET <URL> API with access to a Local Site as a superuser
        """
        url, mimetype, tokens = self.setup_basic_get_test(
            self.user, True, self.local_site_name, True)
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            rsp = self.api_get(url, expected_mimetype=mimetype)

        self.assertIn('oauth_tokens', rsp)
        self.assertEqual(len(rsp['oauth_tokens']), 1)
        self.compare_item(rsp['oauth_tokens'][0], tokens[0])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the OAuthTokenResource item APIs."""

    fixtures = ['test_users']
    resource = resources.oauth_token
    sample_api_url = 'oauth-tokens/<token-id>/'

    not_owner_status_code = 404
    not_owner_error = DOES_NOT_EXIST
    test_api_token_access = False
    test_oauth_token_access = False

    compare_item = _compare_item

    def setup_http_not_allowed_item_test(self, user):
        return get_oauth_token_item_url(1)

    #
    # HTTP GET tests
    #
    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        application = self.create_oauth_application(
            user=user,
            with_local_site=with_local_site,
        )
        access_token = self.create_oauth_token(user=user,
                                               application=application,
                                               scope='root:read')

        return (get_oauth_token_item_url(access_token.pk, local_site_name),
                oauth_token_item_mimetype,
                access_token)

    @webapi_test_template
    def test_get_superuser(self):
        """Testing the GET <URL> API as a superuser"""
        url, mimetype, token = self.setup_basic_get_test(self.user, False,
                                                         None)
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            rsp = self.api_get(url, expected_mimetype=mimetype)

        self.assertIn('oauth_token', rsp)
        self.compare_item(rsp['oauth_token'], token)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_superuser_local_site(self):
        """Testing the GET <URL> API with access to a Local Site as a superuser
        """
        url, mimetype, token = self.setup_basic_get_test(self.user, True,
                                                         self.local_site_name)
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            rsp = self.api_get(url, expected_mimetype=mimetype)

        self.assertIn('oauth_token', rsp)
        self.compare_item(rsp['oauth_token'], token)

    #
    # HTTP PUT tests
    #
    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        application = self.create_oauth_application(
            user=user,
            with_local_site=with_local_site)
        access_token = self.create_oauth_token(user=user,
                                               application=application,
                                               scope='root:read')

        if put_valid_data:
            request_data = {
                'add_scopes': 'user:read',
                'remove_scopes': 'root:read'
            }
        else:
            request_data = {
                'add_scopes': 'root:write',
                'scopes': 'root:write'
            }

        return (get_oauth_token_item_url(access_token.pk, local_site_name),
                oauth_token_item_mimetype,
                request_data,
                access_token,
                [])

    def check_put_result(self, user, item_rsp, access_token):
        self.compare_item(item_rsp,
                          AccessToken.objects.get(pk=access_token.pk))

    @webapi_test_template
    def test_put_superuser(self):
        """Testing the PUT <URL> API as a superuser"""
        url, mimetype, request_data, token = self.setup_basic_put_test(
            self.user, False, None, True)[:-1]
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            rsp = self.api_get(url, request_data, expected_mimetype=mimetype)

        self.assertIn('oauth_token', rsp)
        self.check_put_result(self.user, rsp['oauth_token'], token)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_superuser_local_site(self):
        """Testing the PUT <URL> API with access to a Local Site as a superuser
        """
        url, mimetype, request_data, token = self.setup_basic_put_test(
            self.user, True, self.local_site_name, True)[:-1]
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            rsp = self.api_get(url, request_data, expected_mimetype=mimetype)

        self.assertIn('oauth_token', rsp)
        self.check_put_result(self.user, rsp['oauth_token'], token)

    #
    # HTTP DELETE tests
    #
    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        application = self.create_oauth_application(
            user=user,
            with_local_site=with_local_site,
        )
        access_token = self.create_oauth_token(application=application,
                                               user=user)

        return (get_oauth_token_item_url(access_token.pk, local_site_name),
                [access_token.pk])

    def check_delete_result(self, user, access_token_pk):
        self.assertIsNone(get_object_or_none(AccessToken, pk=access_token_pk))

    @webapi_test_template
    def def_test_delete_superuser(self):
        """Testing the DELETE <URL> API as a superuser"""
        url, (pk,) = self.setup_basic_delete_test(self.user, False, None)
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            self.api_delete(url, expected_status=204)

        self.check_put_result(self.user, pk)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def def_test_delete_superuser_local_site(self):
        """Testing the DELETE <URL> API with access to a Local Site as a
        superuser
        """
        url, (pk,) = self.setup_basic_delete_test(self.user, True,
                                                  self.local_site_name)
        self._login_user(admin=True)

        with override_feature_check(oauth2_service_feature.feature_id, True):
            self.api_delete(url, expected_status=204)

        self.check_put_result(self.user, pk)
