from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _, get_language
from djblets.cache.backend import cache_memoize
from housekeeping.functions import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard70Warning
from reviewboard.diffviewer.chunk_generator import compute_chunk_last_header
from reviewboard.diffviewer.diffutils import populate_diff_chunks
from reviewboard.diffviewer.errors import UserVisibleError
from reviewboard.diffviewer.settings import DiffSettings


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

    ######################
    # Instance variables #
    ######################

    #: Settings used for the generation of the diff.
    #:
    #: Version Added:
    #:     5.0.2
    #:
    #: Type:
    #:     reviewboard.diffviewer.settings.DiffSettings
    diff_settings: DiffSettings

    @deprecate_non_keyword_only_args(RemovedInReviewBoard70Warning)
    def __init__(self,
                 diff_file,
                 *,
                 chunk_index=None,
                 collapse_all=True,
                 lines_of_context=None,
                 extra_context=None,
                 allow_caching=True,
                 template_name=default_template_name,
                 show_deleted=False,
                 diff_settings):
        """Initialize the renderer.

        Version Changed:
            6.0:
            * Removed the ``highlighting`` argument.
            * Made ``diff_settings`` mandatory.

        Version Changed:
            5.0.2:
            * Added ``diff_settings``, which will be required starting in
              Review Board 6.
            * Deprecated ``highlighting`` in favor of ``diff_settings``.

        Args:
            diff_file (dict):
                The diff file information to render.

            chunk_index (int, optional):
                The index of a specific chunk to render.

                Deprecated:
                    5.0.2:
                    This has been replaced with ``diff_settings``.

            collapse_all (bool, optional):
                Whether to collapse all chunks.

            lines_of_context (list of int, optional):
                The lines of context to include for the render.

                This can be a 1-item or 2-item list.

                If 1-item, the contents will represent the lines of context
                both before and after modified lines.

                If 2-item, the first item will be the lines of context before,
                and the second will be after.

            extra_context (dict, optional):
                Extra context data for the template.

            allow_caching (bool, optional):
                Whether to allow caching of the rendered content.

            template_name (str, optional):
                The name of the template used to render.

            show_deleted (bool, optional):
                Whether to show deleted file content.

            diff_settings (reviewboard.diffviewer.settings.DiffSettings):
                The settings used to control the display of diffs.

                Version Added:
                    5.0.2
        """
        self.diff_file = diff_file
        self.diff_settings = diff_settings
        self.chunk_index = chunk_index
        self.highlighting = diff_settings.syntax_highlighting
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
            populate_diff_chunks(files=[self.diff_file],
                                 request=request,
                                 diff_settings=self.diff_settings)

        if self.chunk_index is not None:
            assert not self.lines_of_context or self.collapse_all

            self.num_chunks = len(self.diff_file['chunks'])

            if self.chunk_index < 0 or self.chunk_index >= self.num_chunks:
                raise UserVisibleError(
                    _('Invalid chunk index %s specified.')
                    % self.chunk_index)

        rendered = render_to_string(template_name=self.template_name,
                                    context=self.make_context())

        # Ensure that we're actually returning a str. render_to_string gives us
        # a SafeString (which is an str subclass), but pickle chokes on that,
        # since it explicitly checks the instance type instead of using
        # isinstance. This causes an infinite recursion trying to call __str__
        # to turn it into an str, because SafeString.__str__ just returns self.
        return rendered[:]

    def make_cache_key(self):
        """Creates and returns a cache key representing the diff to render."""
        filediff = self.diff_file['filediff']
        base_filediff = self.diff_file['base_filediff']

        key = '%s-%s-%s-' % (self.template_name,
                             self.diff_file['index'],
                             filediff.diffset.revision)

        if base_filediff is not None:
            key += 'base-%s-' % base_filediff.pk

        if self.diff_file['force_interdiff']:
            interfilediff = self.diff_file['interfilediff']
            key += 'interdiff-%s-' % filediff.pk

            if interfilediff:
                key += str(interfilediff.pk)
            else:
                key += 'none'
        else:
            key += str(filediff.pk)

        if self.chunk_index is not None:
            key += '-chunk-%s' % self.chunk_index

        if self.collapse_all:
            key += '-collapsed'

        if self.show_deleted:
            key += '-show_deleted'

        key += '-%s-%s-%s' % (self.diff_settings.state_hash,
                              get_language(),
                              settings.TEMPLATE_SERIAL)

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
