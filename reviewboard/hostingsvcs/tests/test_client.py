"""Test cases for the hosting service client support."""

from __future__ import unicode_literals

from kgb import SpyAgency

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (HostingService,
                                             HostingServiceClient,
                                             HostingServiceHTTPRequest,
                                             HostingServiceHTTPResponse)
from reviewboard.testing.testcase import TestCase


class DummyHTTPRequest(HostingServiceHTTPRequest):
    def open(self):
        method = self.method

        if method in ('DELETE', 'HEAD'):
            data = None
        else:
            data = b'test response'

        if method == 'DELETE':
            status_code = 204
        elif method == 'POST':
            status_code = 201
        else:
            status_code = 200

        return HostingServiceHTTPResponse(
            request=self,
            url=self.url,
            data=data,
            headers={
                str('Test-header'): str('Value'),
            },
            status_code=status_code)


class HostingServiceHTTPRequestTests(TestCase):
    """Unit tests for HostingServiceHTTPRequest."""

    def test_init_with_query(self):
        """Testing HostingServiceHTTPRequest construction with query="""
        request = HostingServiceHTTPRequest(
            url='http://example.com?z=1&z=2&baz=true',
            query={
                'foo': 'bar',
                'a': 10,
                'list': ['a', 'b', 'c'],
            })

        self.assertEqual(
            request.url,
            'http://example.com?a=10&baz=true&foo=bar&list=a&list=b&list=c'
            '&z=1&z=2')

    def test_add_basic_auth(self):
        """Testing HostingServiceHTTPRequest.add_basic_auth"""
        request = HostingServiceHTTPRequest('http://example.com')
        request.add_basic_auth(b'username', b'password')

        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
            })

    def test_get_header(self):
        """Testing HostingServiceHTTPRequest.get_header"""
        request = HostingServiceHTTPRequest(
            'http://example.com',
            headers={
                'Authorization': 'Basic abc123',
                'Content-Length': '123',
            })

        self.assertEqual(request.get_header('Authorization'), 'Basic abc123')
        self.assertEqual(request.get_header('AUTHORIZATION'), 'Basic abc123')
        self.assertEqual(request.get_header('authorization'), 'Basic abc123')

        self.assertEqual(request.get_header('Content-Length'), '123')
        self.assertEqual(request.get_header('CONTENT-LENGTH'), '123')
        self.assertEqual(request.get_header('content-length'), '123')


class HostingServiceHTTPResponseTests(TestCase):
    """Unit tests for HostingServiceHTTPResponse."""

    def test_json(self):
        """Testing HostingServiceHTTPResponse.json"""
        request = HostingServiceHTTPRequest('http://example.com')
        response = HostingServiceHTTPResponse(request=request,
                                              url='http://example.com',
                                              data=b'{"a": 1, "b": 2}',
                                              headers={},
                                              status_code=200)
        self.assertEqual(
            response.json,
            {
                'a': 1,
                'b': 2,
            })

    def test_json_with_non_json_response(self):
        """Testing HostingServiceHTTPResponse.json with non-JSON response"""
        request = HostingServiceHTTPRequest('http://example.com')
        response = HostingServiceHTTPResponse(request=request,
                                              url='http://example.com',
                                              data=b'{[(',
                                              headers={},
                                              status_code=200)

        with self.assertRaises(ValueError):
            response.json

    def test_get_header(self):
        """Testing HostingServiceHTTPRequest.get_header"""
        request = HostingServiceHTTPRequest('http://example.com')
        response = HostingServiceHTTPResponse(
            request=request,
            url=request.url,
            status_code=200,
            data=b'',
            headers={
                str('Authorization'): str('Basic abc123'),
                str('Content-Length'): str('123'),
            })

        self.assertEqual(response.get_header('Authorization'), 'Basic abc123')
        self.assertEqual(response.get_header('AUTHORIZATION'), 'Basic abc123')
        self.assertEqual(response.get_header('authorization'), 'Basic abc123')

        self.assertEqual(response.get_header('Content-Length'), '123')
        self.assertEqual(response.get_header('CONTENT-LENGTH'), '123')
        self.assertEqual(response.get_header('content-length'), '123')


class HostingServiceClientTests(SpyAgency, TestCase):
    """Unit tests for HostingServiceClient"""

    def setUp(self):
        super(HostingServiceClientTests, self).setUp()

        account = HostingServiceAccount()
        service = HostingService(account)

        self.client = HostingServiceClient(service)
        self.client.http_request_cls = DummyHTTPRequest

    def test_http_delete(self):
        """Testing HostingServiceClient.http_delete"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_delete(
            url='http://example.com',
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertIsNone(response.data)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.status_code, 204)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=None,
            headers={
                'Foo': 'bar',
            },
            credentials={
                'username': 'username',
                'password': 'password',
            }))

        request = self.client.build_http_request.last_call.return_value
        self.assertIsNone(request.data)
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'DELETE')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_http_get(self):
        """Testing HostingServiceClient.http_get"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_get(
            url='http://example.com',
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.data, b'test response')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=None,
            headers={
                'Foo': 'bar',
            },
            method='GET',
            username='username',
            password='password'))

        request = self.client.build_http_request.last_call.return_value
        self.assertIsNone(request.data)
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'GET')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_http_head(self):
        """Testing HostingServiceClient.http_head"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_head(
            url='http://example.com',
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertIsNone(response.data)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=None,
            headers={
                'Foo': 'bar',
            },
            method='HEAD',
            username='username',
            password='password'))

        request = self.client.build_http_request.last_call.return_value
        self.assertIsNone(request.data)
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'HEAD')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_http_post_with_body_unicode(self):
        """Testing HostingServiceClient.http_post with body as Unicode"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_post(
            url='http://example.com',
            body='test body\U0001f60b',
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.data, b'test response')
        self.assertEqual(response.status_code, 201)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=b'test body\xf0\x9f\x98\x8b',
            headers={
                'Content-Length': '13',
                'Foo': 'bar',
            },
            method='POST',
            username='username',
            password='password'))

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.data, b'test body\xf0\x9f\x98\x8b')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '13',
                'Foo': 'bar',
            })

    def test_http_post_with_body_bytes(self):
        """Testing HostingServiceClient.http_post with body as bytes"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_post(
            url='http://example.com',
            body=b'test body\x01\x02\x03',
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.data, b'test response')
        self.assertEqual(response.status_code, 201)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=b'test body\x01\x02\x03',
            headers={
                'Content-Length': '12',
                'Foo': 'bar',
            },
            method='POST',
            username='username',
            password='password'))

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.data, b'test body\x01\x02\x03')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '12',
                'Foo': 'bar',
            })

    def test_http_put_with_body_unicode(self):
        """Testing HostingServiceClient.http_put with body as Unicode"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_put(
            url='http://example.com',
            body='test body\U0001f60b',
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.data, b'test response')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=b'test body\xf0\x9f\x98\x8b',
            headers={
                'Content-Length': '13',
                'Foo': 'bar',
            },
            method='PUT',
            username='username',
            password='password'))

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'PUT')
        self.assertEqual(request.data, b'test body\xf0\x9f\x98\x8b')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '13',
                'Foo': 'bar',
            })

    def test_http_put_with_body_bytes(self):
        """Testing HostingServiceClient.http_put with body as bytes"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_put(
            url='http://example.com',
            body=b'test body\x01\x02\x03',
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.data, b'test response')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=b'test body\x01\x02\x03',
            headers={
                'Content-Length': '12',
                'Foo': 'bar',
            },
            method='PUT',
            username='username',
            password='password'))

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'PUT')
        self.assertEqual(request.data, b'test body\x01\x02\x03')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '12',
                'Foo': 'bar',
            })

    def test_http_request(self):
        """Testing HostingServiceClient.http_request"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_request(
            url='http://example.com',
            body=b'test',
            headers={
                'Foo': 'bar',
            },
            method='BAZ',
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.data, b'test response')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                str('Test-header'): str('Value'),
            })

        data, headers = response
        self.assertEqual(data, response.data)
        self.assertEqual(headers, response.headers)

        self.assertTrue(self.client.build_http_request.called_with(
            url='http://example.com',
            body=b'test',
            headers={
                'Foo': 'bar',
            },
            method='BAZ',
            username='username',
            password='password'))

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'BAZ')
        self.assertEqual(request.data, b'test')
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_build_http_request(self):
        """Testing HostingServiceClient.build_http_request"""
        request = self.client.build_http_request(
            url='http://example.com',
            body=b'test',
            method='POST',
            credentials={},
            headers={
                'Foo': 'bar',
            })

        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.data, b'test')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(
            request.headers,
            {
                'Foo': 'bar',
            })

    def test_build_http_request_with_basic_auth(self):
        """Testing HostingServiceClient.build_http_request with username and
        password
        """
        request = self.client.build_http_request(
            url='http://example.com',
            body=b'test',
            method='POST',
            headers={
                'Foo': 'bar',
            },
            credentials={
                'username': 'username',
                'password': 'password',
            })

        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.data, b'test')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })
