import fnmatch
import re
from difflib import SequenceMatcher

from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from djblets.log import log_timed
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.misc import cache_memoize
from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

from reviewboard.diffviewer.differ import get_differ
from reviewboard.diffviewer.diffutils import get_original_file, \
                                             get_patched_file
from reviewboard.diffviewer.opcode_generator import get_diff_opcode_generator


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


class DiffChunkGenerator(object):
    """Generates chunks for a diff that can be used for rendering.

    Each chunk represents an insert, delete or equal section. It contains
    all the data needed to render the portion of the diff.

    There are three ways this can operate, based on provided parameters.

    1) filediff, no interfilediff
       - Returns chunks for a single filediff. This is the usual way
         people look at diffs in the diff viewer.

         In this mode, we get the original file based on the filediff
         and then patch it to get the resulting file.

         This is also used for interdiffs where the source revision
         has no equivalent modified file but the interdiff revision
         does. It's no different than a standard diff.

    2) filediff, interfilediff
       - Returns chunks showing the changes between a source filediff
         and the interdiff.

         This is the typical mode used when showing the changes
         between two diffs. It requires that the file is included in
         both revisions of a diffset.

    3) filediff, no interfilediff, force_interdiff
       - Returns chunks showing the changes between a source
         diff and an unmodified version of the diff.

         This is used when the source revision in the diffset contains
         modifications to a file which have then been reverted in the
         interdiff revision. We don't actually have an interfilediff
         in this case, so we have to indicate that we are indeed in
         interdiff mode so that we can special-case this and not
         grab a patched file for the interdiff version.
    """
    NEWLINES_RE = re.compile(r'\r?\n')

    # The maximum size a line can be before we start shutting off styling.
    STYLED_MAX_LINE_LEN = 1000
    STYLED_MAX_LIMIT_BYTES = 200000  # 200KB

    def __init__(self, request, filediff, interfilediff=None,
                 force_interdiff=False, enable_syntax_highlighting=True):
        assert filediff

        self.request = request
        self.diffset = filediff.diffset
        self.filediff = filediff
        self.interfilediff = interfilediff
        self.force_interdiff = force_interdiff
        self.enable_syntax_highlighting = enable_syntax_highlighting
        self.differ = None

        self.filename = filediff.source_file

        # Chunk processing state.
        self._last_header = [None, None]
        self._last_header_index = [0, 0]
        self._cur_meta = {}
        self._chunk_index = 0

    def make_cache_key(self):
        """Creates a cache key for any generated chunks."""
        key = 'diff-sidebyside-'

        if self.enable_syntax_highlighting:
            key += 'hl-'

        if not self.force_interdiff:
            key += str(self.filediff.pk)
        elif self.interfilediff:
            key += 'interdiff-%s-%s' % (self.filediff.pk,
                                        self.interfilediff.pk)
        else:
            key += 'interdiff-%s-none' % self.filediff.pk

        return key

    def get_chunks(self):
        """Returns the chunks for the given diff information.

        If the file is binary or deleted, or if the file has moved with no
        additional changes, then an empty list of chunks will be returned.

        If there are chunks already computed in the cache, they will be
        returned. Otherwise, new chunks will be generated, stored in cache,
        and returned.
        """
        if (self.filediff.binary or
            self.filediff.deleted or
            self.filediff.source_revision == ''):
            return []

        return cache_memoize(self.make_cache_key(),
                             lambda: list(self._get_chunks_uncached()),
                             large_data=True)

    def _get_chunks_uncached(self):
        """Returns the list of chunks, bypassing the cache."""
        old = get_original_file(self.filediff, self.request)
        new = get_patched_file(old, self.filediff, self.request)

        if self.interfilediff:
            old = new
            interdiff_orig = get_original_file(self.interfilediff,
                                               self.request)
            new = get_patched_file(interdiff_orig, self.interfilediff,
                                   self.request)
        elif self.force_interdiff:
            # Basically, revert the change.
            old, new = new, old

        encoding = self.diffset.repository.encoding or 'iso-8859-15'
        old = self._convert_to_utf8(old, encoding)
        new = self._convert_to_utf8(new, encoding)

        # Normalize the input so that if there isn't a trailing newline, we add
        # it.
        if old and old[-1] != '\n':
            old += '\n'

        if new and new[-1] != '\n':
            new += '\n'

        a = self.NEWLINES_RE.split(old or '')
        b = self.NEWLINES_RE.split(new or '')

        # Remove the trailing newline, now that we've split this. This will
        # prevent a duplicate line number at the end of the diff.
        del a[-1]
        del b[-1]

        a_num_lines = len(a)
        b_num_lines = len(b)

        markup_a = markup_b = None

        if self._get_enable_syntax_highlighting(old, new, a, b):
            repository = self.filediff.diffset.repository
            tool = repository.get_scmtool()
            source_file = \
                tool.normalize_path_for_display(self.filediff.source_file)
            dest_file = \
                tool.normalize_path_for_display(self.filediff.dest_file)

            try:
                # TODO: Try to figure out the right lexer for these files
                #       once instead of twice.
                markup_a = self._apply_pygments(old or '', source_file)
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
            if fnmatch.fnmatch(self.filename, pattern):
                ignore_space = False
                break

        self.differ = get_differ(a, b, ignore_space=ignore_space,
                                 compat_version=self.diffset.diffcompat)
        self.differ.add_interesting_lines_for_headers(self.filename)

        context_num_lines = siteconfig.get("diffviewer_context_num_lines")
        collapse_threshold = 2 * context_num_lines + 3

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

        line_num = 1
        opcodes_generator = get_diff_opcode_generator(self.differ)

        for tag, i1, i2, j1, j2, meta in opcodes_generator:
            old_lines = markup_a[i1:i2]
            new_lines = markup_b[j1:j2]
            num_lines = max(len(old_lines), len(new_lines))

            self._cur_meta = meta
            lines = map(self._diff_line,
                        xrange(line_num, line_num + num_lines),
                        xrange(i1 + 1, i2 + 1), xrange(j1 + 1, j2 + 1),
                        a[i1:i2], b[j1:j2], old_lines, new_lines)
            self._cur_meta = None

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

        log_timer.done()

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

    def _diff_line(self, v_line_num, old_line_num, new_line_num,
                   old_line, new_line, old_markup, new_markup):
        """Creates a single line in the diff viewer.

        Information on the line will be returned, and later will be used
        for rendering the line. The line represents a single row of a
        side-by-side diff. It contains a row number, real line numbers,
        region information, syntax-highlighted HTML for the text,
        and other metadata.
        """
        if (old_line and new_line and
            len(old_line) <= self.STYLED_MAX_LINE_LEN and
            len(new_line) <= self.STYLED_MAX_LINE_LEN and
            old_line != new_line):
            old_region, new_region = self._get_line_changed_regions(old_line,
                                                                    new_line)
        else:
            old_region = new_region = []

        meta = self._cur_meta

        result = [
            v_line_num,
            old_line_num or '', mark_safe(old_markup or ''), old_region,
            new_line_num or '', mark_safe(new_markup or ''), new_region,
            (old_line_num, new_line_num) in meta['whitespace_lines']
        ]

        if old_line_num and old_line_num in meta.get('moved', {}):
            destination = meta['moved'][old_line_num]
            result.append(destination)
        elif new_line_num and new_line_num in meta.get('moved', {}):
            destination = meta['moved'][new_line_num]
            result.append(destination)

        return result

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

        for i in xrange(last_index, len(possible_functions)):
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
        lexer = get_lexer_for_filename(filename,
                                       stripnl=False,
                                       encoding='utf-8')
        lexer.add_filter('codetagify')

        return highlight(data, lexer, NoWrapperHtmlFormatter()).splitlines()

    def _convert_to_utf8(self, s, enc):
        """Returns the passed string as a unicode string.

        If conversion to UTF-8 fails, we try the user-specified encoding, which
        defaults to ISO 8859-15.  This can be overridden by users inside the
        repository configuration, which gives users repository-level control
        over file encodings (file-level control is really, really hard).
        """
        if isinstance(s, unicode):
            return s.encode('utf-8')
        elif isinstance(s, basestring):
            try:
                # First try strict unicode (for when everything is valid utf-8)
                return unicode(s, 'utf-8')
            except UnicodeError:
                # Now try any candidate encodings.
                for e in enc.split(','):
                    try:
                        u = unicode(s, e)
                        return u.encode('utf-8')
                    except UnicodeError:
                        pass

                # Finally, try to convert to straight unicode and replace all
                # unknown characters.
                try:
                    return unicode(s, 'utf-8', errors='replace')
                except UnicodeError:
                    raise Exception(
                        _("Diff content couldn't be converted to UTF-8 "
                          "using the following encodings: %s") % enc)
        else:
            raise TypeError("Value to convert is unexpected type %s", type(s))

    def _get_line_changed_regions(self, oldline, newline):
        """Returns regions of changes between two similar lines."""
        if oldline is None or newline is None:
            return (None, None)

        # Use the SequenceMatcher directly. It seems to give us better results
        # for this. We should investigate steps to move to the new differ.
        differ = SequenceMatcher(None, oldline, newline)

        # This thresholds our results -- we don't want to show inter-line diffs
        # if most of the line has changed, unless those lines are very short.

        # FIXME: just a plain, linear threshold is pretty crummy here.  Short
        # changes in a short line get lost.  I haven't yet thought of a fancy
        # nonlinear test.
        if differ.ratio() < 0.6:
            return (None, None)

        oldchanges = []
        newchanges = []
        back = (0, 0)

        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'equal':
                if (i2 - i1 < 3) or (j2 - j1 < 3):
                    back = (j2 - j1, i2 - i1)
                continue

            oldstart, oldend = i1 - back[0], i2
            newstart, newend = j1 - back[1], j2

            if oldchanges != [] and oldstart <= oldchanges[-1][1] < oldend:
                oldchanges[-1] = (oldchanges[-1][0], oldend)
            elif not oldline[oldstart:oldend].isspace():
                oldchanges.append((oldstart, oldend))

            if newchanges != [] and newstart <= newchanges[-1][1] < newend:
                newchanges[-1] = (newchanges[-1][0], newend)
            elif not newline[newstart:newend].isspace():
                newchanges.append((newstart, newend))

            back = (0, 0)

        return oldchanges, newchanges


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
