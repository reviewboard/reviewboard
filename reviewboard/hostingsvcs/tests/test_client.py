"""Test cases for the hosting service client support."""

from __future__ import annotations

from kgb import SpyAgency

from reviewboard.hostingsvcs.base import (HostingServiceClient,
                                          HostingServiceHTTPRequest,
                                          HostingServiceHTTPResponse)
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.testing.hosting_services import TestService
from reviewboard.testing.testcase import TestCase


class _DummyHTTPRequest(HostingServiceHTTPRequest):
    def open(self) -> HostingServiceHTTPResponse:
        method = self.method

        if method in {'DELETE', 'HEAD'}:
            data = None
        else:
            data = b'{"key": "test response"}'

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
                'Test-header': 'Value',
            },
            status_code=status_code)


class HostingServiceHTTPRequestTests(TestCase):
    """Unit tests for HostingServiceHTTPRequest."""

    def test_init_with_query(self) -> None:
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

    def test_init_with_body_not_bytes(self) -> None:
        """Testing HostingServiceHTTPRequest construction with non-bytes body
        """
        account = HostingServiceAccount()
        service = TestService(account)

        expected_message = (
            f'Received non-bytes body for the HTTP request for '
            f'{TestService!r}. This is likely an implementation problem. '
            f'Please make sure only byte strings are sent for the request '
            f'body.'
        )

        with self.assertRaisesMessage(TypeError, expected_message):
            HostingServiceHTTPRequest(
                url='http://example.com?z=1&z=2&baz=true',
                method='POST',
                body=123,  # type:ignore
                hosting_service=service)

    def test_init_with_header_key_not_unicode(self) -> None:
        """Testing HostingServiceHTTPRequest construction with non-Unicode
        header key
        """
        account = HostingServiceAccount()
        service = TestService(account)

        expected_message = (
            f"Received non-Unicode header name b'My-Header' (value='abc') for "
            f"the HTTP request for {TestService!r}. This is likely an "
            f"implementation problem. Please make sure only Unicode strings "
            f"are sent in request headers."
        )

        with self.assertRaisesMessage(TypeError, expected_message):
            HostingServiceHTTPRequest(
                url='http://example.com?z=1&z=2&baz=true',
                method='POST',
                headers={  # type:ignore
                    b'My-Header': 'abc',
                },
                hosting_service=service)

    def test_init_with_header_value_not_unicode(self) -> None:
        """Testing HostingServiceHTTPRequest construction with non-Unicode
        header value
        """
        account = HostingServiceAccount()
        service = TestService(account)

        expected_message = (
            f"Received non-Unicode header value for 'My-Header' "
            f"(value=b'abc') for the HTTP request for {TestService!r}. This "
            f"is likely an implementation problem. Please make sure only "
            f"Unicode strings are sent in request headers."
        )

        with self.assertRaisesMessage(TypeError, expected_message):
            HostingServiceHTTPRequest(
                url='http://example.com?z=1&z=2&baz=true',
                method='POST',
                headers={  # type:ignore
                    'My-Header': b'abc',
                },
                hosting_service=service)

    def test_add_basic_auth(self) -> None:
        """Testing HostingServiceHTTPRequest.add_basic_auth"""
        request = HostingServiceHTTPRequest('http://example.com')
        request.add_basic_auth(b'username', b'password')

        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
            })

    def test_get_header(self) -> None:
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

    def test_json(self) -> None:
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

    def test_json_with_non_json_response(self) -> None:
        """Testing HostingServiceHTTPResponse.json with non-JSON response"""
        request = HostingServiceHTTPRequest('http://example.com')
        response = HostingServiceHTTPResponse(request=request,
                                              url='http://example.com',
                                              data=b'XXX',
                                              headers={},
                                              status_code=200)

        with self.assertRaises(ValueError):
            response.json

    def test_get_header(self) -> None:
        """Testing HostingServiceHTTPRequest.get_header"""
        request = HostingServiceHTTPRequest('http://example.com')
        response = HostingServiceHTTPResponse(
            request=request,
            url=request.url,
            status_code=200,
            data=b'',
            headers={
                'Authorization': 'Basic abc123',
                'Content-Length': '123',
            })

        self.assertEqual(response.get_header('Authorization'), 'Basic abc123')
        self.assertEqual(response.get_header('AUTHORIZATION'), 'Basic abc123')
        self.assertEqual(response.get_header('authorization'), 'Basic abc123')

        self.assertEqual(response.get_header('Content-Length'), '123')
        self.assertEqual(response.get_header('CONTENT-LENGTH'), '123')
        self.assertEqual(response.get_header('content-length'), '123')


class HostingServiceClientTests(SpyAgency, TestCase):
    """Unit tests for HostingServiceClient"""

    #: The hosting service client for the tests.
    #:
    #: Type:
    #:     reviewboard.hostingsvcs.base.client.HostingServiceClient
    client: HostingServiceClient

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        account = HostingServiceAccount()
        service = TestService(account)

        self.client = HostingServiceClient(service)
        self.client.http_request_cls = _DummyHTTPRequest

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        self.client = None  # type: ignore

    def test_http_delete(self) -> None:
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
        self.assertEqual(response.data, b'')
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.status_code, 204)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        self.assertSpyCalledWith(
            self.client.build_http_request,
            url='http://example.com',
            body=None,
            headers={
                'Foo': 'bar',
            },
            credentials={
                'username': 'username',
                'password': 'password',
            })

        request = self.client.build_http_request.last_call.return_value
        self.assertIsNone(request.body)
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'DELETE')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_http_get(self) -> None:
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
        self.assertEqual(response.data, b'{"key": "test response"}')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        self.assertSpyCalledWith(
            self.client.build_http_request,
            url='http://example.com',
            body=None,
            headers={
                'Foo': 'bar',
            },
            method='GET',
            username='username',
            password='password')

        request = self.client.build_http_request.last_call.return_value
        self.assertIsNone(request.body)
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'GET')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_http_head(self) -> None:
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
        self.assertEqual(response.data, b'')
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        self.assertSpyCalledWith(
            self.client.build_http_request,
            url='http://example.com',
            body=None,
            headers={
                'Foo': 'bar',
            },
            method='HEAD',
            username='username',
            password='password')

        request = self.client.build_http_request.last_call.return_value
        self.assertIsNone(request.body)
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'HEAD')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_http_post_with_body_unicode(self) -> None:
        """Testing HostingServiceClient.http_post with body as Unicode"""
        self.spy_on(self.client.build_http_request)

        response = self.client.http_post(
            url='http://example.com',
            body='test body\U0001f60b'.encode('utf-8'),
            headers={
                'Foo': 'bar',
            },
            username='username',
            password='password')

        self.assertIsInstance(response, HostingServiceHTTPResponse)
        self.assertEqual(response.url, 'http://example.com')
        self.assertEqual(response.data, b'{"key": "test response"}')
        self.assertEqual(response.status_code, 201)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        self.assertSpyCalledWith(
            self.client.build_http_request,
            url='http://example.com',
            body=b'test body\xf0\x9f\x98\x8b',
            headers={
                'Content-Length': '13',
                'Foo': 'bar',
            },
            method='POST',
            username='username',
            password='password')

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.body, b'test body\xf0\x9f\x98\x8b')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '13',
                'Foo': 'bar',
            })

    def test_http_post_with_body_bytes(self) -> None:
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
        self.assertEqual(response.data, b'{"key": "test response"}')
        self.assertEqual(response.status_code, 201)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        self.assertSpyCalledWith(
            self.client.build_http_request,
            url='http://example.com',
            body=b'test body\x01\x02\x03',
            headers={
                'Content-Length': '12',
                'Foo': 'bar',
            },
            method='POST',
            username='username',
            password='password')

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.body, b'test body\x01\x02\x03')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '12',
                'Foo': 'bar',
            })

    def test_http_put_with_body_unicode(self) -> None:
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
        self.assertEqual(response.data, b'{"key": "test response"}')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'PUT')
        self.assertEqual(request.body, b'test body\xf0\x9f\x98\x8b')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '13',
                'Foo': 'bar',
            })

    def test_http_put_with_body_bytes(self) -> None:
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
        self.assertEqual(response.data, b'{"key": "test response"}')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        self.assertSpyCalledWith(
            self.client.build_http_request,
            url='http://example.com',
            body=b'test body\x01\x02\x03',
            headers={
                'Content-Length': '12',
                'Foo': 'bar',
            },
            method='PUT',
            username='username',
            password='password')

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'PUT')
        self.assertEqual(request.body, b'test body\x01\x02\x03')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Content-length': '12',
                'Foo': 'bar',
            })

    def test_http_request(self) -> None:
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
        self.assertEqual(response.data, b'{"key": "test response"}')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.headers, dict)
        self.assertEqual(
            response.headers,
            {
                'Test-header': 'Value',
            })

        self.assertSpyCalledWith(
            self.client.build_http_request,
            url='http://example.com',
            body=b'test',
            headers={
                'Foo': 'bar',
            },
            method='BAZ',
            username='username',
            password='password')

        request = self.client.build_http_request.last_call.return_value
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.method, 'BAZ')
        self.assertEqual(request.body, b'test')
        self.assertIsInstance(request.headers, dict)
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })

    def test_build_http_request(self) -> None:
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
        self.assertEqual(request.body, b'test')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(
            request.headers,
            {
                'Foo': 'bar',
            })

    def test_build_http_request_with_basic_auth(self) -> None:
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
        self.assertEqual(request.body, b'test')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(
            request.headers,
            {
                'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                'Foo': 'bar',
            })
