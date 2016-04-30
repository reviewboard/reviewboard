from __future__ import unicode_literals

import fnmatch
import functools
import hashlib
import re

from django.utils import six
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.six.moves import range
from django.utils.translation import get_language
from djblets.log import log_timed
from djblets.cache.backend import cache_memoize
from djblets.siteconfig.models import SiteConfiguration
from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.formatters import HtmlFormatter

from reviewboard.diffviewer.differ import DiffCompatVersion, get_differ
from reviewboard.diffviewer.diffutils import (get_line_changed_regions,
                                              get_original_file,
                                              get_patched_file,
                                              convert_to_unicode,
                                              split_line_endings)
from reviewboard.diffviewer.opcode_generator import (DiffOpcodeGenerator,
                                                     get_diff_opcode_generator)


class NoWrapperHtmlFormatter(HtmlFormatter):
    """An HTML Formatter for Pygments that doesn't wrap items in a div."""
    def __init__(self, *args, **kwargs):
        super(NoWrapperHtmlFormatter, self).__init__(*args, **kwargs)

    def _wrap_div(self, inner):
        """Removes the div wrapper from formatted code.

        This is called by the formatter to wrap the contents of inner.
        Inner is a list of tuples containing formatted code. If the first item
        in the tuple is zero, then it's the div wrapper, so we should ignore
        it.
        """
        for tup in inner:
            if tup[0]:
                yield tup


class RawDiffChunkGenerator(object):
    """A generator for chunks for a diff that can be used for rendering.

    Each chunk represents an insert, delete, replace, or equal section. It
    contains all the data needed to render the portion of the diff.

    This is general-purpose and meant to operate on strings each consisting of
    at least one line of text, or lists of lines of text.

    If the caller passes lists of lines instead of strings, then the
    caller will also be responsible for applying any syntax highlighting and
    dealing with newline differences.
    """

    NEWLINES_RE = re.compile(r'\r?\n')

    # The maximum size a line can be before we start shutting off styling.
    STYLED_MAX_LINE_LEN = 1000
    STYLED_MAX_LIMIT_BYTES = 200000  # 200KB

    # A list of filename extensions that won't be styled.
    STYLED_EXT_BLACKLIST = (
        '.txt',  # ResourceLexer is used as a default.
    )

    # Default tab size used in browsers.
    TAB_SIZE = DiffOpcodeGenerator.TAB_SIZE

    def __init__(self, old, new, orig_filename, modified_filename,
                 enable_syntax_highlighting=True, encoding_list=None,
                 diff_compat=DiffCompatVersion.DEFAULT):
        self.old = old
        self.new = new
        self.orig_filename = orig_filename
        self.modified_filename = modified_filename
        self.enable_syntax_highlighting = enable_syntax_highlighting
        self.encoding_list = encoding_list or ['iso-8859-15']
        self.diff_compat = diff_compat
        self.differ = None

        # Chunk processing state.
        self._last_header = [None, None]
        self._last_header_index = [0, 0]
        self._chunk_index = 0

    def get_opcode_generator(self):
        """Return the DiffOpcodeGenerator used to generate diff opcodes."""
        return get_diff_opcode_generator(self.differ)

    def get_chunks(self, cache_key=None):
        """Return the chunks for the given diff information.

        If a cache key is provided and there are chunks already computed in the
        cache, they will be yielded. Otherwise, new chunks will be generated,
        stored in cache (given a cache key), and yielded.
        """
        if cache_key:
            chunks = cache_memoize(cache_key,
                                   lambda: list(self.get_chunks_uncached()),
                                   large_data=True)
        else:
            chunks = self.get_chunks_uncached()

        for chunk in chunks:
            yield chunk

    def get_chunks_uncached(self):
        """Yield the list of chunks, bypassing the cache."""
        for chunk in self.generate_chunks(self.old, self.new):
            yield chunk

    def generate_chunks(self, old, new):
        """Generate chunks for the difference between two strings.

        The strings will be normalized, ensuring they're of the proper
        encoding and ensuring they have consistent newlines. They're then
        syntax-highlighted (if requested).

        Once the strings are ready, chunks are built from the strings and
        yielded to the caller. Each chunk represents information on an
        equal, inserted, deleted, or replaced set of lines.

        The number of lines of each chunk type are stored in the
        :py:attr:`counts` dictionary, which can then be accessed after
        yielding all chunks.
        """
        is_lists = isinstance(old, list)
        assert is_lists == isinstance(new, list)

        if is_lists:
            if self.encoding_list:
                old = self.normalize_source_list(old)
                new = self.normalize_source_list(new)

            a = old
            b = new
        else:
            old, a = self.normalize_source_string(old)
            new, b = self.normalize_source_string(new)

        a_num_lines = len(a)
        b_num_lines = len(b)

        if is_lists:
            markup_a = a
            markup_b = b
        else:
            markup_a = None
            markup_b = None

            if self._get_enable_syntax_highlighting(old, new, a, b):
                source_file = \
                    self.normalize_path_for_display(self.orig_filename)
                dest_file = \
                    self.normalize_path_for_display(self.modified_filename)

                try:
                    # TODO: Try to figure out the right lexer for these files
                    #       once instead of twice.
                    if not source_file.endswith(self.STYLED_EXT_BLACKLIST):
                        markup_a = self._apply_pygments(old or '', source_file)

                    if not dest_file.endswith(self.STYLED_EXT_BLACKLIST):
                        markup_b = self._apply_pygments(new or '', dest_file)
                except:
                    pass

            if not markup_a:
                markup_a = self.NEWLINES_RE.split(escape(old))

            if not markup_b:
                markup_b = self.NEWLINES_RE.split(escape(new))

        siteconfig = SiteConfiguration.objects.get_current()
        ignore_space = True

        for pattern in siteconfig.get('diffviewer_include_space_patterns'):
            if fnmatch.fnmatch(self.orig_filename, pattern):
                ignore_space = False
                break

        self.differ = get_differ(a, b, ignore_space=ignore_space,
                                 compat_version=self.diff_compat)
        self.differ.add_interesting_lines_for_headers(self.orig_filename)

        context_num_lines = siteconfig.get("diffviewer_context_num_lines")
        collapse_threshold = 2 * context_num_lines + 3

        line_num = 1
        opcodes_generator = self.get_opcode_generator()

        counts = {
            'equal': 0,
            'replace': 0,
            'insert': 0,
            'delete': 0,
        }

        for tag, i1, i2, j1, j2, meta in opcodes_generator:
            old_lines = markup_a[i1:i2]
            new_lines = markup_b[j1:j2]
            num_lines = max(len(old_lines), len(new_lines))

            lines = map(functools.partial(self._diff_line, tag, meta),
                        range(line_num, line_num + num_lines),
                        range(i1 + 1, i2 + 1), range(j1 + 1, j2 + 1),
                        a[i1:i2], b[j1:j2], old_lines, new_lines)

            counts[tag] += num_lines

            if tag == 'equal' and num_lines > collapse_threshold:
                last_range_start = num_lines - context_num_lines

                if line_num == 1:
                    yield self._new_chunk(lines, 0, last_range_start, True)
                    yield self._new_chunk(lines, last_range_start, num_lines)
                else:
                    yield self._new_chunk(lines, 0, context_num_lines)

                    if i2 == a_num_lines and j2 == b_num_lines:
                        yield self._new_chunk(lines, context_num_lines,
                                              num_lines, True)
                    else:
                        yield self._new_chunk(lines, context_num_lines,
                                              last_range_start, True)
                        yield self._new_chunk(lines, last_range_start,
                                              num_lines)
            else:
                yield self._new_chunk(lines, 0, num_lines, False, tag, meta)

            line_num += num_lines

        self.counts = counts

    def normalize_source_string(self, s):
        """Normalize a source string of text to use for the diff.

        This will normalize the encoding of the string and the newlines,
        returning a tuple containing the normalized string and a list of
        lines split from the source.

        Both the original and modified strings used for the diff will be
        normalized independently.

        This is only used if the caller passes a string instead of a list for
        the original or new values.

        Subclasses can override this to provide custom behavior.
        """
        s = convert_to_unicode(s, self.encoding_list)[1]

        # Normalize the input so that if there isn't a trailing newline, we
        # add it.
        if s and not s.endswith('\n'):
            s += '\n'

        lines = self.NEWLINES_RE.split(s or '')

        # Remove the trailing newline, now that we've split this. This will
        # prevent a duplicate line number at the end of the diff.
        del lines[-1]

        return s, lines

    def normalize_source_list(self, l):
        """Normalize a list of source lines to use for the diff.

        This will normalize the encoding of the lines.

        Both the original and modified lists of lines used for the diff will be
        normalized independently.

        This is only used if the caller passes a list instead of a string for
        the original or new values.

        Subclasses can override this to provide custom behavior.
        """
        if self.encoding_list:
            l = [
                convert_to_unicode(s, self.encoding_list)[1]
                for s in l
            ]

        return l

    def normalize_path_for_display(self, filename):
        """Normalize a file path for display to the user.

        By default, this returns the filename as-is. Subclasses can override
        the behavior to return a variant of the filename.
        """
        return filename

    def get_line_changed_regions(self, old_line_num, old_line,
                                 new_line_num, new_line):
        """Return information on changes between two lines.

        This returns a tuple containing a list of tuples of ranges in the
        old line, and a list of tuples of ranges in the new line, that
        should be highlighted.

        This defaults to simply wrapping get_line_changed_regions() from
        diffutils. Subclasses can override to provide custom behavior.
        """
        return get_line_changed_regions(old_line, new_line)

    def _get_enable_syntax_highlighting(self, old, new, a, b):
        """Returns whether or not we'll be enabling syntax highlighting.

        This is based first on the value received when constructing the
        generator, and then based on heuristics to determine if it's fast
        enough to render with syntax highlighting on.

        The heuristics take into account the size of the files in bytes and
        the number of lines.
        """
        if not self.enable_syntax_highlighting:
            return False

        siteconfig = SiteConfiguration.objects.get_current()
        threshold = siteconfig.get('diffviewer_syntax_highlighting_threshold')

        if threshold and (len(a) > threshold or len(b) > threshold):
            return False

        # Very long files, especially XML files, can take a long time to
        # highlight. For files over a certain size, don't highlight them.
        if (len(old) > self.STYLED_MAX_LIMIT_BYTES or
                len(new) > self.STYLED_MAX_LIMIT_BYTES):
            return False

        # Don't style the file if we have any *really* long lines.
        # It's likely a minified file or data or something that doesn't
        # need styling, and it will just grind Review Board to a halt.
        for lines in (a, b):
            for line in lines:
                if len(line) > self.STYLED_MAX_LINE_LEN:
                    return False

        return True

    def _diff_line(self, tag, meta, v_line_num, old_line_num, new_line_num,
                   old_line, new_line, old_markup, new_markup):
        """Creates a single line in the diff viewer.

        Information on the line will be returned, and later will be used
        for rendering the line. The line represents a single row of a
        side-by-side diff. It contains a row number, real line numbers,
        region information, syntax-highlighted HTML for the text,
        and other metadata.
        """
        if (tag == 'replace' and
            old_line and new_line and
            len(old_line) <= self.STYLED_MAX_LINE_LEN and
            len(new_line) <= self.STYLED_MAX_LINE_LEN and
            old_line != new_line):
            # Generate information on the regions that changed between the
            # two lines.
            old_region, new_region = \
                self.get_line_changed_regions(old_line_num, old_line,
                                              new_line_num, new_line)
        else:
            old_region = new_region = []

        old_markup = old_markup or ''
        new_markup = new_markup or ''

        line_pair = (old_line_num, new_line_num)

        indentation_changes = meta.get('indentation_changes', {})

        if line_pair[0] is not None and line_pair[1] is not None:
            indentation_change = indentation_changes.get('%d-%d' % line_pair)

            if indentation_change:
                old_markup, new_markup = self._highlight_indentation(
                    old_markup, new_markup, *indentation_change)

        result = [
            v_line_num,
            old_line_num or '', mark_safe(old_markup), old_region,
            new_line_num or '', mark_safe(new_markup), new_region,
            line_pair in meta['whitespace_lines']
        ]

        moved_info = {}

        if old_line_num and old_line_num in meta.get('moved-to', {}):
            moved_info['to'] = (
                meta['moved-to'][old_line_num],
                old_line_num - 1 not in meta['moved-to'],
            )

        if new_line_num and new_line_num in meta.get('moved-from', {}):
            moved_info['from'] = (
                meta['moved-from'][new_line_num],
                new_line_num - 1 not in meta['moved-from'],
            )

        if moved_info:
            result.append(moved_info)

        return result

    def _highlight_indentation(self, old_markup, new_markup, is_indent,
                               raw_indent_len, norm_indent_len_diff):
        """Highlights indentation in an HTML-formatted line.

        This will wrap the indentation in <span> tags, and format it in
        a way that makes it clear how many spaces or tabs were used.
        """
        if is_indent:
            new_markup = self._wrap_indentation_chars(
                'indent',
                new_markup,
                raw_indent_len,
                norm_indent_len_diff,
                self._serialize_indentation)
        else:
            old_markup = self._wrap_indentation_chars(
                'unindent',
                old_markup,
                raw_indent_len,
                norm_indent_len_diff,
                self._serialize_unindentation)

        return old_markup, new_markup

    def _wrap_indentation_chars(self, class_name, markup, raw_indent_len,
                                norm_indent_len_diff, serializer):
        """Wraps characters in a string with indentation markers.

        This will insert the indentation markers and its wrapper in the
        markup string. It's careful not to interfere with any tags that
        may be used to highlight that line.
        """
        start_pos = 0

        # There may be a tag wrapping this whitespace. If so, we need to
        # find where the actual whitespace chars begin.
        while markup[start_pos] == '<':
            end_tag_pos = markup.find('>', start_pos + 1)

            # We'll only reach this if some corrupted HTML was generated.
            # We want to know about that.
            assert end_tag_pos != -1

            start_pos = end_tag_pos + 1

        end_pos = start_pos + raw_indent_len

        indentation = markup[start_pos:end_pos]

        if indentation.strip() != '':
            # There may be other things in here we didn't expect. It's not
            # a straight sequence of characters. Give up on highlighting it.
            return markup

        serialized, remainder = serializer(indentation, norm_indent_len_diff)

        return '%s<span class="%s">%s</span>%s' % (
            markup[:start_pos],
            class_name,
            serialized,
            remainder + markup[end_pos:])

    def _serialize_indentation(self, chars, norm_indent_len_diff):
        """Serializes an indentation string into an HTML representation.

        This will show every space as ">", and every tab as "------>|".
        In the case of tabs, we display as much of it as possible (anchoring
        to the right-hand side) given the space we have within the tab
        boundary.
        """
        s = ''
        i = 0

        for j, c in enumerate(chars):
            if c == ' ':
                s += '&gt;'
                i += 1
            elif c == '\t':
                # Build "------>|" with the room we have available.
                in_tab_pos = i % self.TAB_SIZE

                if in_tab_pos < self.TAB_SIZE - 1:
                    if in_tab_pos < self.TAB_SIZE - 2:
                        num_dashes = (self.TAB_SIZE - 2 - in_tab_pos)
                        s += '&mdash;' * num_dashes
                        i += num_dashes

                    s += '&gt;'
                    i += 1

                s += '|'
                i += 1

            if i >= norm_indent_len_diff:
                break

        return s, chars[j + 1:]

    def _serialize_unindentation(self, chars, norm_indent_len_diff):
        """Serializes an unindentation string into an HTML representation.

        This will show every space as "<", and every tab as "|<------".
        In the case of tabs, we display as much of it as possible (anchoring
        to the left-hand side) given the space we have within the tab
        boundary.
        """
        s = ''
        i = 0

        for j, c in enumerate(chars):
            if c == ' ':
                s += '&lt;'
                i += 1
            elif c == '\t':
                # Build "|<------" with the room we have available.
                in_tab_pos = i % self.TAB_SIZE

                s += '|'
                i += 1

                if in_tab_pos < self.TAB_SIZE - 1:
                    s += '&lt;'
                    i += 1

                    if in_tab_pos < self.TAB_SIZE - 2:
                        num_dashes = (self.TAB_SIZE - 2 - in_tab_pos)
                        s += '&mdash;' * num_dashes
                        i += num_dashes

            if i >= norm_indent_len_diff:
                break

        return s, chars[j + 1:]

    def _new_chunk(self, all_lines, start, end, collapsable=False,
                   tag='equal', meta=None):
        """Creates a chunk.

        A chunk represents an insert, delete, or equal region. The chunk
        contains a bunch of metadata for things like whether or not it's
        collapsable and any header information.

        This is what ends up being returned to the caller of this class.
        """
        if not meta:
            meta = {}

        left_headers = list(self._get_interesting_headers(
            all_lines, start, end - 1, False))
        right_headers = list(self._get_interesting_headers(
            all_lines, start, end - 1, True))

        meta['left_headers'] = left_headers
        meta['right_headers'] = right_headers

        lines = all_lines[start:end]
        num_lines = len(lines)

        compute_chunk_last_header(lines, num_lines, meta, self._last_header)

        if (collapsable and end < len(all_lines) and
                (self._last_header[0] or self._last_header[1])):
            meta['headers'] = list(self._last_header)

        chunk = {
            'index': self._chunk_index,
            'lines': lines,
            'numlines': num_lines,
            'change': tag,
            'collapsable': collapsable,
            'meta': meta,
        }

        self._chunk_index += 1

        return chunk

    def _get_interesting_headers(self, lines, start, end, is_modified_file):
        """Returns all headers for a region of a diff.

        This scans for all headers that fall within the specified range
        of the specified lines on both the original and modified files.
        """
        possible_functions = \
            self.differ.get_interesting_lines('header', is_modified_file)

        if not possible_functions:
            raise StopIteration

        try:
            if is_modified_file:
                last_index = self._last_header_index[1]
                i1 = lines[start][4]
                i2 = lines[end - 1][4]
            else:
                last_index = self._last_header_index[0]
                i1 = lines[start][1]
                i2 = lines[end - 1][1]
        except IndexError:
            raise StopIteration

        for i in range(last_index, len(possible_functions)):
            linenum, line = possible_functions[i]
            linenum += 1

            if linenum > i2:
                break
            elif linenum >= i1:
                last_index = i
                yield linenum, line

        if is_modified_file:
            self._last_header_index[1] = last_index
        else:
            self._last_header_index[0] = last_index

    def _apply_pygments(self, data, filename):
        """Applies Pygments syntax-highlighting to a file's contents.

        The resulting HTML will be returned as a list of lines.
        """
        lexer = guess_lexer_for_filename(filename,
                                         data,
                                         stripnl=False,
                                         encoding='utf-8')
        lexer.add_filter('codetagify')

        return split_line_endings(
            highlight(data, lexer, NoWrapperHtmlFormatter()))


class DiffChunkGenerator(RawDiffChunkGenerator):
    """A generator for chunks for a FileDiff that can be used for rendering.

    Each chunk represents an insert, delete, replace, or equal section. It
    contains all the data needed to render the portion of the diff.

    There are three ways this can operate, based on provided parameters.

    1) filediff, no interfilediff -
       Returns chunks for a single filediff. This is the usual way
       people look at diffs in the diff viewer.

       In this mode, we get the original file based on the filediff
       and then patch it to get the resulting file.

       This is also used for interdiffs where the source revision
       has no equivalent modified file but the interdiff revision
       does. It's no different than a standard diff.

    2) filediff, interfilediff -
       Returns chunks showing the changes between a source filediff
       and the interdiff.

       This is the typical mode used when showing the changes
       between two diffs. It requires that the file is included in
       both revisions of a diffset.

    3) filediff, no interfilediff, force_interdiff -
       Returns chunks showing the changes between a source
       diff and an unmodified version of the diff.

       This is used when the source revision in the diffset contains
       modifications to a file which have then been reverted in the
       interdiff revision. We don't actually have an interfilediff
       in this case, so we have to indicate that we are indeed in
       interdiff mode so that we can special-case this and not
       grab a patched file for the interdiff version.
    """

    def __init__(self, request, filediff, interfilediff=None,
                 force_interdiff=False, enable_syntax_highlighting=True):
        assert filediff

        self.request = request
        self.diffset = filediff.diffset
        self.filediff = filediff
        self.interfilediff = interfilediff
        self.force_interdiff = force_interdiff
        self.repository = self.diffset.repository
        self.tool = self.repository.get_scmtool()

        super(DiffChunkGenerator, self).__init__(
            old=None,
            new=None,
            orig_filename=filediff.source_file,
            modified_filename=filediff.dest_file,
            enable_syntax_highlighting=enable_syntax_highlighting,
            encoding_list=self.repository.get_encoding_list(),
            diff_compat=filediff.diffset.diffcompat)

    def make_cache_key(self):
        """Create a cache key for any generated chunks."""
        key = 'diff-sidebyside-'

        if self.enable_syntax_highlighting:
            key += 'hl-'

        if not self.force_interdiff:
            key += six.text_type(self.filediff.pk)
        elif self.interfilediff:
            key += 'interdiff-%s-%s' % (self.filediff.pk,
                                        self.interfilediff.pk)
        else:
            key += 'interdiff-%s-none' % self.filediff.pk

        key += '-%s' % get_language()

        return key

    def get_opcode_generator(self):
        """Return the DiffOpcodeGenerator used to generate diff opcodes."""
        diff = self.filediff.diff

        if self.interfilediff:
            interdiff = self.interfilediff.diff
        else:
            interdiff = None

        return get_diff_opcode_generator(self.differ, diff, interdiff)

    def get_chunks(self):
        """Return the chunks for the given diff information.

        If the file is binary or is an added or deleted 0-length file, or if
        the file has moved with no additional changes, then an empty list of
        chunks will be returned.

        If there are chunks already computed in the cache, they will be
        yielded. Otherwise, new chunks will be generated, stored in cache,
        and yielded.
        """
        counts = self.filediff.get_line_counts()

        if (self.filediff.binary or
            self.filediff.source_revision == '' or
            ((self.filediff.is_new or self.filediff.deleted or
              self.filediff.moved or self.filediff.copied) and
             counts['raw_insert_count'] == 0 and
             counts['raw_delete_count'] == 0)):
            raise StopIteration

        cache_key = self.make_cache_key()

        for chunk in super(DiffChunkGenerator, self).get_chunks(cache_key):
            yield chunk

    def get_chunks_uncached(self):
        """Yield the list of chunks, bypassing the cache."""
        old = get_original_file(self.filediff, self.request,
                                self.encoding_list)
        new = get_patched_file(old, self.filediff, self.request)

        if self.filediff.orig_sha1 is None:
            self.filediff.extra_data.update({
                'orig_sha1': self._get_checksum(old),
                'patched_sha1': self._get_checksum(new),
            })
            self.filediff.save(update_fields=['extra_data'])

        if self.interfilediff:
            old = new
            interdiff_orig = get_original_file(self.interfilediff,
                                               self.request,
                                               self.encoding_list)
            new = get_patched_file(interdiff_orig, self.interfilediff,
                                   self.request)

            if self.interfilediff.orig_sha1 is None:
                self.interfilediff.extra_data.update({
                    'orig_sha1': self._get_checksum(interdiff_orig),
                    'patched_sha1': self._get_checksum(new),
                })
                self.interfilediff.save(update_fields=['extra_data'])
        elif self.force_interdiff:
            # Basically, revert the change.
            old, new = new, old

        if self.interfilediff:
            log_timer = log_timed(
                "Generating diff chunks for interdiff ids %s-%s (%s)" %
                (self.filediff.id, self.interfilediff.id,
                 self.filediff.source_file),
                request=self.request)
        else:
            log_timer = log_timed(
                "Generating diff chunks for self.filediff id %s (%s)" %
                (self.filediff.id, self.filediff.source_file),
                request=self.request)

        for chunk in self.generate_chunks(old, new):
            yield chunk

        log_timer.done()

        if not self.interfilediff and not self.force_interdiff:
            insert_count = self.counts['insert']
            delete_count = self.counts['delete']
            replace_count = self.counts['replace']
            equal_count = self.counts['equal']

            self.filediff.set_line_counts(
                insert_count=insert_count,
                delete_count=delete_count,
                replace_count=replace_count,
                equal_count=equal_count,
                total_line_count=(insert_count + delete_count +
                                  replace_count + equal_count))

    def normalize_path_for_display(self, filename):
        return self.tool.normalize_path_for_display(filename)

    def _get_checksum(self, content):
        hasher = hashlib.sha1()
        hasher.update(content)
        return hasher.hexdigest()


def compute_chunk_last_header(lines, numlines, meta, last_header=None):
    """Computes information for the displayed function/class headers.

    This will record the displayed headers, their line numbers, and expansion
    offsets relative to the header's collapsed line range.

    The last_header variable, if provided, will be modified, which is
    important when processing several chunks at once. It will also be
    returned as a convenience.
    """
    if last_header is None:
        last_header = [None, None]

    line = lines[0]

    for i, (linenum, header_key) in enumerate([(line[1], 'left_headers'),
                                               (line[4], 'right_headers')]):
        headers = meta[header_key]

        if headers:
            header = headers[-1]
            last_header[i] = {
                'line': header[0],
                'text': header[1].strip(),
            }

    return last_header


_generator = DiffChunkGenerator


def get_diff_chunk_generator_class():
    """Returns the DiffChunkGenerator class used for generating chunks."""
    return _generator


def set_diff_chunk_generator_class(renderer):
    """Sets the DiffChunkGenerator class used for generating chunks."""
    assert renderer

    globals()['_generator'] = renderer


def get_diff_chunk_generator(*args, **kwargs):
    """Returns a DiffChunkGenerator instance used for generating chunks."""
    return _generator(*args, **kwargs)
