from datetime import datetime, timedelta

from django.utils import timezone
from djblets.db.query import get_object_or_none
from djblets.webapi.errors import (INVALID_FORM_DATA,
                                   PERMISSION_DENIED)
from djblets.webapi.testing.decorators import webapi_test_template
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
    if api_token.last_used:
        expected_last_used = api_token.last_used.isoformat()
    else:
        expected_last_used = None

    if api_token.expires:
        expected_expires = api_token.expires.isoformat()
    else:
        expected_expires = None

    if api_token.invalid_date:
        expected_invalid_date = api_token.invalid_date.isoformat()
    else:
        expected_invalid_date = None

    self.assertEqual(item_rsp['id'], api_token.pk)
    self.assertEqual(item_rsp['token'], api_token.token)
    self.assertEqual(item_rsp['token_generator_id'],
                     api_token.token_generator_id)
    self.assertEqual(item_rsp['note'], api_token.note)
    self.assertEqual(item_rsp['policy'], api_token.policy)
    self.assertEqual(item_rsp['extra_data'], api_token.extra_data)
    self.assertEqual(item_rsp['time_added'], api_token.time_added.isoformat())
    self.assertEqual(item_rsp['last_updated'],
                     api_token.last_updated.isoformat())
    self.assertEqual(item_rsp['last_used'], expected_last_used)
    self.assertEqual(item_rsp['expires'], expected_expires)
    self.assertEqual(item_rsp['valid'], api_token.valid)
    self.assertEqual(item_rsp['invalid_date'], expected_invalid_date)
    self.assertEqual(item_rsp['invalid_reason'], api_token.invalid_reason)


class APITokenTestsMixin(object):
    token_data = {
        'note': 'This is my new token.',
        'policy': '{"perms": "ro", "resources": {"*": {"allow": ["*"]}}}',
    }


class ResourceListTests(SpyAgency, ExtraDataListMixin, BaseWebAPITestCase,
                        APITokenTestsMixin, metaclass=BasicTestsMetaclass):
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

    @webapi_test_template
    def test_get_with_api_token_auth_denied(self):
        """Testing the GET <URL> API denies access when using
        token-based authentication
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

    @webapi_test_template
    def test_post_with_generation_error(self):
        """Testing the POST <URL> API with Token Generation Failed error"""
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

    @webapi_test_template
    def test_post_with_api_token_auth_denied(self):
        """Testing the POST <URL> API denies access when using
        token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_post_test(user, False, None, True)[0]

        rsp = self.api_post(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @webapi_test_template
    def test_post_with_expires_field_utc_timezone(self):
        """Testing the POST <URL> API with setting an ISO 8601
        timestamp with UTC timezone for the expiration date
        """
        expires = datetime(2022, 9, 20, 13, 42, 0,
                           tzinfo=timezone.utc).isoformat()
        token_data = self.token_data.copy()
        token_data['expires'] = expires

        rsp = self.api_post(get_api_token_list_url(self.user),
                            token_data,
                            expected_mimetype=api_token_item_mimetype,
                            expected_status=201)

        token = WebAPIToken.objects.get(pk=rsp['api_token']['id'])

        self.assertEqual(token.expires.isoformat(),
                         '2022-09-20T13:42:00+00:00')
        self.check_post_result(self.user, rsp, None)

    @webapi_test_template
    def test_post_with_expires_field_non_utc_timezone(self):
        """Testing the POST <URL> API with setting an ISO 8601
        timestamp with a non-UTC timezone for the expiration date
        """
        expires = datetime(
            2022, 9, 20, 13, 42, 0,
            tzinfo=timezone.get_fixed_timezone(timedelta(hours=5)))
        utc_expires = '2022-09-20T08:42:00+00:00'

        token_data = self.token_data.copy()
        token_data['expires'] = expires.isoformat()

        rsp = self.api_post(get_api_token_list_url(self.user),
                            token_data,
                            expected_mimetype=api_token_item_mimetype,
                            expected_status=201)

        # Compare against the UTC time since dates are stored in UTC.
        rsp['api_token']['expires'] = utc_expires

        token = WebAPIToken.objects.get(pk=rsp['api_token']['id'])

        self.assertEqual(token.expires.isoformat(), utc_expires)
        self.check_post_result(self.user, rsp, None)

    @webapi_test_template
    def test_post_with_expires_field_no_timezone(self):
        """Testing the POST <URL> API with setting an ISO 8601
        timestamp with no timezone specified for the expiration date
        """
        # When no timezone is specified, the user's profile's timezone
        # will be used.
        profile = self.user.get_profile()
        profile.timezone = 'US/Eastern'
        profile.save(update_fields=('timezone',))

        expires = datetime(2022, 9, 20, 13, 42, 0)
        utc_expires = '2022-09-20T17:42:00+00:00'

        token_data = self.token_data.copy()
        token_data['expires'] = expires.isoformat()

        rsp = self.api_post(get_api_token_list_url(self.user),
                            token_data,
                            expected_mimetype=api_token_item_mimetype,
                            expected_status=201)

        # Compare against the UTC time since dates are stored in UTC.
        rsp['api_token']['expires'] = utc_expires

        token = WebAPIToken.objects.get(pk=rsp['api_token']['id'])

        self.assertEqual(token.expires.isoformat(), utc_expires)
        self.check_post_result(self.user, rsp, None)

    @webapi_test_template
    def test_post_with_expires_field_empty(self):
        """Testing the POST <URL> API with setting an empty expiration
        date for the token
        """
        token_data = self.token_data.copy()
        token_data['expires'] = ''

        rsp = self.api_post(get_api_token_list_url(self.user),
                            token_data,
                            expected_mimetype=api_token_item_mimetype,
                            expected_status=201)

        self.check_post_result(self.user, rsp, None)


class ResourceItemTests(ExtraDataItemMixin, BaseWebAPITestCase,
                        APITokenTestsMixin, metaclass=BasicTestsMetaclass):
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

    @webapi_test_template
    def test_delete_with_api_token_auth_denied(self):
        """Testing the DELETE <URL> API denies access when
        using token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_delete_test(user, False, None)[0]

        rsp = self.api_delete(url, expected_status=403)
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

    @webapi_test_template
    def test_get_not_modified(self):
        """Testing the GET <URL> API with Not Modified response"""
        token = self.create_webapi_token(self.user)

        self._testHttpCaching(get_api_token_item_url(token),
                              check_last_modified=True)

    @webapi_test_template
    def test_get_with_api_token_auth_denied(self):
        """Testing the GET <URL> API denies access when using
        token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_get_test(user, False, None)[0]

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP PUT tests
    #

    @webapi_test_template
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

    @webapi_test_template
    def test_put_with_api_token_auth_denied(self):
        """Testing the PUT <URL> API denies access when using
        token-based authentication
        """
        user = self._authenticate_basic_tests(with_webapi_token=True)
        url = self.setup_basic_put_test(user, False, None, True)[0]

        rsp = self.api_put(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @webapi_test_template
    def test_put_with_invalidation(self):
        """Testing the PUT <URL> API with invalidating a token"""
        token = self.create_webapi_token(self.user)
        url = get_api_token_item_url(token)

        # Testing that the token can be invalidated.
        rsp = self.api_put(
            url,
            {
                'valid': 0,
                'invalid_reason': 'test reason',
            },
            expected_mimetype=api_token_item_mimetype,
            expected_status=200)

        self.check_put_result(self.user, rsp['api_token'], token)

        # Testing that the token cannot be updated to be valid.
        rsp = self.api_put(url,
                           {'valid': 1},
                           expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)

    @webapi_test_template
    def test_put_with_expires_field_utc_timezone(self):
        """Testing the PUT <URL> API with setting an ISO 8601
        timestamp with UTC timezone for the expiration date
        """
        token = self.create_webapi_token(self.user)
        expires = datetime(2022, 9, 20, 13, 42, 0,
                           tzinfo=timezone.utc).isoformat()

        token_data = self.token_data.copy()
        token_data['expires'] = expires

        rsp = self.api_put(get_api_token_item_url(token),
                           token_data,
                           expected_mimetype=api_token_item_mimetype,
                           expected_status=200)

        token.refresh_from_db()

        self.assertEqual(token.expires.isoformat(),
                         '2022-09-20T13:42:00+00:00')
        self.check_put_result(self.user, rsp['api_token'], token)

    @webapi_test_template
    def test_put_with_expires_field_non_utc_timezone(self):
        """Testing the PUT <URL> API with setting an ISO 8601
        timestamp with a non-UTC timezone for the expiration date
        """
        token = self.create_webapi_token(self.user)

        expires = datetime(
            2022, 9, 20, 13, 42, 0,
            tzinfo=timezone.get_fixed_timezone(timedelta(hours=5)))
        utc_expires = '2022-09-20T08:42:00+00:00'

        token_data = self.token_data.copy()
        token_data['expires'] = expires.isoformat()

        rsp = self.api_put(get_api_token_item_url(token),
                           token_data,
                           expected_mimetype=api_token_item_mimetype,
                           expected_status=200)

        # Compare against the UTC time since dates are stored in UTC.
        rsp['api_token']['expires'] = utc_expires

        token.refresh_from_db()

        self.assertEqual(token.expires.isoformat(), utc_expires)
        self.check_put_result(self.user, rsp['api_token'], token)

    @webapi_test_template
    def test_put_with_expires_field_no_timezone(self):
        """Testing the PUT <URL> API with setting an ISO 8601
        timestamp with no timezone specified for the expiration date
        """
        # When no timezone is specified, the user's profile's timezone
        # will be used.
        profile = self.user.get_profile()
        profile.timezone = 'US/Eastern'
        profile.save(update_fields=('timezone',))

        token = self.create_webapi_token(self.user)

        expires = datetime(2022, 9, 20, 13, 42, 0)
        utc_expires = '2022-09-20T17:42:00+00:00'

        token_data = self.token_data.copy()
        token_data['expires'] = expires.isoformat()

        rsp = self.api_put(get_api_token_item_url(token),
                           token_data,
                           expected_mimetype=api_token_item_mimetype,
                           expected_status=200)

        # Compare against the UTC time since dates are stored in UTC.
        rsp['api_token']['expires'] = utc_expires

        token.refresh_from_db()

        self.assertEqual(token.expires.isoformat(), utc_expires)
        self.check_put_result(self.user, rsp['api_token'], token)

    @webapi_test_template
    def test_put_with_expires_field_empty(self):
        """Testing the PUT <URL> API with setting an empty expiration
        date for the token
        """
        token = self.create_webapi_token(self.user)
        url = get_api_token_item_url(token)

        token_data = self.token_data.copy()
        token_data['expires'] = ''

        rsp = self.api_put(url,
                           token_data,
                           expected_mimetype=api_token_item_mimetype,
                           expected_status=200)

        self.check_put_result(self.user, rsp['api_token'], token)
