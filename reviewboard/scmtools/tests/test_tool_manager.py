"""Unit tests for reviewboard.scmtools.managers.ToolManager."""

from __future__ import unicode_literals

from django.db.models import Q

from reviewboard.scmtools.models import Tool
from reviewboard.testing import TestCase


class ToolManagerTests(TestCase):
    """Unit tests for reviewboard.scmtools.managers.ToolManager."""

    fixtures = ['test_scmtools']

    def test_get_with_id_caches(self):
        """Testing Tool.objects.get with id= caches"""
        self._test_id_cache_query(id=1)

    def test_get_with_id_exact_caches(self):
        """Testing Tool.objects.get with id__exact= caches"""
        self._test_id_cache_query(id__exact=1)

    def test_get_with_pk_caches(self):
        """Testing Tool.objects.get with pk= caches"""
        self._test_id_cache_query(pk=1)

    def test_get_with_pk_exact_caches(self):
        """Testing Tool.objects.get with pk__exact= caches"""
        self._test_id_cache_query(pk=1)

    def test_get_with_q_id_caches(self):
        """Testing Tool.objects.get with Q(id=) caches"""
        self._test_id_cache_query(Q(id=1))

    def test_get_with_q_pk_caches(self):
        """Testing Tool.objects.get with Q(pk=) caches"""
        self._test_id_cache_query(Q(pk=1))

    def test_get_with_q_id_exact_caches(self):
        """Testing Tool.objects.get with Q(id__exact=) caches"""
        self._test_id_cache_query(Q(id__exact=1))

    def test_get_with_q_pk_exact_caches(self):
        """Testing Tool.objects.get with Q(pk__exact=) caches"""
        self._test_id_cache_query(Q(pk__exact=1))

    def test_get_non_id_lookup(self):
        """Testing Tool.objects.get with non-id/pk lookup"""
        with self.assertNumQueries(1):
            tool1 = Tool.objects.get(name='Git')

        with self.assertNumQueries(2):
            tool2 = Tool.objects.get(name='Git')
            tool3 = Tool.objects.get(name='CVS')

        self.assertIsNot(tool1, tool2)
        self.assertEqual(tool1, tool2)
        self.assertNotEqual(tool1, tool3)

    def _test_id_cache_query(self, *args, **kwargs):
        """Utility function for testing ID-based caching.

        Args:
            *args (tuple):
                Positional arguments to use for the query.

            **kwargs (dict):
                Keyword arguments to use for the query.

        Raises:
            AssertionError:
                An assertion failed.
        """
        Tool.objects.clear_tool_cache()

        with self.assertNumQueries(1):
            tool1 = Tool.objects.get(*args, **kwargs)

        with self.assertNumQueries(0):
            # Further queries for any available ID should reuse the cache.
            tools = [
                Tool.objects.get(id=1),
                Tool.objects.get(id__exact=1),
                Tool.objects.get(pk=1),
                Tool.objects.get(pk__exact=1),
                Tool.objects.get(Q(id=1)),
                Tool.objects.get(Q(id__exact=1)),
                Tool.objects.get(Q(pk=1)),
                Tool.objects.get(Q(pk__exact=1)),
            ]

            tool3 = Tool.objects.get(pk=2)

        for tool in tools:
            self.assertIs(tool1, tool)

        self.assertIsNot(tool1, tool3)
