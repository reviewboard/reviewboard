from __future__ import unicode_literals

from django.core.cache import cache

from djblets.cache.backend import (cache_memoize, make_cache_key,
                                   CACHE_CHUNK_SIZE)
from djblets.testing.testcases import TestCase


class CacheTests(TestCase):
    def tearDown(self):
        cache.clear()

    def test_cache_memoize(self):
        """Testing cache_memoize"""
        cacheKey = "abc123"
        testStr = "Test 123"

        def cacheFunc(cacheCalled=[]):
            self.assertTrue(not cacheCalled)
            cacheCalled.append(True)
            return testStr

        result = cache_memoize(cacheKey, cacheFunc)
        self.assertEqual(result, testStr)

        # Call a second time. We should only call cacheFunc once.
        result = cache_memoize(cacheKey, cacheFunc)
        self.assertEqual(result, testStr)

    def test_cache_memoize_large_files(self):
        """Testing cache_memoize with large files"""
        cacheKey = "abc123"

        # This takes into account the size of the pickle data, and will
        # get us to exactly 2 chunks of data in cache.
        data = 'x' * (CACHE_CHUNK_SIZE * 2 - 8)

        def cacheFunc(cacheCalled=[]):
            self.assertTrue(not cacheCalled)
            cacheCalled.append(True)
            return data

        result = cache_memoize(cacheKey, cacheFunc, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)

        self.assertTrue(make_cache_key(cacheKey) in cache)
        self.assertTrue(make_cache_key('%s-0' % cacheKey) in cache)
        self.assertTrue(make_cache_key('%s-1' % cacheKey) in cache)
        self.assertFalse(make_cache_key('%s-2' % cacheKey) in cache)

        result = cache_memoize(cacheKey, cacheFunc, large_data=True,
                               compress_large_data=False)
        self.assertEqual(result, data)
