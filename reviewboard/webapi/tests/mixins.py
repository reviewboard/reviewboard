from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.util.compat import six
from djblets.util.compat.six.moves import range
from djblets.util.decorators import simple_decorator
from djblets.webapi.errors import PERMISSION_DENIED


@simple_decorator
def test_template(test_func):
    """Marks this test function as a template for tests.

    This adds a flag to the test function hinting that it should be
    processed differently. WebAPITestCase will replace the docstring to
    match that of the active test suite.
    """
    def _call(*args, **kwargs):
        return test_func(*args, **kwargs)

    _call.is_test_template = True

    return _call


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
    """
    def __new__(meta, name, bases, d):
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
            if 'DELETE' in resource.allowed_methods:
                bases = (BasicDeleteTestsMixin,) + bases
            else:
                bases = (BasicDeleteNotAllowedTestsMixin,) + bases

        if 'GET' in test_http_methods:
            if is_list:
                bases = (BasicGetListTestsMixin,) + bases
            else:
                bases = (BasicGetItemTestsMixin,) + bases

        if 'POST' in test_http_methods and (is_list or is_singleton):
            if 'POST' in resource.allowed_methods:
                bases = (BasicPostTestsMixin,) + bases
            else:
                bases = (BasicPostNotAllowedTestsMixin,) + bases

        if 'PUT' in test_http_methods and not is_list:
            if 'PUT' in resource.allowed_methods:
                bases = (BasicPutTestsMixin,) + bases
            else:
                bases = (BasicPutNotAllowedTestsMixin,) + bases

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

    @test_template
    def test_delete(self):
        """Testing the DELETE <URL> API"""
        self.load_fixtures(self.basic_delete_fixtures)
        self._login_user(admin=self.basic_delete_use_admin)

        url, cb_args = self.setup_basic_delete_test(self.user, False, None)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        self.apiDelete(url)
        self.check_delete_result(self.user, *cb_args)

    @add_fixtures(['test_site'])
    @test_template
    def test_delete_with_site(self):
        """Testing the DELETE <URL> API with access to a local site"""
        self.load_fixtures(self.basic_delete_fixtures)

        user = self._login_user(local_site=True,
                                admin=self.basic_delete_use_admin)
        url, cb_args = self.setup_basic_delete_test(user, True,
                                                    self.local_site_name)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        self.apiDelete(url)
        self.check_delete_result(user, *cb_args)

    @add_fixtures(['test_site'])
    @test_template
    def test_delete_with_site_no_access(self):
        """Testing the DELETE <URL> API without access to a local site"""
        self.load_fixtures(self.basic_delete_fixtures)

        user = self._login_user(local_site=True,
                                admin=self.basic_delete_use_admin)
        url, cb_args = self.setup_basic_delete_test(user, True,
                                                    self.local_site_name)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        user = self._login_user()
        rsp = self.apiDelete(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @test_template
    def test_delete_not_owner(self):
        """Testing the DELETE <URL> API without owner"""
        self.load_fixtures(self.basic_delete_fixtures)

        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        url, cb_args = self.setup_basic_delete_test(user, False, None)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiDelete(url, expected_status=403)
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

    @test_template
    def test_delete_method_not_allowed(self):
        """Testing the DELETE <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_item_test(self.user)

        self.apiDelete(url, expected_status=405)


class BasicGetItemTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP GET unit tests for item resources.

    The subclass must implement ``setup_basic_get_test``.

    It may also set ``basic_get_fixtures`` to a list of additional
    fixture names to import.
    """
    basic_get_fixtures = []

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        raise NotImplementedError("%s doesn't implement setup_basic_get_test"
                                  % self.__class__.__name__)

    @test_template
    def test_get(self):
        """Testing the GET <URL> API"""
        self.load_fixtures(self.basic_get_fixtures)

        url, mimetype, item = self.setup_basic_get_test(self.user, False, None)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiGet(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        item_rsp = rsp[self.resource.item_result_key]
        self.compare_item(item_rsp, item)

    @add_fixtures(['test_site'])
    @test_template
    def test_get_with_site(self):
        """Testing the GET <URL> API with access to a local site"""
        self.load_fixtures(self.basic_get_fixtures)

        user = self._login_user(local_site=True)
        url, mimetype, item = \
            self.setup_basic_get_test(user, True, self.local_site_name)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiGet(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        item_rsp = rsp[self.resource.item_result_key]
        self.compare_item(item_rsp, item)

    @add_fixtures(['test_site'])
    @test_template
    def test_get_with_site_no_access(self):
        """Testing the GET <URL> API without access to a local site"""
        self.load_fixtures(self.basic_get_fixtures)

        url, mimetype, item = \
            self.setup_basic_get_test(self.user, True, self.local_site_name)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiGet(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicGetListTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP GET unit tests for list resources.

    The subclass must implement ``setup_basic_get_test``.

    It may also set ``basic_get_fixtures`` to a list of additional
    fixture names to import.
    """
    basic_get_fixtures = []

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        raise NotImplementedError("%s doesn't implement setup_basic_get_test"
                                  % self.__class__.__name__)

    @test_template
    def test_get(self):
        """Testing the GET <URL> API"""
        self.load_fixtures(self.basic_get_fixtures)

        url, mimetype, items = self.setup_basic_get_test(self.user, False,
                                                         None, True)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiGet(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.list_result_key in rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    @add_fixtures(['test_site'])
    @test_template
    def test_get_with_site(self):
        """Testing the GET <URL> API with access to a local site"""
        self.load_fixtures(self.basic_get_fixtures)

        user = self._login_user(local_site=True)
        url, mimetype, items = self.setup_basic_get_test(user, True,
                                                         self.local_site_name,
                                                         True)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiGet(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.list_result_key in rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    @add_fixtures(['test_site'])
    @test_template
    def test_get_with_site_no_access(self):
        """Testing the GET <URL> API without access to a local site"""
        self.load_fixtures(self.basic_get_fixtures)

        url, mimetype, items = self.setup_basic_get_test(self.user, True,
                                                         self.local_site_name,
                                                         False)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiGet(url, expected_status=403)
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

    @test_template
    def test_post(self):
        """Testing the POST <URL> API"""
        self.load_fixtures(self.basic_post_fixtures)
        self._login_user(admin=self.basic_post_use_admin)

        url, mimetype, post_data, cb_args = \
            self.setup_basic_post_test(self.user, False, None, True)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiPost(url, post_data, expected_mimetype=mimetype)
        self._close_file_handles(post_data)
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(self.user, rsp, *cb_args)

    @add_fixtures(['test_site'])
    @test_template
    def test_post_with_site(self):
        """Testing the POST <URL> API with access to a local site"""
        self.load_fixtures(self.basic_post_fixtures)

        user = self._login_user(local_site=True,
                                admin=self.basic_post_use_admin)
        url, mimetype, post_data, cb_args = \
            self.setup_basic_post_test(user, True, self.local_site_name, True)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiPost(url, post_data, expected_mimetype=mimetype)
        self._close_file_handles(post_data)
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(user, rsp, *cb_args)

    @add_fixtures(['test_site'])
    @test_template
    def test_post_with_site_no_access(self):
        """Testing the POST <URL> API without access to a local site"""
        self.load_fixtures(self.basic_post_fixtures)

        user = self._login_user(local_site=True)
        url, mimetype, post_data, cb_args = \
            self.setup_basic_post_test(user, True, self.local_site_name, False)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        self._login_user()

        rsp = self.apiPost(url, post_data, expected_status=403)
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

    @test_template
    def test_post_method_not_allowed(self):
        """Testing the POST <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_list_test(self.user)

        self.apiPost(url, {}, expected_status=405)


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

    @test_template
    def test_put(self):
        """Testing the PUT <URL> API"""
        self.load_fixtures(self.basic_put_fixtures)
        self._login_user(admin=self.basic_put_use_admin)

        url, mimetype, put_data, item, cb_args = \
            self.setup_basic_put_test(self.user, False, None, True)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiPut(url, put_data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        self.check_put_result(self.user, rsp[self.resource.item_result_key],
                              item, *cb_args)

    @add_fixtures(['test_site'])
    @test_template
    def test_put_with_site(self):
        """Testing the PUT <URL> API with access to a local site"""
        self.load_fixtures(self.basic_put_fixtures)

        user = self._login_user(local_site=True,
                                admin=self.basic_put_use_admin)
        url, mimetype, put_data, item, cb_args = \
            self.setup_basic_put_test(user, True, self.local_site_name, True)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiPut(url, put_data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        self.check_put_result(self.user, rsp[self.resource.item_result_key],
                              item, *cb_args)

    @add_fixtures(['test_site'])
    @test_template
    def test_put_with_site_no_access(self):
        """Testing the PUT <URL> API without access to a local site"""
        self.load_fixtures(self.basic_put_fixtures)

        user = self._login_user(local_site=True,
                                admin=self.basic_put_use_admin)
        url, mimetype, put_data, item, cb_args = \
            self.setup_basic_put_test(user, True, self.local_site_name, False)
        self.assertTrue(url.startswith('/s/' + self.local_site_name))

        user = self._login_user()
        rsp = self.apiPut(url, put_data, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @test_template
    def test_put_not_owner(self):
        """Testing the PUT <URL> API without owner"""
        self.load_fixtures(self.basic_put_fixtures)

        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        url, mimetype, put_data, item, cb_args = \
            self.setup_basic_put_test(user, False, None, False)
        self.assertFalse(url.startswith('/s/' + self.local_site_name))

        rsp = self.apiPut(url, put_data, expected_status=403)
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

    @test_template
    def test_put_method_not_allowed(self):
        """Testing the PUT <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_item_test(self.user)

        self.apiPut(url, {}, expected_status=405)


class BaseReviewRequestChildMixin(object):
    """Base class for tests for children of ReviewRequestResource.

    This will test that the resources are only accessible when the user has
    access to the review request itself (such as when the review request
    is private due to being in an invite-only repository or group).

    This applies to immediate children and any further down the tree.
    """
    def setup_review_request_child_test(self, review_request):
        raise NotImplementedError(
            "%s doesn't implement setup_review_request_child_test"
            % self.__class__.__name__)

    @test_template
    def test_get_with_private_group(self):
        """Testing the GET <URL> API
        with access to review request on a private group
        """
        group = self.create_review_group(invite_only=True)
        group.users.add(self.user)
        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        url, mimetype = self.setup_review_request_child_test(review_request)

        rsp = self.apiGet(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')

    @test_template
    def test_get_with_private_group_no_access(self):
        """Testing the GET <URL> API
        without access to review request on a private group
        """
        group = self.create_review_group(invite_only=True)
        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        url, mimetype = self.setup_review_request_child_test(review_request)

        rsp = self.apiGet(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_scmtools'])
    @test_template
    def test_get_with_private_repo(self):
        """Testing the GET <URL> API
        with access to review request on a private repository
        """
        repository = self.create_repository(public=False)
        repository.users.add(self.user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        url, mimetype = self.setup_review_request_child_test(review_request)

        rsp = self.apiGet(url, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_scmtools'])
    @test_template
    def test_get_with_private_repo_no_access(self):
        """Testing the GET <URL> API
        without access to review request on a private repository
        """
        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        url, mimetype = self.setup_review_request_child_test(review_request)

        rsp = self.apiGet(url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ReviewRequestChildListMixin(BaseReviewRequestChildMixin):
    """Tests for list resources that are children of ReviewRequestResource."""


class ReviewRequestChildItemMixin(BaseReviewRequestChildMixin):
    """Tests for item resources that are children of ReviewRequestResource."""
