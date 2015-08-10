#
# tests.py -- Unit tests for classes in djblets.webapi
#
# Copyright (c) 2011  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import print_function, unicode_literals

import json
import warnings

from django.contrib.auth.models import AnonymousUser, User
from django.test.client import RequestFactory
from django.utils import six

from djblets.testing.testcases import TestCase
from djblets.webapi.decorators import (copy_webapi_decorator_data,
                                       webapi_login_required,
                                       webapi_permission_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED,
                                   WebAPIError)
from djblets.webapi.resources import (UserResource, WebAPIResource,
                                      unregister_resource)


class WebAPIDecoratorTests(TestCase):
    def test_copy_webapi_decorator_data(self):
        """Testing copy_webapi_decorator_data"""
        def func1():
            """Function 1"""

        def func2():
            """Function 2"""

        func1.test1 = True
        func1.response_errors = set(['a', 'b'])
        func2.test2 = True
        func2.response_errors = set(['c', 'd'])

        result = copy_webapi_decorator_data(func1, func2)
        self.assertEqual(result, func2)

        self.assertTrue(hasattr(func2, 'test1'))
        self.assertTrue(hasattr(func2, 'test2'))
        self.assertTrue(hasattr(func2, 'response_errors'))
        self.assertTrue(func2.test1)
        self.assertTrue(func2.test2)
        self.assertEqual(func2.response_errors, set(['a', 'b', 'c', 'd']))
        self.assertEqual(func2.__doc__, 'Function 1')
        self.assertEqual(func2.__name__, 'func1')

        self.assertFalse(hasattr(func1, 'test2'))
        self.assertEqual(func1.response_errors, set(['a', 'b']))

    def test_webapi_response_errors_state(self):
        """Testing @webapi_response_errors state"""
        def orig_func():
            """Function 1"""

        func = webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN)(orig_func)

        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_response_errors_preserves_state(self):
        """Testing @webapi_response_errors preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        @webapi_response_errors(NOT_LOGGED_IN)
        def func():
            """Function 1"""

        self.assertEqual(func.__name__, 'func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_response_errors_call(self):
        """Testing @webapi_response_errors calls original function"""
        @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN)
        def func():
            func.seen = True

        func()

        self.assertTrue(hasattr(func, 'seen'))

    def test_webapi_login_required_state(self):
        """Testing @webapi_login_required state"""
        def orig_func():
            """Function 1"""

        func = webapi_login_required(orig_func)

        self.assertFalse(hasattr(orig_func, 'login_required'))
        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'login_required'))
        self.assertTrue(func.login_required)
        self.assertEqual(func.response_errors, set([NOT_LOGGED_IN]))

    def test_webapi_login_required_preserves_state(self):
        """Testing @webapi_login_required preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        func = webapi_login_required(orig_func)

        self.assertFalse(hasattr(orig_func, 'login_required'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'login_required'))
        self.assertTrue(func.login_required)
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN]))

    def test_webapi_login_required_call_when_authenticated(self):
        """Testing @webapi_login_required calls when authenticated"""
        @webapi_login_required
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        result = func(request)

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_login_required_call_when_anonymous(self):
        """Testing @webapi_login_required calls when anonymous"""
        @webapi_login_required
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = AnonymousUser()
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, NOT_LOGGED_IN)

    def test_webapi_permission_required_state(self):
        """Testing @webapi_permission_required state"""
        def orig_func():
            """Function 1"""

        func = webapi_permission_required('myperm')(orig_func)

        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([NOT_LOGGED_IN, PERMISSION_DENIED]))

    def test_webapi_permission_required_preserves_state(self):
        """Testing @webapi_permission_required preserves decorator state"""
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        func = webapi_permission_required('myperm')(orig_func)

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, NOT_LOGGED_IN,
                              PERMISSION_DENIED]))

    def test_webapi_permission_required_call_when_anonymous(self):
        """Testing @webapi_permission_required calls when anonymous"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = AnonymousUser()
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, NOT_LOGGED_IN)

    def test_webapi_permission_required_call_when_has_permission(self):
        """Testing @webapi_permission_required calls when has permission"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        request.user.has_perm = lambda perm: True
        result = func(request)

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_permission_required_call_when_no_permission(self):
        """Testing @webapi_permission_required calls when no permission"""
        @webapi_permission_required('foo')
        def func(request):
            func.seen = True

        request = RequestFactory().request()
        request.user = User()
        request.user.has_perm = lambda perm: False
        result = func(request)

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result, PERMISSION_DENIED)

    def test_webapi_request_fields_state(self):
        """Testing @webapi_request_fields state"""
        def orig_func():
            """Function 1"""

        required = {
            'required_param': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional = {
            'optional_param': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        func = webapi_request_fields(required, optional)(orig_func)

        self.assertFalse(hasattr(orig_func, 'required_fields'))
        self.assertFalse(hasattr(orig_func, 'optional_fields'))
        self.assertFalse(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'required_fields'))
        self.assertTrue(hasattr(func, 'optional_fields'))
        self.assertEqual(func.required_fields, required)
        self.assertEqual(func.optional_fields, optional)
        self.assertEqual(func.response_errors, set([INVALID_FORM_DATA]))

    def test_webapi_request_fields_preserves_state(self):
        """Testing @webapi_request_fields preserves decorator state"""
        required1 = {
            'required1': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional1 = {
            'optional1': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        @webapi_request_fields(required1, optional1)
        @webapi_response_errors(DOES_NOT_EXIST)
        def orig_func():
            """Function 1"""

        required2 = {
            'required2': {
                'type': bool,
                'description': 'Required param'
            },
        }

        optional2 = {
            'optional2': {
                'type': bool,
                'description': 'Optional param'
            },
        }

        func = webapi_request_fields(required2, optional2)(orig_func)

        expected_required = required1.copy()
        expected_required.update(required2)
        expected_optional = optional1.copy()
        expected_optional.update(optional2)

        self.assertTrue(hasattr(orig_func, 'required_fields'))
        self.assertTrue(hasattr(orig_func, 'optional_fields'))
        self.assertTrue(hasattr(orig_func, 'response_errors'))

        self.assertEqual(func.__name__, 'orig_func')
        self.assertEqual(func.__doc__, 'Function 1')
        self.assertTrue(hasattr(func, 'response_errors'))
        self.assertTrue(hasattr(func, 'required_fields'))
        self.assertTrue(hasattr(func, 'optional_fields'))
        self.assertEqual(func.required_fields, expected_required)
        self.assertEqual(func.optional_fields, expected_optional)
        self.assertEqual(func.response_errors,
                         set([DOES_NOT_EXIST, INVALID_FORM_DATA]))

    def test_webapi_request_fields_call_normalizes_params(self):
        """Testing @webapi_request_fields normalizes params to function"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
            optional={
                'optional_param': {
                    'type': bool,
                }
            },
        )
        def func(request, required_param=None, optional_param=None,
                 extra_fields={}):
            func.seen = True
            self.assertTrue(isinstance(required_param, int))
            self.assertTrue(isinstance(optional_param, bool))
            self.assertEqual(required_param, 42)
            self.assertTrue(optional_param)
            self.assertFalse(extra_fields)

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_with_unexpected_arg(self):
        """Testing @webapi_request_fields with unexpected argument"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
        )
        def func(request, required_param=None, extra_fields={}):
            func.seen = True

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result[0], INVALID_FORM_DATA)
        self.assertTrue('fields' in result[1])
        self.assertTrue('optional_param' in result[1]['fields'])

    def test_webapi_request_fields_call_with_allow_unknown(self):
        """Testing @webapi_request_fields with allow_unknown=True"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
            allow_unknown=True
        )
        def func(request, required_param=None, extra_fields={}):
            func.seen = True
            self.assertEqual(required_param, 42)
            self.assertTrue('optional_param' in extra_fields)
            self.assertEqual(extra_fields['optional_param'], '1')

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'optional_param': '1',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_filter_special_params(self):
        """Testing @webapi_request_fields filters special params"""
        @webapi_request_fields(
            required={
                'required_param': {
                    'type': int,
                }
            },
        )
        def func(request, required_param=None, extra_fields={}):
            func.seen = True
            self.assertTrue(isinstance(required_param, int))
            self.assertEqual(required_param, 42)
            self.assertFalse(extra_fields)

        result = func(RequestFactory().get(
            path='/',
            data={
                'required_param': '42',
                'api_format': 'json',
            }
        ))

        self.assertTrue(hasattr(func, 'seen'))
        self.assertEqual(result, None)

    def test_webapi_request_fields_call_validation_int(self):
        """Testing @webapi_request_fields with int parameter validation"""
        @webapi_request_fields(
            required={
                'myint': {
                    'type': int,
                }
            }
        )
        def func(request, myint=False, extra_fields={}):
            func.seen = True

        result = func(RequestFactory().get(
            path='/',
            data={
                'myint': 'abc',
            }
        ))

        self.assertFalse(hasattr(func, 'seen'))
        self.assertEqual(result[0], INVALID_FORM_DATA)
        self.assertTrue('fields' in result[1])
        self.assertTrue('myint' in result[1]['fields'])


class WebAPIErrorTests(TestCase):
    def test_with_message(self):
        """Testing WebAPIError.with_message"""
        orig_msg = 'Original message'
        new_msg = 'New message'
        headers = {
            'foo': 'bar',
        }

        orig_error = WebAPIError(123, orig_msg, http_status=500,
                                 headers=headers)
        new_error = orig_error.with_message(new_msg)

        self.assertNotEqual(orig_error, new_error)
        self.assertEqual(new_error.msg, new_msg)
        self.assertEqual(new_error.headers, headers)
        self.assertEqual(new_error.code, orig_error.code)
        self.assertEqual(new_error.http_status, orig_error.http_status)
        self.assertEqual(orig_error.msg, orig_msg)
        self.assertEqual(orig_error.headers, headers)

    def test_with_overrides(self):
        """Testing WebAPIError.with_overrides"""
        orig_msg = 'Original message'
        new_msg = 'New message'
        orig_headers = {
            'foo': 'bar',
        }
        new_headers = {
            'abc': '123',
        }

        orig_error = WebAPIError(123, orig_msg, http_status=500,
                                 headers=orig_headers)
        new_error = orig_error.with_overrides(new_msg, headers=new_headers)

        self.assertNotEqual(orig_error, new_error)
        self.assertEqual(new_error.msg, new_msg)
        self.assertEqual(new_error.headers, new_headers)
        self.assertEqual(new_error.code, orig_error.code)
        self.assertEqual(new_error.http_status, orig_error.http_status)
        self.assertEqual(orig_error.msg, orig_msg)
        self.assertEqual(orig_error.headers, orig_headers)


class WebAPIResourceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.test_resource = None

    def tearDown(self):
        if self.test_resource:
            unregister_resource(self.test_resource)

    def test_vendor_mimetypes(self):
        """Testing WebAPIResource with vendor-specific mimetypes"""
        class TestResource(WebAPIResource):
            mimetype_vendor = 'djblets'

        self.test_resource = TestResource()

        item_mimetypes = [
            mimetype['item']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'item' in mimetype
        ]

        list_mimetypes = [
            mimetype['list']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'list' in mimetype
        ]

        self.assertEqual(len(list_mimetypes), 4)
        self.assertEqual(len(item_mimetypes), 4)

        self.assertTrue('application/json' in
                        list_mimetypes)
        self.assertTrue('application/xml' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+json' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+xml' in
                        list_mimetypes)

        self.assertTrue('application/json' in
                        item_mimetypes)
        self.assertTrue('application/xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+json' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)

    def test_vendor_mimetypes_with_custom(self):
        """Testing WebAPIResource with vendor-specific and custom mimetypes"""
        class TestResource(WebAPIResource):
            mimetype_vendor = 'djblets'
            allowed_mimetypes = WebAPIResource.allowed_mimetypes + [
                {'item': 'text/html'},
            ]

        self.test_resource = TestResource()

        item_mimetypes = [
            mimetype['item']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'item' in mimetype
        ]

        list_mimetypes = [
            mimetype['list']
            for mimetype in self.test_resource.allowed_mimetypes
            if 'list' in mimetype
        ]

        self.assertEqual(len(list_mimetypes), 4)
        self.assertEqual(len(item_mimetypes), 5)

        self.assertTrue('application/json' in
                        list_mimetypes)
        self.assertTrue('application/xml' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+json' in
                        list_mimetypes)
        self.assertTrue('application/vnd.djblets.testresources+xml' in
                        list_mimetypes)

        self.assertTrue('application/json' in
                        item_mimetypes)
        self.assertTrue('application/xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+json' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)
        self.assertTrue('application/vnd.djblets.testresource+xml' in
                        item_mimetypes)
        self.assertTrue('text/html' in
                        item_mimetypes)

    def test_get_with_vendor_mimetype(self):
        """Testing WebAPIResource with GET and vendor-specific mimetypes"""
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'

            def get(self, *args, **kwargs):
                return 200, {}

            create = get
            update = get
            delete = get

        self.test_resource = TestResource()
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml')
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            method='post')

        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            view_kwargs={'id': 1},
            method='put')
        self._test_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            view_kwargs={'id': 1},
            method='delete')

    def test_get_with_item_mimetype(self):
        """Testing WebAPIResource with GET and Item-Content-Type header"""
        class TestResource(WebAPIResource):
            allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
            mimetype_vendor = 'djblets'
            uri_object_key = 'id'

            def get(self, *args, **kwargs):
                return 200, {}

            create = get
            update = get
            delete = get

        self.test_resource = TestResource()
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            method='post')

        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            view_kwargs={'id': 1},
            method='put')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/',
            'application/vnd.djblets.testresources+json',
            'application/vnd.djblets.testresources+xml',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml')
        self._test_item_mimetype_responses(
            self.test_resource,
            '/api/tests/1/',
            'application/vnd.djblets.testresource+json',
            'application/vnd.djblets.testresource+xml',
            None,
            None,
            view_kwargs={'id': 1},
            method='delete')

    def test_generate_etag_with_encode_etag_true(self):
        """Testing WebAPIResource.generate_etag with encode_etag=True"""
        class TestObject(object):
            my_field = 'abc'

        request = RequestFactory().request()
        request.user = User()

        resource = WebAPIResource()

        with warnings.catch_warnings(record=True) as w:
            etag = resource.generate_etag(TestObject(), ['my_field'], request,
                                          encode_etag=True)
            self.assertEqual(len(w), 1)
            self.assertIn('generate_etag will stop generating',
                          six.text_type(w[0].message))

        self.assertEqual(etag, '416c0aecaf0b1e8ec64104349ba549c7534861f2')

    def test_generate_etag_with_encode_etag_false(self):
        """Testing WebAPIResource.generate_etag with encode_etag=False"""
        class TestObject(object):
            my_field = 'abc'

        request = RequestFactory().request()
        request.user = User()

        resource = WebAPIResource()
        obj = TestObject()

        with warnings.catch_warnings(record=True) as w:
            etag = resource.generate_etag(obj, None, request,
                                          encode_etag=False)
            self.assertEqual(len(w), 0)

        self.assertEqual(
            etag,
            repr(resource.serialize_object(obj, request=request)))

    def test_are_cache_headers_current_with_old_last_modified(self):
        """Testing WebAPIResource.are_cache_headers_current with old last
        modified timestamp
        """
        request = RequestFactory().request()
        request.META['HTTP_IF_MODIFIED_SINCE'] = \
            'Wed, 14 Jan 2015 13:49:10 GMT'

        resource = WebAPIResource()
        self.assertFalse(resource.are_cache_headers_current(
            request, last_modified='Wed, 14 Jan 2015 12:10:13 GMT'))

    def test_are_cache_headers_current_with_current_last_modified(self):
        """Testing WebAPIResource.are_cache_headers_current with current last
        modified timestamp
        """
        timestamp = 'Wed, 14 Jan 2015 13:49:10 GMT'
        request = RequestFactory().request()
        request.META['HTTP_IF_MODIFIED_SINCE'] = timestamp

        resource = WebAPIResource()
        self.assertTrue(resource.are_cache_headers_current(
            request, last_modified=timestamp))

    def test_are_cache_headers_current_with_old_etag(self):
        """Testing WebAPIResource.are_cache_headers_current with old ETag"""
        request = RequestFactory().request()
        request.META['HTTP_IF_NONE_MATCH'] = 'abc123'

        resource = WebAPIResource()
        self.assertFalse(resource.are_cache_headers_current(request,
                                                            etag='def456'))

    def test_are_cache_headers_current_with_current_etag(self):
        """Testing WebAPIResource.are_cache_headers_current with current
        ETag
        """
        etag = 'abc123'
        request = RequestFactory().request()
        request.META['HTTP_IF_NONE_MATCH'] = etag

        resource = WebAPIResource()
        self.assertTrue(resource.are_cache_headers_current(request, etag=etag))

    def test_serialize_object_with_cache_copy(self):
        """Testing WebAPIResource.serialize_object always returns a copy of
        the cached data
        """
        class TestObject(object):
            my_field = 'abc'

        request = RequestFactory().request()
        request.user = User()

        resource = WebAPIResource()
        resource.fields = {
            'my_field': {
                'type': six.text_type,
            }
        }

        obj = TestObject()

        # We check this three times, since prior to Djblets 2.0.20, we would
        # first return a copy of the newly-generated data, then the cached
        # copy of the original data, and then the cached copy again (which
        # would no longer be untouched).
        data = resource.serialize_object(obj, request=request)
        self.assertIn('my_field', data)
        del data['my_field']

        data = resource.serialize_object(obj, request=request)
        self.assertIn('my_field', data)
        del data['my_field']

        data = resource.serialize_object(obj, request=request)
        self.assertIn('my_field', data)

    def _test_mimetype_responses(self, resource, url, json_mimetype,
                                 xml_mimetype, **kwargs):
        self._test_mimetype_response(resource, url, '*/*', json_mimetype,
                                     **kwargs)
        self._test_mimetype_response(resource, url, 'application/json',
                                     json_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, json_mimetype,
                                     json_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, 'application/xml',
                                     xml_mimetype, **kwargs)
        self._test_mimetype_response(resource, url, xml_mimetype, xml_mimetype,
                                     **kwargs)

    def _test_mimetype_response(self, resource, url, accept_mimetype,
                                response_mimetype, method='get',
                                view_kwargs={}):
        func = getattr(self.factory, method)

        if accept_mimetype:
            request = func(url, HTTP_ACCEPT=accept_mimetype)
        else:
            request = func(url)

        response = resource(request, **view_kwargs)
        print(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], response_mimetype)

    def _test_item_mimetype_responses(self, resource, url, json_mimetype,
                                      xml_mimetype, json_item_mimetype,
                                      xml_item_mimetype, **kwargs):
        self._test_item_mimetype_response(resource, url, '*/*',
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, 'application/json',
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, json_mimetype,
                                          json_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, 'application/xml',
                                          xml_item_mimetype, **kwargs)
        self._test_item_mimetype_response(resource, url, xml_mimetype,
                                          xml_item_mimetype, **kwargs)

    def _test_item_mimetype_response(self, resource, url, accept_mimetype,
                                     response_item_mimetype=None,
                                     method='get', view_kwargs={}):
        func = getattr(self.factory, method)

        if accept_mimetype:
            request = func(url, HTTP_ACCEPT=accept_mimetype)
        else:
            request = func(url)

        response = resource(request, **view_kwargs)
        print(response)
        self.assertEqual(response.status_code, 200)

        if response_item_mimetype:
            self.assertEqual(response['Item-Content-Type'],
                             response_item_mimetype)
        else:
            self.assertTrue('Item-Content-Type' not in response)


class WebAPICoreTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user_resource = UserResource()

    def tearDown(self):
        unregister_resource(self.user_resource)

    def test_pagination_serialization_encoding(self):
        """Testing WebAPIResponsePaginated query parameter encoding"""
        # This test is for an issue when query parameters included unicode
        # characters. In this case, creating the 'self' or pagination links
        # would cause a KeyError. If this test runs fine without any uncaught
        # exceptions, then it means we're good.
        request = self.factory.get('/api/users/?q=%D0%B5')
        response = self.user_resource(request)
        print(response)

        rsp = json.loads(response.content)
        self.assertEqual(rsp['links']['self']['href'],
                         'http://testserver/api/users/?q=%D0%B5')
