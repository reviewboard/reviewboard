from __future__ import annotations

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory
from djblets.cache.backend import cache_memoize
from kgb import SpyAgency, SpyOpReturn

from reviewboard.diffviewer.chunk_generator import DiffChunkGenerator
from reviewboard.diffviewer.diffutils import populate_diff_chunks
from reviewboard.diffviewer.errors import UserVisibleError
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.renderers import DiffRenderer
from reviewboard.diffviewer.settings import DiffSettings
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

        diff_settings = DiffSettings.create()

        renderer = DiffRenderer(diff_file, chunk_index=-1,
                                diff_settings=diff_settings)
        self.assertRaises(UserVisibleError,
                          lambda: renderer.render_to_string_uncached(None))

        renderer = DiffRenderer(diff_file, chunk_index=1,
                                diff_settings=diff_settings)
        self.assertRaises(UserVisibleError,
                          lambda: renderer.render_to_string_uncached(None))

    def test_construction_with_valid_chunks(self):
        """Testing DiffRenderer construction with valid chunks"""
        diff_file = {
            'chunks': [{}],
            'chunks_loaded': True,
        }

        # Should not assert.
        renderer = DiffRenderer(diff_file, chunk_index=0,
                                diff_settings=DiffSettings.create())
        self.spy_on(renderer.render_to_string, call_original=False)
        self.spy_on(renderer.make_context, call_original=False)

        renderer.render_to_string_uncached(None)
        self.assertEqual(renderer.num_chunks, 1)
        self.assertEqual(renderer.chunk_index, 0)

    def test_construction_with_setting_syntax_highlighting_true(self):
        """Testing DiffRenderer construction with
        DiffSettings.syntax_highlighting=True
        """
        diff_file = {
            'chunks': [{}],
            'chunks_loaded': True,
        }

        diff_settings = DiffSettings.create(syntax_highlighting=True)

        renderer = DiffRenderer(diff_file,
                                chunk_index=0,
                                diff_settings=diff_settings)
        self.assertTrue(renderer.highlighting)

    def test_construction_with_setting_syntax_highlighting_false(self):
        """Testing DiffRenderer construction with
        DiffSettings.syntax_highlighting=False
        """
        diff_file = {
            'chunks': [{}],
            'chunks_loaded': True,
        }

        diff_settings = DiffSettings.create(syntax_highlighting=False)

        renderer = DiffRenderer(diff_file,
                                chunk_index=0,
                                diff_settings=diff_settings)
        self.assertFalse(renderer.highlighting)

    def test_render_to_response(self):
        """Testing DiffRenderer.render_to_response"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file, diff_settings=DiffSettings.create())
        self.spy_on(renderer.render_to_string,
                    call_fake=lambda self, request: 'Foo')

        request_factory = RequestFactory()
        request = request_factory.get('/')
        response = renderer.render_to_response(request)

        self.assertTrue(renderer.render_to_string.called)
        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(response.content, b'Foo')

    def test_render_to_string(self):
        """Testing DiffRenderer.render_to_string"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file, diff_settings=DiffSettings.create())
        self.spy_on(renderer.render_to_string_uncached,
                    call_fake=lambda self, request: 'Foo')
        self.spy_on(renderer.make_cache_key,
                    call_fake=lambda self: 'my-cache-key')
        self.spy_on(cache_memoize)

        request_factory = RequestFactory()
        request = request_factory.get('/')
        response = renderer.render_to_response(request)

        self.assertEqual(response.content, b'Foo')
        self.assertTrue(renderer.render_to_string_uncached.called)
        self.assertTrue(renderer.make_cache_key.called)
        self.assertTrue(cache_memoize.spy.called)

    def test_render_to_string_uncached(self):
        """Testing DiffRenderer.render_to_string_uncached"""
        diff_file = {
            'chunks': [{}]
        }

        renderer = DiffRenderer(diff_file, lines_of_context=[5, 5],
                                diff_settings=DiffSettings.create())
        self.spy_on(renderer.render_to_string_uncached,
                    call_fake=lambda self, request: 'Foo')
        self.spy_on(renderer.make_cache_key,
                    call_fake=lambda self: 'my-cache-key')
        self.spy_on(cache_memoize)

        request_factory = RequestFactory()
        request = request_factory.get('/')
        response = renderer.render_to_response(request)

        self.assertEqual(response.content, b'Foo')
        self.assertTrue(renderer.render_to_string_uncached.called)
        self.assertFalse(renderer.make_cache_key.called)
        self.assertFalse(cache_memoize.spy.called)

    def test_render_to_string_uncached_with_chunk_generator_cls(
        self,
    ) -> None:
        """Testing DiffRenderer.render_to_string_uncached with
        chunk_generator_cls
        """
        class MyChunkGenerator(DiffChunkGenerator):
            pass

        diff_file = {
            'chunks': [{}],
        }

        diff_settings = DiffSettings.create()
        renderer = DiffRenderer(diff_file,
                                diff_settings=diff_settings,
                                chunk_generator_cls=MyChunkGenerator)
        self.spy_on(populate_diff_chunks, call_original=False)
        self.spy_on(renderer.make_context, call_original=False)
        self.spy_on(render_to_string, op=SpyOpReturn(''))

        renderer.render_to_string_uncached(None)

        self.assertSpyCalledWith(populate_diff_chunks,
                                 files=[diff_file],
                                 request=None,
                                 diff_settings=diff_settings,
                                 chunk_generator_cls=MyChunkGenerator)

    def test_make_cache_key_with_chunk_generator_cls(self) -> None:
        """Testing DiffRenderer.make_cache_key with chunk_generator_cls"""
        class MyChunkGenerator(DiffChunkGenerator):
            pass

        diff_file = {
            'base_filediff': None,
            'filediff': FileDiff(pk=1, diffset=DiffSet(revision=1)),
            'force_interdiff': False,
            'index': 0,
        }

        diff_settings = DiffSettings.create()
        key = DiffRenderer(diff_file,
                           diff_settings=diff_settings).make_cache_key()
        key_with_cls = DiffRenderer(
            diff_file,
            diff_settings=diff_settings,
            chunk_generator_cls=MyChunkGenerator,
        ).make_cache_key()

        self.assertNotEqual(key, key_with_cls)
        self.assertIn(
            f'-{__name__}.{MyChunkGenerator.__qualname__}-',
            key_with_cls)

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

        renderer = DiffRenderer(diff_file, chunk_index=1,
                                diff_settings=DiffSettings.create())
        context = renderer.make_context()

        self.assertEqual(context['standalone'], True)
        self.assertEqual(context['file'], diff_file)
        self.assertEqual(len(diff_file['chunks']), 1)

        chunk = diff_file['chunks'][0]
        self.assertEqual(chunk['change'], 'replace')

    def test_make_context_with_filtered_interdiff_lines(self) -> None:
        """Testing DiffRenderer.make_context with lines_of_context and
        filtered interdiff lines
        """
        # Interdiffs can filter out opcodes, resulting in equal chunks where
        # the two sides have different numbers of lines. The lines at the end
        # of such a chunk have an empty line number on one side.
        meta = {
            'left_headers': [
                (1, 'def foo():'),
                (20, 'def bar():'),
            ],
            'right_headers': [
                (1, 'def foo():'),
                (5, 'def bar():'),
                (15, 'def baz():'),
            ],
        }

        lines = [
            [i, i, '', [], i, '', [], False]
            for i in range(1, 9)
        ]
        lines += [
            [i, i, '', [], '', '', [], False]
            for i in range(9, 11)
        ]

        diff_file = {
            'newfile': False,
            'interfilediff': None,
            'filediff': FileDiff(),
            'force_interdiff': True,
            'chunks': [
                {
                    'lines': [],
                    'meta': {},
                    'change': 'replace',
                },
                {
                    'lines': lines,
                    'meta': meta,
                    'change': 'equal',
                },
                {
                    'lines': [],
                    'meta': {},
                    'change': 'replace',
                },
            ],
        }

        renderer = DiffRenderer(diff_file,
                                chunk_index=1,
                                lines_of_context=[2, 0],
                                diff_settings=DiffSettings.create())

        # This is normally set in render_to_string_uncached().
        renderer.num_chunks = len(diff_file['chunks'])

        renderer.make_context()

        # The last line with a right-hand line number is line 8, so only the
        # header at line 15 must be filtered out.
        self.assertEqual(meta['left_headers'], [(1, 'def foo():')])
        self.assertEqual(
            meta['right_headers'],
            [
                (1, 'def foo():'),
                (5, 'def bar():'),
            ])
