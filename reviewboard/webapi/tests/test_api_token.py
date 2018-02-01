from __future__ import unicode_literals

from django.utils import six
from djblets.db.query import get_object_or_none
from djblets.webapi.errors import PERMISSION_DENIED
from kgb import SpyAgency

from reviewboard.site.models import LocalSite
from reviewboard.webapi.errors import TOKEN_GENERATION_FAILED
from reviewboard.webapi.models import WebAPIToken
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (api_token_item_mimetype,
                                                api_token_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_api_token_item_url,
                                           get_api_token_list_url)


def _compare_item(self, item_rsp, api_token):
    self.assertEqual(item_rsp['id'], api_token.pk)
    self.assertEqual(item_rsp['token'], api_token.token)
    self.assertEqual(item_rsp['note'], api_token.note)
    self.assertEqual(item_rsp['policy'], api_token.policy)
    self.assertEqual(item_rsp['extra_data'], api_token.extra_data)


class APITokenTestsMixin(object):
    token_data = {
        'note': 'This is my new token.',
        'policy': '{"perms": "ro", "resources": {"*": {"allow": ["*"]}}}',
    }


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(SpyAgency, ExtraDataListMixin, BaseWebAPITestCase,
                        APITokenTestsMixin):
    """Testing the APITokenResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'users/<username>/api-tokens/'
    resource = resources.api_token
    test_api_token_access = False
    test_oauth_token_access = False

    compare_item = _compare_item

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            if not with_local_site:
                LocalSite.objects.create(name=self.local_site_name)

            # Due to running this test with a WebAPIToken, we may
            # already have one in the database we need to include.
            items = list(user.webapi_tokens.all())
            items.append(self.create_webapi_token(
                user, note='Token 1', with_local_site=with_local_site))

            self.create_webapi_token(user, note='Token 2',
                                     with_local_site=not with_local_site)
        else:
            items = []

        return (get_api_token_list_url(user, local_site_name),
                api_token_list_mimetype,
                items)

    def test_get_with_api_token_auth_denied(self):
        """Testing the GET users/<username>/api-tokens/ API denies access
        when using token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_get_test(user, False, None, True)[0]

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        if post_valid_data:
            post_data = self.token_data.copy()
        else:
            post_data = {}

        return (get_api_token_list_url(user, local_site_name),
                api_token_item_mimetype,
                post_data,
                [local_site_name])

    def check_post_result(self, user, rsp, local_site_name):
        token_rsp = rsp['api_token']
        token = WebAPIToken.objects.get(pk=token_rsp['id'])

        self.compare_item(token_rsp, token)

        if local_site_name:
            self.assertIsNotNone(token.local_site_id)
            self.assertEqual(token.local_site.name, local_site_name)
        else:
            self.assertIsNone(token.local_site_id)

    def test_post_with_generation_error(self):
        """Testing the POST users/<username>/api-tokens/ API
        with Token Generation Failed error"""
        def _generate_token(self, *args, **kwargs):
            kwargs['max_attempts'] = 0
            orig_generate_token(*args, **kwargs)

        orig_generate_token = WebAPIToken.objects.generate_token

        self.spy_on(WebAPIToken.objects.generate_token,
                    call_fake=_generate_token)

        rsp = self.api_post(get_api_token_list_url(self.user),
                            self.token_data,
                            expected_status=500)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], TOKEN_GENERATION_FAILED.code)
        self.assertEqual(rsp['err']['msg'],
                         'Could not create a unique API token. '
                         'Please try again.')

    def test_post_with_api_token_auth_denied(self):
        """Testing the POST users/<username>/api-tokens/ API denies access
        when using token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_post_test(user, False, None, True)[0]

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, BaseWebAPITestCase,
                        APITokenTestsMixin):
    """Testing the APITokenResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'users/<username>/api-tokens/<id>/'
    resource = resources.api_token
    test_api_token_access = False
    test_oauth_token_access = False

    compare_item = _compare_item

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        token = self.create_webapi_token(user, with_local_site=with_local_site)

        return (get_api_token_item_url(token, local_site_name),
                [token.pk])

    def check_delete_result(self, user, token_id):
        self.assertIsNone(get_object_or_none(WebAPIToken, pk=token_id))

    def test_delete_with_api_token_auth_denied(self):
        """Testing the DELETE users/<username>/api-tokens/<id>/ API denies
        access when using token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_delete_test(user, False, None)[0]

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        token = self.create_webapi_token(user, with_local_site=with_local_site)

        return (get_api_token_item_url(token, local_site_name),
                api_token_item_mimetype,
                token)

    def test_get_not_modified(self):
        """Testing the GET users/<username>/api-tokens/<id>/ API
        with Not Modified response
        """
        token = self.create_webapi_token(self.user)

        self._testHttpCaching(get_api_token_item_url(token),
                              check_last_modified=True)

    def test_get_with_api_token_auth_denied(self):
        """Testing the GET users/<username>/api-tokens/<id>/ API denies access
        when using token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_get_test(user, False, None)[0]

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        token = self.create_webapi_token(user, with_local_site=with_local_site)

        return (get_api_token_item_url(token, local_site_name),
                api_token_item_mimetype,
                self.token_data.copy(),
                token,
                [])

    def check_put_result(self, user, item_rsp, token):
        self.compare_item(item_rsp, WebAPIToken.objects.get(pk=token.pk))

    def test_put_with_api_token_auth_denied(self):
        """Testing the PUT users/<username>/api-tokens/<id>/ API denies access
        when using token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_put_test(user, False, None, True)[0]

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
