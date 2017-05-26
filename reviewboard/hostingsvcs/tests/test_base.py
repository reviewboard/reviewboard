"""Test cases for the base URLRequest and HostingServiceClient classes."""

from __future__ import unicode_literals

import base64

from django.utils.six.moves.urllib.request import (HTTPBasicAuthHandler,
                                                   urlopen)
from kgb import SpyAgency

from reviewboard.hostingsvcs.service import HostingServiceClient, URLRequest
from reviewboard.testing.testcase import TestCase


def _test_basic_auth(testcase, request):
    """Test the request contains the HTTP Basic Auth header.

    Args:
        testcase (reviewboard.testing.testcase.TestCase):
            The test case

        request (reviewboard.hostingsvcs.service.URLRequest):
            The request to check.
    """
    testcase.assertIn(HTTPBasicAuthHandler.auth_header, request.headers)
    testcase.assertEqual(request.headers[HTTPBasicAuthHandler.auth_header],
                         b'Basic %s' % base64.b64encode(b'username:password'))


class URLRequestTests(TestCase):
    """Tests for URLRequest."""

    def test_http_basic_auth(self):
        """Testing HTTP basic auth requests"""

        request = URLRequest('http://example.com')
        request.add_basic_auth(b'username', b'password')
        _test_basic_auth(self, request)


class FakeResponse(object):
    """A fake response from urllopen"""

    def read(self):
        return ''

    @property
    def headers(self):
        return {}


class HostingServiceClientTests(SpyAgency, TestCase):
    """Tests for HostingServiceClient"""

    def test_http_request_basic_auth(self):
        """Testing HostingServiceClient.http_request with basic auth"""
        self.spy_on(urlopen, call_fake=lambda *args, **kwargs: FakeResponse())

        client = HostingServiceClient(None)
        client.http_get('http://example.com',
                        username=b'username',
                        password=b'password')

        self.assertTrue(urlopen.spy.called)
        request = urlopen.spy.calls[0].args[0]

        _test_basic_auth(self, request)
