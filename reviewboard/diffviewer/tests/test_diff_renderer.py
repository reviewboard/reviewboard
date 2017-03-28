from __future__ import unicode_literals

from django.http import HttpResponse
from django.test import RequestFactory
from djblets.cache.backend import cache_memoize
from kgb import SpyAgency

from reviewboard.diffviewer.errors import UserVisibleError
from reviewboard.diffviewer.models import FileDiff
from reviewboard.diffviewer.renderers import DiffRenderer
from reviewboard.testing import TestCase


class DiffRendererTests(SpyAgency, TestCase):
    """Unit tests for DiffRenderer."""

    def test_construction_with_invalid_chunks(self):
        """Testing DiffRenderer construction with invalid chunks"""
        diff_file = {
            'chunks': [{}],
            'filediff': None,
            'interfilediff': None,
            'force_interdiff': False,
            'chunks_loaded': True,
        }

        renderer = DiffRenderer(diff_file, chunk_index=-1)
        self.assertRaises(UserVisibleError,
                          lambda: renderer.render_to_string_uncached(None))

        renderer = DiffRenderer(diff_file, chunk_index=1)
        self.assertRaises(UserVisibleError,
                          lambda: renderer.render_to_string_uncached(None))

    def test_construction_with_valid_chunks(self):
        """Testing DiffRenderer construction with valid chunks"""
        diff_file = {
            'chunks': [{}],
            'chunks_loaded': True,
        }

        # Should not assert.
        renderer = DiffRenderer(diff_file, chunk_index=0)
        self.spy_on(renderer.render_to_string, call_original=False)
        self.spy_on(renderer.make_context, call_original=False)

        renderer.render_to_string_uncached(None)
        self.assertEqual(renderer.num_chunks, 1)
        self.assertEqual(renderer.chunk_index, 0)

    def test_render_to_response(self):
        """Testing DiffRenderer.render_to_response"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file)
        self.spy_on(renderer.render_to_string,
                    call_fake=lambda self, request: 'Foo')

        request_factory = RequestFactory()
        request = request_factory.get('/')
        response = renderer.render_to_response(request)

        self.assertTrue(renderer.render_to_string.called)
        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(response.content, 'Foo')

    def test_render_to_string(self):
        """Testing DiffRenderer.render_to_string"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file)
        self.spy_on(renderer.render_to_string_uncached,
                    call_fake=lambda self, request: 'Foo')
        self.spy_on(renderer.make_cache_key,
                    call_fake=lambda self: 'my-cache-key')
        self.spy_on(cache_memoize)

        request_factory = RequestFactory()
        request = request_factory.get('/')
        response = renderer.render_to_response(request)

        self.assertEqual(response.content, 'Foo')
        self.assertTrue(renderer.render_to_string_uncached.called)
        self.assertTrue(renderer.make_cache_key.called)
        self.assertTrue(cache_memoize.spy.called)

    def test_render_to_string_uncached(self):
        """Testing DiffRenderer.render_to_string_uncached"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file, lines_of_context=[5, 5])
        self.spy_on(renderer.render_to_string_uncached,
                    call_fake=lambda self, request: 'Foo')
        self.spy_on(renderer.make_cache_key,
                    call_fake=lambda self: 'my-cache-key')
        self.spy_on(cache_memoize)

        request_factory = RequestFactory()
        request = request_factory.get('/')
        response = renderer.render_to_response(request)

        self.assertEqual(response.content, 'Foo')
        self.assertTrue(renderer.render_to_string_uncached.called)
        self.assertFalse(renderer.make_cache_key.called)
        self.assertFalse(cache_memoize.spy.called)

    def test_make_context_with_chunk_index(self):
        """Testing DiffRenderer.make_context with chunk_index"""
        diff_file = {
            'newfile': True,
            'interfilediff': None,
            'filediff': FileDiff(),
            'chunks': [
                {
                    'lines': [],
                    'meta': {},
                    'change': 'insert',
                },
                {
                    # This is not how lines really look, but it's fine for
                    # current usage tests.
                    'lines': range(10),
                    'meta': {},
                    'change': 'replace',
                },
                {
                    'lines': [],
                    'meta': {},
                    'change': 'delete',
                }
            ],
        }

        renderer = DiffRenderer(diff_file, chunk_index=1)
        context = renderer.make_context()

        self.assertEqual(context['standalone'], True)
        self.assertEqual(context['file'], diff_file)
        self.assertEqual(len(diff_file['chunks']), 1)

        chunk = diff_file['chunks'][0]
        self.assertEqual(chunk['change'], 'replace')
