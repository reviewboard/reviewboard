from __future__ import unicode_literals

from django.utils.six.moves.urllib.parse import parse_qs, urlsplit
from kgb import SpyAgency

from reviewboard.hostingsvcs.utils.paginator import (APIPaginator,
                                                     InvalidPageError,
                                                     ProxyPaginator)
from reviewboard.testing import TestCase


class DummyAPIPaginator(APIPaginator):
    start_query_param = 'start'
    per_page_query_param = 'per-page'

    def fetch_url(self, url):
        return {
            'data': [1, 2, 3],
            'headers': {},
        }


class DummyMultiPageAPIPaginator(APIPaginator):
    def fetch_url(self, url):
        if url == 'http://example.com/':
            return {
                'data': ['a', 'b', 'c'],
                'per_page': 3,
                'total_count': 8,
                'next_url': 'http://example.com/?page=2',
            }
        elif url == 'http://example.com/?page=2':
            return {
                'data': ['d', 'e', 'f'],
                'per_page': 3,
                'total_count': 8,
                'prev_url': 'http://example.com/?page=1',
                'next_url': 'http://example.com/?page=3',
            }
        elif url == 'http://example.com/?page=3':
            return {
                'data': ['g', 'h'],
                'per_page': 3,
                'total_count': 8,
                'prev_url': 'http://example.com/?page=2',
            }
        else:
            self.fail('Unexpected URL %s' % url)


class BasePaginatorTests(SpyAgency, TestCase):
    """Unit tests for BasePaginator."""

    def test_iter_pages(self):
        """Testing BasePaginator.iter_pages"""
        paginator = DummyMultiPageAPIPaginator(client=None,
                                               url='http://example.com/')
        pages = list(paginator.iter_pages())

        self.assertEqual(len(pages), 3)
        self.assertEqual(pages[0], ['a', 'b', 'c'])
        self.assertEqual(pages[1], ['d', 'e', 'f'])
        self.assertEqual(pages[2], ['g', 'h'])

    def test_iter_pages_with_max_pages(self):
        """Testing BasePaginator.iter_pages with max_pages"""
        self.spy_on(DummyMultiPageAPIPaginator.fetch_url)

        paginator = DummyMultiPageAPIPaginator(client=None,
                                               url='http://example.com/')

        pages = list(paginator.iter_pages(max_pages=2))

        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0], ['a', 'b', 'c'])
        self.assertEqual(pages[1], ['d', 'e', 'f'])
        self.assertEqual(len(DummyMultiPageAPIPaginator.fetch_url.calls), 2)

    def test_iter_items(self):
        """Testing BasePaginator.iter_items"""
        paginator = DummyMultiPageAPIPaginator(client=None,
                                               url='http://example.com/')

        self.assertEqual(list(paginator.iter_items()),
                         ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])

    def test_iter_items_with_max_pages(self):
        """Testing BasePaginator.iter_items with max_pages"""
        self.spy_on(DummyMultiPageAPIPaginator.fetch_url)

        paginator = DummyMultiPageAPIPaginator(client=None,
                                               url='http://example.com/')

        self.assertEqual(list(paginator.iter_items(max_pages=2)),
                         ['a', 'b', 'c', 'd', 'e', 'f'])
        self.assertEqual(len(DummyMultiPageAPIPaginator.fetch_url.calls), 2)

    def test_iter(self):
        """Testing BasePaginator.__iter__"""
        paginator = DummyMultiPageAPIPaginator(client=None,
                                               url='http://example.com/')
        pages = list(iter(paginator))

        self.assertEqual(len(pages), 3)
        self.assertEqual(pages[0], ['a', 'b', 'c'])
        self.assertEqual(pages[1], ['d', 'e', 'f'])
        self.assertEqual(pages[2], ['g', 'h'])


class APIPaginatorTests(TestCase):
    """Tests for APIPaginator."""

    def test_construct_initial_load(self):
        """Testing APIPaginator construction performs initial load"""
        paginator = DummyAPIPaginator(None, 'http://example.com', start=10)
        self.assertEqual(paginator.page_data, [1, 2, 3])

    def test_construct_with_start(self):
        """Testing APIPaginator construction with start=<value>"""
        url = 'http://example.com/api/list/?foo=1'
        paginator = DummyAPIPaginator(
            client=None,
            url='http://example.com/api/list/?foo=1',
            start=10)
        query_params = paginator.request_kwargs['query']

        self.assertEqual(query_params['start'], 10)

    def test_construct_with_per_page(self):
        """Testing APIPaginator construction with per_page=<value>"""
        paginator = DummyAPIPaginator(
            client=None,
            url='http://example.com/api/list/?foo=1',
            per_page=10)
        query_params = paginator.request_kwargs['query']

        self.assertEqual(query_params['per-page'], 10)

    def test_extract_page_info(self):
        """Testing APIPaginator page information extraction"""
        class PageInfoAPIPaginator(APIPaginator):
            def fetch_url(self, url):
                return {
                    'data': ['a', 'b', 'c'],
                    'headers': {
                        'Foo': 'Bar',
                    },
                    'per_page': 10,
                    'total_count': 100,
                    'prev_url': 'http://example.com/?page=1',
                    'next_url': 'http://example.com/?page=3',
                }

        paginator = PageInfoAPIPaginator(client=None,
                                         url='http://example.com/')

        self.assertEqual(paginator.page_data, ['a', 'b', 'c'])
        self.assertEqual(paginator.page_headers['Foo'], 'Bar')
        self.assertEqual(paginator.per_page, 10)
        self.assertEqual(paginator.total_count, 100)
        self.assertEqual(paginator.prev_url, 'http://example.com/?page=1')
        self.assertEqual(paginator.next_url, 'http://example.com/?page=3')

    def test_prev(self):
        """Testing APIPaginator.prev"""
        prev_url = 'http://example.com/?page=1'

        paginator = DummyAPIPaginator(client=None,
                                      url='http://example.com')
        paginator.prev_url = prev_url

        self.assertTrue(paginator.has_prev)
        self.assertFalse(paginator.has_next)

        data = paginator.prev()

        self.assertEqual(data, [1, 2, 3])
        self.assertEqual(paginator.url, prev_url)

    def test_prev_without_prev_page(self):
        """Testing APIPaginator.prev without a previous page"""
        paginator = DummyAPIPaginator(client=None,
                                      url='http://example.com')
        url = paginator.url

        self.assertFalse(paginator.has_prev)
        self.assertRaises(InvalidPageError, paginator.prev)
        self.assertEqual(paginator.url, url)

    def test_next(self):
        """Testing APIPaginator.next"""
        next_url = 'http://example.com/?page=3'

        paginator = DummyAPIPaginator(client=None,
                                      url='http://example.com')
        paginator.next_url = next_url

        self.assertFalse(paginator.has_prev)
        self.assertTrue(paginator.has_next)

        data = paginator.next()

        self.assertEqual(data, [1, 2, 3])
        self.assertEqual(paginator.url, next_url)

    def test_next_without_next_page(self):
        """Testing APIPaginator.next without a next page"""
        paginator = DummyAPIPaginator(client=None,
                                      url='http://example.com')
        url = paginator.url

        self.assertFalse(paginator.has_next)
        self.assertRaises(InvalidPageError, paginator.next)
        self.assertEqual(paginator.url, url)


class ProxyPaginatorTests(TestCase):
    """Tests for ProxyPaginator."""

    def setUp(self):
        self.paginator = DummyAPIPaginator(client=None,
                                           url='http://example.com')
        self.proxy = ProxyPaginator(self.paginator)

    def test_has_prev(self):
        """Testing ProxyPaginator.has_prev"""
        self.assertFalse(self.proxy.has_prev)

        self.paginator.prev_url = 'http://example.com/?start=1'
        self.assertTrue(self.proxy.has_prev)

    def test_has_next(self):
        """Testing ProxyPaginator.has_next"""
        self.assertFalse(self.proxy.has_next)

        self.paginator.next_url = 'http://example.com/?start=2'
        self.assertTrue(self.proxy.has_next)

    def test_per_page(self):
        """Testing ProxyPaginator.per_page"""
        self.paginator.per_page = 10
        self.assertEqual(self.proxy.per_page, 10)

    def test_total_count(self):
        """Testing ProxyPaginator.total_count"""
        self.paginator.total_count = 100
        self.assertEqual(self.proxy.total_count, 100)

    def test_prev(self):
        """Testing ProxyPaginator.prev"""
        prev_url = 'http://example.com/?page=1'

        self.paginator.prev_url = prev_url

        self.assertTrue(self.proxy.has_prev)
        self.assertFalse(self.proxy.has_next)

        data = self.proxy.prev()

        self.assertEqual(data, [1, 2, 3])
        self.assertEqual(self.paginator.url, prev_url)

    def test_next(self):
        """Testing ProxyPaginator.next"""
        next_url = 'http://example.com/?page=3'

        self.paginator.next_url = next_url

        self.assertFalse(self.proxy.has_prev)
        self.assertTrue(self.proxy.has_next)

        data = self.proxy.next()

        self.assertEqual(data, [1, 2, 3])
        self.assertEqual(self.paginator.url, next_url)

    def test_normalize_page_data(self):
        """Testing ProxyPaginator.normalize_page_data"""
        proxy = ProxyPaginator(
            self.paginator,
            normalize_page_data_func=lambda data: list(reversed(data)))

        self.assertEqual(proxy.page_data, [3, 2, 1])

    def test_normalize_page_data_on_prev(self):
        """Testing ProxyPaginator.normalize_page_data on prev"""
        proxy = ProxyPaginator(
            self.paginator,
            normalize_page_data_func=lambda data: list(reversed(data)))
        self.paginator.prev_url = 'http://example.com/?page=1'

        data = proxy.prev()

        self.assertEqual(data, [3, 2, 1])

    def test_normalize_page_data_on_next(self):
        """Testing ProxyPaginator.normalize_page_data on next"""
        proxy = ProxyPaginator(
            self.paginator,
            normalize_page_data_func=lambda data: list(reversed(data)))
        self.paginator.next_url = 'http://example.com/?page=3'

        data = proxy.next()

        self.assertEqual(data, [3, 2, 1])
