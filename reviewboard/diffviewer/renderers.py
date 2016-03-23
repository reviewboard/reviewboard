from __future__ import unicode_literals

from django.conf import settings
from django.http import HttpResponse
from django.template import Context
from django.template.loader import render_to_string
from django.utils import six
from django.utils.translation import ugettext as _, get_language
from djblets.cache.backend import cache_memoize

from reviewboard.diffviewer.chunk_generator import compute_chunk_last_header
from reviewboard.diffviewer.diffutils import populate_diff_chunks
from reviewboard.diffviewer.errors import UserVisibleError


class DiffRenderer(object):
    """Renders a file's diffs.

    A DiffRenderer is constructed as needed and set up for render, and then
    thrown away. The rendered diff can show that of a whole file (in a
    collapsed or fully expanded state), or a particular chunk within a file.

    The rendered diff will be optimistically pulled out of cache, if it
    exists. Otherwise, a new one will be rendered and placed in the cache.

    The diff_file (from get_diff_files) is the only required parameter.
    The renderer may modify the contents of this, and should make a copy if
    it needs to be left untouched.

    Note that any of the render functions are meant to be called only once per
    DiffRenderer. It will alter the state of the renderer, possibly
    disrupting future render calls.
    """
    default_template_name = 'diffviewer/diff_file_fragment.html'

    def __init__(self, diff_file, chunk_index=None, highlighting=False,
                 collapse_all=True, lines_of_context=None, extra_context=None,
                 allow_caching=True, template_name=default_template_name,
                 show_deleted=False):
        self.diff_file = diff_file
        self.chunk_index = chunk_index
        self.highlighting = highlighting
        self.collapse_all = collapse_all
        self.lines_of_context = lines_of_context
        self.extra_context = extra_context or {}
        self.allow_caching = allow_caching
        self.template_name = template_name
        self.num_chunks = 0
        self.show_deleted = show_deleted

        if self.lines_of_context and len(self.lines_of_context) == 1:
            # If we only have one value, then assume it represents before
            # and after the collapsed header area.
            self.lines_of_context.append(self.lines_of_context[0])

    def render_to_response(self, request):
        """Renders the diff to an HttpResponse."""
        return HttpResponse(self.render_to_string(request))

    def render_to_string(self, request):
        """Returns the diff as a string.

        The resulting diff may optimistically be pulled from the cache, if
        not rendering a custom line range. This makes diff rendering very
        quick.

        If operating with a cache, and the diff doesn't exist in the cache,
        it will be stored after render.
        """
        cache = self.allow_caching and not self.lines_of_context

        if cache:
            return cache_memoize(
                self.make_cache_key(),
                lambda: self.render_to_string_uncached(request),
                large_data=True)
        else:
            return self.render_to_string_uncached(request)

    def render_to_string_uncached(self, request):
        """Renders a diff to a string without caching.

        This is a potentially expensive operation, and so is meant to be called
        only as often as necessary. render_to_string will call this if it's
        not already in the cache.
        """
        if not self.diff_file.get('chunks_loaded', False):
            populate_diff_chunks([self.diff_file], self.highlighting,
                                 request=request)

        if self.chunk_index is not None:
            assert not self.lines_of_context or self.collapse_all

            self.num_chunks = len(self.diff_file['chunks'])

            if self.chunk_index < 0 or self.chunk_index >= self.num_chunks:
                raise UserVisibleError(
                    _('Invalid chunk index %s specified.')
                    % self.chunk_index)

        return render_to_string(self.template_name,
                                Context(self.make_context()))

    def make_cache_key(self):
        """Creates and returns a cache key representing the diff to render."""
        filediff = self.diff_file['filediff']

        key = '%s-%s-%s-' % (self.template_name,
                             self.diff_file['index'],
                             filediff.diffset.revision)

        if self.diff_file['force_interdiff']:
            interfilediff = self.diff_file['interfilediff']
            key += 'interdiff-%s-' % filediff.pk

            if interfilediff:
                key += six.text_type(interfilediff.pk)
            else:
                key += 'none'
        else:
            key += six.text_type(filediff.pk)

        if self.chunk_index is not None:
            key += '-chunk-%s' % self.chunk_index

        if self.collapse_all:
            key += '-collapsed'

        if self.highlighting:
            key += '-highlighting'

        if self.show_deleted:
            key += '-show_deleted'

        key += '-%s-%s' % (get_language(), settings.TEMPLATE_SERIAL)

        return key

    def make_context(self):
        """Creates and returns context for a diff render."""
        context = self.extra_context.copy()

        if self.chunk_index is not None:
            # We're rendering a specific chunk within a file's diff, rather
            # than the whole diff.
            self.diff_file['chunks'] = \
                [self.diff_file['chunks'][self.chunk_index]]

            if self.lines_of_context:
                # We're rendering a specific range of lines within this chunk,
                # rather than the default range.
                chunk = self.diff_file['chunks'][0]
                lines = chunk['lines']
                num_lines = len(lines)
                new_lines = []

                total_lines_of_context = (self.lines_of_context[0] +
                                          self.lines_of_context[1])

                if total_lines_of_context >= num_lines:
                    # The lines of context we're expanding to would cover the
                    # entire chunk, so just expand the entire thing.
                    self.collapse_all = False
                else:
                    self.lines_of_context[0] = min(num_lines,
                                                   self.lines_of_context[0])
                    self.lines_of_context[1] = min(num_lines,
                                                   self.lines_of_context[1])

                    # The start of the collapsed header area.
                    collapse_i = 0

                    # Compute the start of the second chunk of code, after the
                    # header.
                    if self.chunk_index < self.num_chunks - 1:
                        chunk2_i = max(num_lines - self.lines_of_context[1], 0)
                    else:
                        chunk2_i = num_lines

                    meta = chunk['meta']

                    if self.lines_of_context[0] and self.chunk_index > 0:
                        # The chunk of context preceding the header.
                        collapse_i = self.lines_of_context[0]
                        self.diff_file['chunks'].insert(0, {
                            'change': chunk['change'],
                            'collapsable': False,
                            'index': self.chunk_index,
                            'lines': lines[:collapse_i],
                            'meta': meta,
                            'numlines': collapse_i,
                        })

                    # The header contents
                    new_lines += lines[collapse_i:chunk2_i]

                    if (self.chunk_index < self.num_chunks - 1 and
                            chunk2_i + self.lines_of_context[1] <= num_lines):
                        # The chunk of context after the header.
                        self.diff_file['chunks'].append({
                            'change': chunk['change'],
                            'collapsable': False,
                            'index': self.chunk_index,
                            'lines': lines[chunk2_i:],
                            'meta': meta,
                            'numlines': num_lines - chunk2_i,
                        })

                    if new_lines:
                        num_lines = len(new_lines)

                        chunk.update({
                            'lines': new_lines,
                            'numlines': num_lines,
                            'collapsable': True,
                        })

                        # Fix the headers to accommodate the new range.
                        if self.chunk_index < self.num_chunks - 1:
                            for prefix, index in (('left', 1), ('right', 4)):
                                meta[prefix + '_headers'] = [
                                    header
                                    for header in meta[prefix + '_headers']
                                    if header[0] <= new_lines[-1][index]
                                ]

                            meta['headers'] = \
                                compute_chunk_last_header(new_lines, num_lines,
                                                          meta)
                    else:
                        self.diff_file['chunks'].remove(chunk)

        equal_lines = 0

        for chunk in self.diff_file['chunks']:
            if chunk['change'] == 'equal':
                equal_lines += chunk['numlines']

        context.update({
            'collapseall': self.collapse_all,
            'file': self.diff_file,
            'lines_of_context': self.lines_of_context or (0, 0),
            'equal_lines': equal_lines,
            'standalone': self.chunk_index is not None,
            'show_deleted': self.show_deleted,
        })

        return context


_diff_renderer_class = DiffRenderer


def get_diff_renderer_class():
    """Returns the DiffRenderer class used for rendering diffs."""
    return _diff_renderer_class


def set_diff_renderer_class(renderer):
    """Sets the DiffRenderer class used for rendering diffs."""
    assert renderer

    globals()['_diff_renderer_class'] = renderer


def get_diff_renderer(*args, **kwargs):
    """Returns a DiffRenderer instance used for rendering diffs."""
    return _diff_renderer_class(*args, **kwargs)
