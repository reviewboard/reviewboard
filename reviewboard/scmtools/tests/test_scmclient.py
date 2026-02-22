"""Unit tests for reviewboard.scmtools.core.SCMClient."""

from urllib.error import HTTPError
from urllib.request import urlopen

import kgb

from reviewboard.scmtools.core import SCMClient
from reviewboard.scmtools.errors import FileNotFoundError, SCMError
from reviewboard.testing.testcase import TestCase


class GetFileHTTPResponse(object):
    def info(self):
        return {
            'Content-Type': 'text/plain',
        }

    def read(self):
        return b'abc'


class SCMClientTests(kgb.SpyAgency, TestCase):
    """Tests for reviewboard.scmtools.core.SCMClient."""

    def test_get_file_http(self):
        """Testing SCMClient.get_file_http"""
        self.spy_on(urlopen, op=kgb.SpyOpReturn(GetFileHTTPResponse()))

        client = SCMClient(path='/path/to/repo')

        self.assertEqual(client.get_file_http('https://example.com',
                                              path='/path/to/file',
                                              revision='abc123'),
                         b'abc')

    def test_get_file_http_with_username(self):
        """Testing SCMClient.get_file_http with username"""
        self.spy_on(urlopen, op=kgb.SpyOpReturn(GetFileHTTPResponse()))

        client = SCMClient(path='/path/to/repo',
                           username='test-user',
                           password='test-pass')

        self.assertEqual(client.get_file_http('https://example.com',
                                              path='/path/to/file',
                                              revision='abc123'),
                         b'abc')

        request = urlopen.last_call.args[0]
        self.assertEqual(request.headers[str('Authorization')],
                         str('Basic dGVzdC11c2VyOnRlc3QtcGFzcw=='))

    def test_get_file_http_with_mime_type_match(self):
        """Testing SCMClient.get_file_http with mime_type and match"""
        self.spy_on(urlopen, op=kgb.SpyOpReturn(GetFileHTTPResponse()))

        client = SCMClient(path='/path/to/repo')

        self.assertEqual(client.get_file_http('https://example.com',
                                              path='/path/to/file',
                                              revision='abc123',
                                              mime_type='text/plain'),
                         b'abc')

    def test_get_file_http_with_mime_type_no_match(self):
        """Testing SCMClient.get_file_http with mime_type and no match"""
        self.spy_on(urlopen, op=kgb.SpyOpReturn(GetFileHTTPResponse()))

        client = SCMClient(path='/path/to/repo')

        self.assertIsNone(client.get_file_http('https://example.com',
                                               path='/path/to/file',
                                               revision='abc123',
                                               mime_type='text/xxx'))

    def test_get_file_http_with_http_error(self):
        """Testing SCMClient.get_file_http with HTTPError"""
        self.spy_on(urlopen,
                    op=kgb.SpyOpRaise(HTTPError(url='https://example.com',
                                                code=500,
                                                msg='Kablam',
                                                hdrs=None,
                                                fp=None)))

        client = SCMClient(path='/path/to/repo')

        message = (
            'HTTP error code 500 when fetching file from https://example.com: '
            'HTTP Error 500: Kablam'
        )

        with self.assertRaisesMessage(SCMError, message) as ctx:
            client.get_file_http('https://example.com',
                                 path='/path/to/file',
                                 revision='abc123')

        self.assertNotIsInstance(ctx.exception, FileNotFoundError)

    def test_get_file_http_with_http_error_404(self):
        """Testing SCMClient.get_file_http with HTTPError 404"""
        self.spy_on(urlopen,
                    op=kgb.SpyOpRaise(HTTPError(url='https://example.com',
                                                code=404,
                                                msg=None,
                                                hdrs=None,
                                                fp=None)))

        client = SCMClient(path='/path/to/repo')

        with self.assertRaises(FileNotFoundError) as ctx:
            client.get_file_http('https://example.com',
                                 path='/path/to/file',
                                 revision='abc123')

        e = ctx.exception
        self.assertEqual(e.path, '/path/to/file')
        self.assertEqual(e.revision, 'abc123')
