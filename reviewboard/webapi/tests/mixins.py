from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from django.utils.six.moves import range
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.models import WebAPIToken


class BasicTestsMetaclass(type):
    """Metaclass to automate common tests for resources.

    An API test class can set this as its metaclass in order to automatically
    add common test methods to ensure basic functionality and access control
    works.

    The class must have a ``resource`` attribute pointing to a WebAPIResource
    instance, and ``sample_api_url`` pointing to a sample URL for the API
    that will be used in the test strings.

    The class can also set ``test_http_methods`` to a tuple of HTTP methods
    that should be tested. By default, this includes DELETE, GET, POST
    and PUT.

    By default, tests will also be repeated on Local Sites. This can be
    disabled by setting ``test_local_sites = False``.
    """
    def __new__(meta, name, bases, d):
        test_local_sites = d.get('test_local_sites', True)
        test_api_token_access = d.get('test_api_token_access', True)
        resource = d['resource']
        is_singleton = False
        is_list = False

        if 'test_http_methods' in d:
            test_http_methods = d['test_http_methods']
        else:
            test_http_methods = ('DELETE', 'GET', 'POST', 'PUT')
            d['test_http_methods'] = test_http_methods

        if name == 'ResourceListTests':
            is_list = True
        elif name == 'ResourceTests':
            is_singleton = True

        if 'DELETE' in test_http_methods and not is_list:
            if 'DELETE' not in resource.allowed_methods:
                mixins = (BasicDeleteNotAllowedTestsMixin,)
            elif test_local_sites:
                mixins = (BasicDeleteTestsWithLocalSiteMixin,)

                if test_api_token_access:
                    mixins += (BasicDeleteTestsWithLocalSiteAndAPITokenMixin,)
            else:
                mixins = (BasicDeleteTestsMixin,)

            bases = mixins + bases

        if 'GET' in test_http_methods:
            if is_list:
                if test_local_sites:
                    mixins = (BasicGetListTestsWithLocalSiteMixin,)

                    if test_api_token_access:
                        mixins += (
                            BasicGetListTestsWithLocalSiteAndAPITokenMixin,
                        )
                else:
                    mixins = (BasicGetListTestsMixin,)
            else:
                if test_local_sites:
                    mixins = (BasicGetItemTestsWithLocalSiteMixin,)

                    if test_api_token_access:
                        mixins += (
                          BasicGetItemTestsWithLocalSiteAndAPITokenMixin,
                        )
                else:
                    mixins = (BasicGetItemTestsMixin,)

            bases = mixins + bases

        if 'POST' in test_http_methods and (is_list or is_singleton):
            if 'POST' not in resource.allowed_methods:
                mixins = (BasicPostNotAllowedTestsMixin,)
            elif test_local_sites:
                mixins = (BasicPostTestsWithLocalSiteMixin,)

                if test_api_token_access:
                    mixins += (BasicPostTestsWithLocalSiteAndAPITokenMixin,)
            else:
                mixins = (BasicPostTestsMixin,)

            bases = mixins + bases

        if 'PUT' in test_http_methods and not is_list:
            if 'PUT' not in resource.allowed_methods:
                mixins = (BasicPutNotAllowedTestsMixin,)
            elif test_local_sites:
                mixins = (BasicPutTestsWithLocalSiteMixin,)

                if test_api_token_access:
                    mixins += (BasicPutTestsWithLocalSiteAndAPITokenMixin,)
            else:
                mixins = (BasicPutTestsMixin,)

            bases = mixins + bases

        return super(BasicTestsMetaclass, meta).__new__(meta, name, bases, d)


class BasicTestsMixin(object):
    """Base class for a mixin for basic API tests."""
    def compare_item(self, item_rsp, obj):
        raise NotImplementedError("%s doesn't implement compare_item"
                                  % self.__class__.__name__)

    def _close_file_handles(self, post_data):
        for value in six.itervalues(post_data):
            if isinstance(value, file):
                value.close()

    def _authenticate_basic_tests(self,
                                  with_local_site=False,
                                  with_admin=False,
                                  with_webapi_token=False,
                                  webapi_token_local_site_id=None):
        user = self._login_user(local_site=with_local_site,
                                admin=with_admin)

        if with_webapi_token:
            webapi_token = WebAPIToken.objects.get_or_create(
                user=user,
                token='abc123',
                local_site_id=webapi_token_local_site_id)[0]

            session = self.client.session
            session['webapi_token_id'] = webapi_token.pk
            session.save()

        return user


class BasicDeleteTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP DELETE unit tests.

    The subclass must implement ``setup_basic_delete_test`` and
    ``check_delete_result``.

    It may also set ``basic_delete_fixtures`` to a list of additional
    fixture names to import, and ``basic_delete_use_admin`` to ``True``
    if it wants to run the test as an administrator user.
    """
    basic_delete_fixtures = []
    basic_delete_use_admin = False

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        raise NotImplementedError(
            "%s doesn't implement setup_basic_delete_test"
            % self.__class__.__name__)

    def check_delete_result(self, user, *args):
        raise NotImplementedError("%s doesn't implement check_delete_result"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_delete(self):
        """Testing the DELETE <URL> API"""
        self.load_fixtures(self.basic_delete_fixtures)
        self._login_user(admin=self.basic_delete_use_admin)

        url, cb_args = self.setup_basic_delete_test(self.user, False, None)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        self.api_delete(url)
        self.check_delete_result(self.user, *cb_args)

    @webapi_test_template
    def test_delete_not_owner(self):
        """Testing the DELETE <URL> API without owner"""
        self.load_fixtures(self.basic_delete_fixtures)

        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        url, cb_args = self.setup_basic_delete_test(user, False, None)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.api_delete(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicDeleteTestsWithLocalSiteMixin(BasicDeleteTestsMixin):
    """Adds basic HTTP DELETE unit tests with Local Sites.

    This extends BasicDeleteTestsMixin to also perform equivalent tests
    on Local Sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_site(self):
        """Testing the DELETE <URL> API with access to a local site"""
        user, url, cb_args = self._setup_test_delete_with_site()

        self.api_delete(url)
        self.check_delete_result(user, *cb_args)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_site_no_access(self):
        """Testing the DELETE <URL> API without access to a local site"""
        user, url, cb_args = self._setup_test_delete_with_site()

        self._login_user()

        rsp = self.api_delete(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _setup_test_delete_with_site(self, **auth_kwargs):
        self.load_fixtures(self.basic_delete_fixtures)

        user = self._authenticate_basic_tests(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin,
            **auth_kwargs)

        url, cb_args = self.setup_basic_delete_test(user, True,
                                                    self.local_site_name)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        return user, url, cb_args


class BasicDeleteTestsWithLocalSiteAndAPITokenMixin(object):
    """Adds basic HTTP DELETE unit tests with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_restrict_site_and_allowed(self):
        """Testing the DELETE <URL> API with access to a local site
        and session restricted to the site
        """
        user, url, cb_args = self._setup_test_delete_with_site(
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)

        self.api_delete(url)
        self.check_delete_result(user, *cb_args)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_restrict_site_and_not_allowed(self):
        """Testing the DELETE <URL> API with access to a local site
        and session restricted to a different site
        """
        user, url, cb_args = self._setup_test_delete_with_site(
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)

        rsp = self.api_delete(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicDeleteNotAllowedTestsMixin(BasicTestsMixin):
    """Mixin to add HTTP 405 Not Allowed tests for HTTP DELETE.

    The subclass must implement ``setup_http_not_allowed_item_test``,
    which will be reused for all HTTP 405 Not Allowed tests on the
    class.
    """
    def setup_http_not_allowed_item_test(self, user):
        raise NotImplementedError(
            "%s doesn't implement setup_http_not_allowed_item_test"
            % self.__class__.__name__)

    @webapi_test_template
    def test_delete_method_not_allowed(self):
        """Testing the DELETE <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_item_test(self.user)

        self.api_delete(url, expected_status=405)


class BasicGetItemTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP GET unit tests for item resources.

    The subclass must implement ``setup_basic_get_test``.

    It may also set ``basic_get_fixtures`` to a list of additional
    fixture names to import.
    """
    basic_get_fixtures = []
    basic_get_returns_json = True
    basic_get_use_admin = False

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        raise NotImplementedError("%s doesn't implement setup_basic_get_test"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_get(self):
        """Testing the GET <URL> API"""
        self.load_fixtures(self.basic_get_fixtures)
        self._login_user(admin=self.basic_get_use_admin)

        url, mimetype, item = self.setup_basic_get_test(self.user, False, None)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.api_get(url,
                           expected_mimetype=mimetype,
                           expected_json=self.basic_get_returns_json)

        if self.basic_get_returns_json:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(self.resource.item_result_key, rsp)

            item_rsp = rsp[self.resource.item_result_key]
            self.compare_item(item_rsp, item)
        else:
            self.compare_item(rsp, item)


class BasicGetItemTestsWithLocalSiteMixin(BasicGetItemTestsMixin):
    """Adds basic HTTP GET unit tests for item resources with Local Sites.

    This extends BasicGetItemTestsMixin to also perform equivalent tests
    on Local Sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site(self):
        """Testing the GET <URL> API with access to a local site"""
        user, url, mimetype, item = self._setup_test_get_with_site()

        rsp = self.api_get(url,
                           expected_mimetype=mimetype,
                           expected_json=self.basic_get_returns_json)

        if self.basic_get_returns_json:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(self.resource.item_result_key, rsp)

            item_rsp = rsp[self.resource.item_result_key]
            self.compare_item(item_rsp, item)
        else:
            self.compare_item(rsp, item)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site_no_access(self):
        """Testing the GET <URL> API without access to a local site"""
        user, url, mimetype, item = self._setup_test_get_with_site()

        self._login_user()

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _setup_test_get_with_site(self, **auth_kwargs):
        self.load_fixtures(self.basic_get_fixtures)

        user = self._authenticate_basic_tests(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            **auth_kwargs)

        url, mimetype, item = \
            self.setup_basic_get_test(user, True, self.local_site_name)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        return user, url, mimetype, item


class BasicGetItemTestsWithLocalSiteAndAPITokenMixin(object):
    """Adds HTTP GET tests for item resources with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_allowed(self):
        """Testing the GET <URL> API with access to a local site
        and session restricted to the site
        """
        user, url, mimetype, item = self._setup_test_get_with_site(
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)

        rsp = self.api_get(url, expected_mimetype=mimetype,
                           expected_json=self.basic_get_returns_json)

        if self.basic_get_returns_json:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(self.resource.item_result_key, rsp)

            item_rsp = rsp[self.resource.item_result_key]
            self.compare_item(item_rsp, item)
        else:
            self.compare_item(rsp, item)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_not_allowed(self):
        """Testing the GET <URL> API with access to a local site
        and session restricted to a different site
        """
        user, url, mimetype, item = self._setup_test_get_with_site(
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicGetListTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP GET unit tests for list resources.

    The subclass must implement ``setup_basic_get_test``.

    It may also set ``basic_get_fixtures`` to a list of additional
    fixture names to import.
    """
    basic_get_fixtures = []
    basic_get_use_admin = False

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        raise NotImplementedError("%s doesn't implement setup_basic_get_test"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_get(self):
        """Testing the GET <URL> API"""
        self.load_fixtures(self.basic_get_fixtures)
        self._login_user(admin=self.basic_get_use_admin)

        url, mimetype, items = self.setup_basic_get_test(self.user, False,
                                                         None, True)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.api_get(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.list_result_key, rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])


class BasicGetListTestsWithLocalSiteMixin(BasicGetListTestsMixin):
    """Adds basic HTTP GET unit tests for list resources with Local Sites.

    This extends BasicGetListTestsMixin to also perform equivalent tests
    on Local Sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site(self):
        """Testing the GET <URL> API with access to a local site"""
        user, url, mimetype, items = self._setup_test_get_list_with_site()

        rsp = self.api_get(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.list_result_key, rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site_no_access(self):
        """Testing the GET <URL> API without access to a local site"""
        user, url, mimetype, items = self._setup_test_get_list_with_site()

        self._login_user()

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _setup_test_get_list_with_site(self, **auth_kwargs):
        self.load_fixtures(self.basic_get_fixtures)

        user = self._authenticate_basic_tests(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            **auth_kwargs)

        url, mimetype, items = self.setup_basic_get_test(user, True,
                                                         self.local_site_name,
                                                         True)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        return user, url, mimetype, items


class BasicGetListTestsWithLocalSiteAndAPITokenMixin(object):
    """Adds HTTP GET tests for lists with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_allowed(self):
        """Testing the GET <URL> API with access to a local site
        and session restricted to the site
        """
        user, url, mimetype, items = self._setup_test_get_list_with_site(
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)

        rsp = self.api_get(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.list_result_key, rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_not_allowed(self):
        """Testing the GET <URL> API with access to a local site
        and session restricted to a different site
        """
        user, url, mimetype, items = self._setup_test_get_list_with_site(
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPostTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP POST unit tests.

    The subclass must implement ``setup_basic_post_test`` and
    ``check_post_result``.

    It may also set ``basic_post_fixtures`` to a list of additional
    fixture names to import, and ``basic_post_use_admin`` to ``True``
    if it wants to run the test as an administrator user.
    """
    basic_post_fixtures = []
    basic_post_use_admin = False

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        raise NotImplementedError("%s doesn't implement setup_basic_post_test"
                                  % self.__class__.__name__)

    def check_post_result(self, user, rsp, *args):
        raise NotImplementedError("%s doesn't implement check_post_result"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_post(self):
        """Testing the POST <URL> API"""
        self.load_fixtures(self.basic_post_fixtures)
        self._login_user(admin=self.basic_post_use_admin)

        url, mimetype, post_data, cb_args = \
            self.setup_basic_post_test(self.user, False, None, True)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.api_post(url, post_data, expected_mimetype=mimetype)
        self._close_file_handles(post_data)
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(self.user, rsp, *cb_args)


class BasicPostTestsWithLocalSiteMixin(BasicPostTestsMixin):
    """Adds basic HTTP POST unit tests with Local Sites.

    This extends BasicPostTestsMixin to also perform equivalent tests
    on Local Sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site(self):
        """Testing the POST <URL> API with access to a local site"""
        user, url, mimetype, post_data, cb_args = \
            self._setup_test_post_with_site()

        rsp = self.api_post(url, post_data, expected_mimetype=mimetype)
        self._close_file_handles(post_data)
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(user, rsp, *cb_args)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site_no_access(self):
        """Testing the POST <URL> API without access to a local site"""
        user, url, mimetype, post_data, cb_args = \
            self._setup_test_post_with_site()

        self._login_user()

        rsp = self.api_post(url, post_data, expected_status=403)
        self._close_file_handles(post_data)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _setup_test_post_with_site(self, **auth_kwargs):
        self.load_fixtures(self.basic_post_fixtures)

        user = self._authenticate_basic_tests(
            with_local_site=True,
            with_admin=self.basic_post_use_admin,
            **auth_kwargs)

        url, mimetype, post_data, cb_args = \
            self.setup_basic_post_test(user, True, self.local_site_name, True)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        return user, url, mimetype, post_data, cb_args


class BasicPostTestsWithLocalSiteAndAPITokenMixin(object):
    """Adds HTTP POST tests with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_restrict_site_and_allowed(self):
        """Testing the POST <URL> API with access to a local site
        and session restricted to the site
        """
        user, url, mimetype, post_data, cb_args = \
            self._setup_test_post_with_site(
                with_webapi_token=True,
                webapi_token_local_site_id=self.local_site_id)

        rsp = self.api_post(url, post_data, expected_mimetype=mimetype)
        self._close_file_handles(post_data)
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(user, rsp, *cb_args)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_restrict_site_and_not_allowed(self):
        """Testing the POST <URL> API with access to a local site
        and session restricted to a different site
        """
        user, url, mimetype, post_data, cb_args = \
            self._setup_test_post_with_site(
                with_webapi_token=True,
                webapi_token_local_site_id=self.local_site_id + 1)

        rsp = self.api_post(url, post_data, expected_status=403)
        self._close_file_handles(post_data)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPostNotAllowedTestsMixin(BasicTestsMixin):
    """Mixin to add HTTP 405 Not Allowed tests for HTTP POST.

    The subclass must implement ``setup_http_not_allowed_list_test``.
    """
    def setup_http_not_allowed_list_test(self, user):
        raise NotImplementedError(
            "%s doesn't implement setup_http_not_allowed_list_test"
            % self.__class__.__name__)

    @webapi_test_template
    def test_post_method_not_allowed(self):
        """Testing the POST <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_list_test(self.user)

        self.api_post(url, {}, expected_status=405)


class BasicPutTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP PUT unit tests.

    The subclass must implement ``setup_basic_put_test`` and
    ``check_put_result``.

    It may also set ``basic_put_fixtures`` to a list of additional
    fixture names to import, and ``basic_put_use_admin`` to ``True``
    if it wants to run the test as an administrator user.
    """
    basic_put_fixtures = []
    basic_put_use_admin = False

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        raise NotImplementedError("%s doesn't implement setup_basic_put_test"
                                  % self.__class__.__name__)

    def check_put_result(self, user, item_rsp, item, *args):
        raise NotImplementedError("%s doesn't implement check_put_result"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_put(self):
        """Testing the PUT <URL> API"""
        self.load_fixtures(self.basic_put_fixtures)
        self._login_user(admin=self.basic_put_use_admin)

        url, mimetype, put_data, item, cb_args = \
            self.setup_basic_put_test(self.user, False, None, True)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.api_put(url, put_data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        self.check_put_result(self.user, rsp[self.resource.item_result_key],
                              item, *cb_args)

    @webapi_test_template
    def test_put_not_owner(self):
        """Testing the PUT <URL> API without owner"""
        self.load_fixtures(self.basic_put_fixtures)

        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        url, mimetype, put_data, item, cb_args = \
            self.setup_basic_put_test(user, False, None, False)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.api_put(url, put_data, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPutTestsWithLocalSiteMixin(BasicPutTestsMixin):
    """Adds basic HTTP PUT unit tests with Local Sites.

    This extends BasicPutTestsMixin to also perform equivalent tests
    on Local Sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_site(self):
        """Testing the PUT <URL> API with access to a local site"""
        user, url, mimetype, put_data, item, cb_args = \
            self._setup_test_put_with_site()

        rsp = self.api_put(url, put_data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        self.check_put_result(user, rsp[self.resource.item_result_key],
                              item, *cb_args)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_site_no_access(self):
        """Testing the PUT <URL> API without access to a local site"""
        user, url, mimetype, put_data, item, cb_args = \
            self._setup_test_put_with_site()

        self._login_user()

        rsp = self.api_put(url, put_data, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _setup_test_put_with_site(self, **auth_kwargs):
        self.load_fixtures(self.basic_put_fixtures)

        user = self._authenticate_basic_tests(
            with_local_site=True,
            with_admin=self.basic_put_use_admin,
            **auth_kwargs)

        url, mimetype, put_data, item, cb_args = \
            self.setup_basic_put_test(user, True, self.local_site_name, True)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        return user, url, mimetype, put_data, item, cb_args


class BasicPutTestsWithLocalSiteAndAPITokenMixin(object):
    """Adds HTTP PUT tests with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """
    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_restrict_site_and_allowed(self):
        """Testing the PUT <URL> API with access to a local site
        and session restricted to the site
        """
        user, url, mimetype, put_data, item, cb_args = \
            self._setup_test_put_with_site(
                with_webapi_token=True,
                webapi_token_local_site_id=self.local_site_id)

        rsp = self.api_put(url, put_data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        self.check_put_result(user, rsp[self.resource.item_result_key],
                              item, *cb_args)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_restrict_site_and_not_allowed(self):
        """Testing the PUT <URL> API with access to a local site
        and session restricted to a different site
        """
        user, url, mimetype, put_data, item, cb_args = \
            self._setup_test_put_with_site(
                with_webapi_token=True,
                webapi_token_local_site_id=self.local_site_id + 1)

        rsp = self.api_put(url, put_data, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPutNotAllowedTestsMixin(BasicTestsMixin):
    """Mixin to add HTTP 405 Not Allowed tests for HTTP PUT.

    The subclass must implement ``setup_http_not_allowed_item_test``,
    which will be reused for all HTTP 405 Not Allowed tests on the
    class.
    """
    def setup_http_not_allowed_item_test(self, user):
        raise NotImplementedError(
            "%s doesn't implement setup_http_not_allowed_item_test"
            % self.__class__.__name__)

    @webapi_test_template
    def test_put_method_not_allowed(self):
        """Testing the PUT <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_item_test(self.user)

        self.api_put(url, {}, expected_status=405)


class BaseReviewRequestChildMixin(object):
    """Base class for tests for children of ReviewRequestResource.

    This will test that the resources are only accessible when the user has
    access to the review request itself (such as when the review request
    is private due to being in an invite-only repository or group).

    This applies to immediate children and any further down the tree.
    """
    basic_get_returns_json = True

    def setup_review_request_child_test(self, review_request):
        raise NotImplementedError(
            "%s doesn't implement setup_review_request_child_test"
            % self.__class__.__name__)

    @webapi_test_template
    def test_get_with_private_group(self):
        """Testing the GET <URL> API
        with access to review request on a private group
        """
        group = self.create_review_group(invite_only=True)
        group.users.add(self.user)
        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        url, mimetype = self.setup_review_request_child_test(review_request)

        self.api_get(url,
                     expected_mimetype=mimetype,
                     expected_json=self.basic_get_returns_json)

    @webapi_test_template
    def test_get_with_private_group_no_access(self):
        """Testing the GET <URL> API
        without access to review request on a private group
        """
        group = self.create_review_group(invite_only=True)
        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        url, mimetype = self.setup_review_request_child_test(review_request)

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_private_repo(self):
        """Testing the GET <URL> API
        with access to review request on a private repository
        """
        repository = self.create_repository(public=False, tool_name='Test')
        repository.users.add(self.user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        url, mimetype = self.setup_review_request_child_test(review_request)

        self.api_get(url,
                     expected_mimetype=mimetype,
                     expected_json=self.basic_get_returns_json)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_private_repo_no_access(self):
        """Testing the GET <URL> API
        without access to review request on a private repository
        """
        repository = self.create_repository(public=False, tool_name='Test')
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        url, mimetype = self.setup_review_request_child_test(review_request)

        rsp = self.api_get(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ReviewRequestChildListMixin(BaseReviewRequestChildMixin):
    """Tests for list resources that are children of ReviewRequestResource."""


class ReviewRequestChildItemMixin(BaseReviewRequestChildMixin):
    """Tests for item resources that are children of ReviewRequestResource."""
