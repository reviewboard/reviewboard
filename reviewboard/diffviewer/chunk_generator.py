"""Diff chunk generator implementations."""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import re
from collections.abc import Mapping
from itertools import zip_longest
from typing import Any, Literal, TYPE_CHECKING, TypedDict

import pygments.util
from django.utils.encoding import force_str
from django.utils.html import escape
from django.utils.translation import get_language, gettext as _
from djblets.log import log_timed
from djblets.cache.backend import cache_memoize
from housekeeping.functions import deprecate_non_keyword_only_args
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import (find_lexer_class,
                             guess_lexer_for_filename)

from reviewboard.codesafety import code_safety_checker_registry
from reviewboard.deprecation import (
    RemovedInReviewBoard80Warning,
    RemovedInReviewBoard10_0Warning,
)
from reviewboard.diffviewer.differ import DiffCompatVersion, get_differ
from reviewboard.diffviewer.diffutils import (
    DiffRegions,
    convert_to_unicode,
    get_filediff_encodings,
    get_line_changed_regions,
    get_original_and_patched_files,
    get_original_file,
    get_patched_file,
    get_sha256,
    split_line_endings,
)
from reviewboard.diffviewer.opcode_generator import get_diff_opcode_generator
from reviewboard.diffviewer.settings import DiffSettings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from django.http import HttpRequest
    from typing_extensions import TypeAlias

    from reviewboard.diffviewer.differ import Differ, DiffOpcodeTag
    from reviewboard.diffviewer.models.filediff import FileDiff
    from reviewboard.diffviewer.opcode_generator import DiffOpcodeGenerator

    _HtmlFormatter = HtmlFormatter[str]
else:
    _HtmlFormatter = HtmlFormatter


logger = logging.getLogger(__name__)


class NoWrapperHtmlFormatter(_HtmlFormatter):
    """An HTML Formatter for Pygments that doesn't wrap items in a div."""

    def _wrap_div(
        self,
        inner: Iterator[tuple[int, str]],
    ) -> Iterator[tuple[int, str]]:
        """Override for the _wrap_div method.

        The parent class uses this method to wrap raw contents in ``<div>``
        tags. This override prevents that, and filters out any wrapper nodes
        which have already been added.

        Args:
            inner (iterator):
                The iterator of nodes.

        Yields:
            tuple:
            Each node to include.

            Tuple:
                0 (int):
                    1, always. For the HTML formatter implementation, this
                    value is either 0 (indicating a wrapper node) or 1
                    (indicating content).

                1 (str):
                    The content of the node.
        """
        for tup in inner:
            if tup[0]:
                yield tup


#: The tag for a diff chunk.
#:
#: Version Added:
#:     8.0
DiffChunkTag: TypeAlias = Literal[
    'delete',
    'equal',
    'insert',
    'replace',
]


#: A line in the diff.
#:
#: Version Added:
#:     8.0
DiffLine: TypeAlias = tuple[
    # [0] Virtual line number (row number in the two-column diff).
    int,

    # [1] Real line number in the original file.
    int | None,

    # [2] HTML markup of the original file line.
    str,

    # [3] Changed regions of the original line (for "replace" chunks).
    DiffRegions,

    # [4] Real line number in the modified file.
    int | None,

    # [5] HTML markup of the modified file line.
    str,

    # [6] Changed regions of the modified line (for "replace" chunks).
    DiffRegions,

    # [7] Whether the line consists only of whitespace changes.
    bool,

    # [8] Metadata for the line.
    dict[str, Any] | None,
]


class DiffChunk(TypedDict):
    """Definition for a chunk in the diff.

    Version Added:
        8.0
    """

    #: The type of change.
    change: DiffChunkTag

    #: Whether the chunk can be collapsed.
    collapsable: bool

    #: The 0-based index of the chunk.
    index: int

    #: The rendered lines in the chunk.
    lines: Sequence[DiffLine]

    #: Metadata for the chunk.
    meta: dict[str, Any]

    #: The number of lines in the chunk.
    numlines: int


#: Type for information about a header in a file.
#:
#: Version Added:
#:     8.0
HeaderInfo = Mapping[str, str] | None


class RawDiffChunkGenerator:
    """A generator for chunks for a diff that can be used for rendering.

    Each chunk represents an insert, delete, replace, or equal section. It
    contains all the data needed to render the portion of the diff.

    This is general-purpose and meant to operate on strings each consisting of
    at least one line of text, or lists of lines of text.

    If the caller passes lists of lines instead of strings, then the
    caller will also be responsible for applying any syntax highlighting and
    dealing with newline differences.

    Chunk generator instances must be recreated for each new file being
    parsed.

    Version Changed:
        5.0:
        Added :py:attr:`all_code_safety_results`.
    """

    NEWLINES_RE = re.compile(r'\r?\n')

    # The maximum size a line can be before we start shutting off styling.
    STYLED_MAX_LINE_LEN = 1000
    STYLED_MAX_LIMIT_BYTES = 200000  # 200KB

    # A list of filename extensions that won't be styled.
    STYLED_EXT_BLACKLIST = (
        '.txt',  # ResourceLexer is used as a default.
    )

    #: The default width for a tabstop.
    TAB_SIZE = DiffSettings.DEFAULT_TAB_SIZE

    ######################
    # Instance variables #
    ######################

    #: Code safety warnings were found while processing the diff.
    #:
    #: This is in the form of::
    #:
    #:     {
    #:         '<checker_id>': {
    #:             'warnings': {'<result_id>', ...},
    #:             'errors': {'<result_id>', ...},
    #:         },
    #:         ...
    #:     }
    #:
    #: All keys are optional.
    #:
    #: Version Added:
    #:     5.0
    all_code_safety_results: dict[str, dict[str, set[str]]]

    #: The diff compatibility version.
    diff_compat: int

    #: Settings used for the generation of the diff.
    #:
    #: Version Added:
    #:     5.0.2
    #:
    #: Type:
    #:     reviewboard.diffviewer.settings.DiffSettings
    diff_settings: DiffSettings

    #: The differ object.
    differ: Differ | Any

    #: Whether to enable syntax highlighting
    enable_syntax_highlighting: bool

    #: A list of file encodings to try.
    encoding_list: Sequence[str]

    #: The old version of the file.
    old: bytes | Sequence[bytes]

    #: The filename for the old version of the file.
    orig_filename: str

    #: The filename for the new version of the file.
    modified_filename: str

    #: The new version of the file.
    new: bytes | Sequence[bytes]

    #: The current chunk being processed.
    _chunk_index: int

    #: The most recently seen header information.
    _last_header: tuple[
        HeaderInfo,
        HeaderInfo,
    ]

    #: The most recent header index used.
    _last_header_index: list[int]

    def __init__(
        self,
        old: bytes | Sequence[bytes] | None,
        new: bytes | Sequence[bytes] | None,
        orig_filename: str,
        modified_filename: str,
        encoding_list: (Sequence[str] | None) = None,
        diff_compat: int = DiffCompatVersion.DEFAULT,
        *,
        diff_settings: DiffSettings,
    ) -> None:
        """Initialize the chunk generator.

        Version Changed:
            6.0:
            * Removed ``enable_syntax_highlighting``.
            * Made ``diff_settings`` mandatory.

        Version Changed:
            5.0.2:
            * Added ``diff_settings``, which will be required starting in
              Review Board 6.
            * Deprecated ``enable_syntax_highlighting`` in favor of
              ``diff_settings``.

        Args:
            old (bytes or list of bytes):
                The old data being modified.

            new (bytes or list of bytes):
                The new data.

            orig_filename (str):
                The filename corresponding to the old data.

            modified_filename (str):
                The filename corresponding to the new data.

            encoding_list (list of str, optional):
                A list of encodings to try for the ``old`` and ``new`` data,
                when converting to Unicode. If not specified, this defaults
                to ``iso-8859-15``.

            diff_compat (int, optional):
                A specific diff compatibility version to use for any diffing
                logic.

            diff_settings (reviewboard.diffviewer.settings.DiffSettings):
                The settings used to control the display of diffs.

                Version Added:
                    5.0.2
        """
        # Check that the data coming in is in the formats we accept.
        for param, param_name in ((old, 'old'), (new, 'new')):
            if param is not None:
                if isinstance(param, list):
                    if param and not isinstance(param[0], bytes):
                        raise TypeError(
                            _('%s expects None, list of bytes, or bytes '
                              'value for "%s", not list of %s')
                            % (type(self).__name__, param_name,
                               type(param[0])))
                elif not isinstance(param, bytes):
                    raise TypeError(
                        _('%s expects None, list of bytes, or bytes value '
                          'for "%s", not %s')
                        % (type(self).__name__, param_name, type(param)))

        if not isinstance(orig_filename, str):
            raise TypeError(
                _('%s expects a Unicode value for "orig_filename"')
                % type(self).__name__)

        if not isinstance(modified_filename, str):
            raise TypeError(
                _('%s expects a Unicode value for "modified_filename"')
                % type(self).__name__)

        assert diff_settings.tab_size
        self.diff_settings = diff_settings

        if old is not None:
            self.old = old

        if new is not None:
            self.new = new

        self.orig_filename = orig_filename
        self.modified_filename = modified_filename
        self.diff_settings = diff_settings
        self.enable_syntax_highlighting = diff_settings.syntax_highlighting
        self.encoding_list = encoding_list or ['iso-8859-15']
        self.diff_compat = diff_compat
        self.differ = None

        self.all_code_safety_results = {}

        # Chunk processing state.
        self._last_header = (None, None)
        self._last_header_index = [0, 0]
        self._chunk_index = 0

    def get_opcode_generator(self) -> DiffOpcodeGenerator:
        """Return the DiffOpcodeGenerator used to generate diff opcodes.

        Returns:
            reviewboard.diffviewer.opcode_generator.DiffOpcodeGenerator:
            The opcode generator.
        """
        return get_diff_opcode_generator(self.differ)

    def get_chunks(
        self,
        cache_key: (str | None) = None,
    ) -> Iterator[DiffChunk]:
        """Yield the chunks for the given diff information.

        If a cache key is provided and there are chunks already computed in the
        cache, they will be yielded. Otherwise, new chunks will be generated,
        stored in cache (given a cache key), and yielded.

        Args:
            cache_key (str, optional):
                The cache key to use.

        Yields:
            DiffChunk:
            Each chunk in the diff.
        """
        if cache_key:
            chunks = cache_memoize(cache_key,
                                   lambda: list(self.get_chunks_uncached()),
                                   large_data=True)
        else:
            chunks = self.get_chunks_uncached()

        yield from chunks

    def get_chunks_uncached(self) -> Iterator[DiffChunk]:
        """Yield the list of chunks, bypassing the cache.

        Yields:
            DiffChunk:
            Each chunk in the diff.
        """
        assert self.old is not None
        assert self.new is not None

        yield from self.generate_chunks(self.old, self.new)

    def generate_chunks(
        self,
        old: bytes | Sequence[bytes],
        new: bytes | Sequence[bytes],
        old_encoding_list: (Sequence[str] | None) = None,
        new_encoding_list: (Sequence[str] | None) = None,
    ) -> Iterator[DiffChunk]:
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

        Args:
            old (bytes or list of bytes):
                The old data being modified.

            new (bytes or list of bytes):
                The new data.

            old_encoding_list (list of str, optional):
                An optional list of encodings that ``old`` may be encoded in.
                If not provided, :py:attr:`encoding_list` is used.

            new_encoding_list (list of str, optional):
                An optional list of encodings that ``new`` may be encoded in.
                If not provided, :py:attr:`encoding_list` is used.

        Yields:
            DiffChunk:
            A rendered chunk.
        """
        is_lists = isinstance(old, list)
        assert is_lists == isinstance(new, list)

        if old_encoding_list is None:
            old_encoding_list = self.encoding_list

        if new_encoding_list is None:
            new_encoding_list = self.encoding_list

        if is_lists:
            assert isinstance(old, list)
            assert isinstance(new, list)

            old_lines = self.normalize_source_list(old, old_encoding_list)
            new_lines = self.normalize_source_list(new, new_encoding_list)

            old_markup = old_lines
            new_markup = new_lines
        else:
            assert isinstance(old, bytes)
            assert isinstance(new, bytes)

            old_str, old_lines = self.normalize_source_string(
                old, old_encoding_list)
            new_str, new_lines = self.normalize_source_string(
                new, new_encoding_list)

            old_markup = None
            new_markup = None

            if self._get_enable_syntax_highlighting(
                old, new, old_lines, new_lines):
                old_markup = self._apply_pygments(
                    old_str,
                    self.normalize_path_for_display(self.orig_filename))
                new_markup = self._apply_pygments(
                    new_str,
                    self.normalize_path_for_display(self.modified_filename))

            if not old_markup:
                old_markup = self.NEWLINES_RE.split(escape(old_str))

            if not new_markup:
                new_markup = self.NEWLINES_RE.split(escape(new_str))

        old_num_lines = len(old_lines)
        new_num_lines = len(new_lines)

        ignore_space = not any(
            fnmatch.fnmatch(self.orig_filename, pattern)
            for pattern in self.diff_settings.include_space_patterns
        )

        self.differ = get_differ(old_lines, new_lines,
                                 ignore_space=ignore_space,
                                 compat_version=self.diff_compat)
        self.differ.add_interesting_lines_for_headers(self.orig_filename)

        context_num_lines = self.diff_settings.context_num_lines
        collapse_threshold = 2 * context_num_lines + 3

        line_num = 1
        opcode_generator = self.get_opcode_generator()

        counts = {
            'equal': 0,
            'replace': 0,
            'insert': 0,
            'delete': 0,
        }

        for tag, i1, i2, j1, j2, meta in opcode_generator:
            num_lines = max(i2 - i1, j2 - j1)

            assert meta is not None

            lines = [
                self._diff_line(tag, meta, *diff_args)  # type:ignore
                for diff_args in zip_longest(
                    range(line_num, line_num + num_lines),
                    range(i1 + 1, i2 + 1),
                    range(j1 + 1, j2 + 1),
                    old_lines[i1:i2],
                    new_lines[j1:j2],
                    old_markup[i1:i2],
                    new_markup[j1:j2]
                )
            ]

            counts[tag] += num_lines

            if tag == 'equal' and num_lines > collapse_threshold:
                last_range_start = num_lines - context_num_lines

                if line_num == 1:
                    yield self._new_chunk(lines, 0, last_range_start, True)
                    yield self._new_chunk(lines, last_range_start, num_lines)
                else:
                    yield self._new_chunk(lines, 0, context_num_lines)

                    if i2 == old_num_lines and j2 == new_num_lines:
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

    def check_line_code_safety(
        self,
        orig_line: str | None,
        modified_line: str | None,
        extra_state: (dict[str, Any] | None) = None,
        **kwargs,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Check the safety of a line of code.

        This will run the original and modified line through all registered
        code safety checkers. If any checker produces warnings or errors,
        those will be associated with the line.

        Version Added:
            5.0

        Args:
            orig_line (str):
                The original line to check.

            modified_line (str):
                The modiifed line to check.

            extra_state (dict, optional):
                Extra state to pass to the checker for the original or
                modified line content item. Used by subclasses to produce
                additional information that may be useful for some code safety
                checkers.

            **kwargs (dict, optional):
                Unused keyword arguments, for future expansion.

        Returns:
            list of tuple:
            A list of code safety results containing warnings or errors. Each
            item is a tuple containing:

            Tuple:
                0 (str):
                    The registered checker ID.

                1 (dict):
                    A dictionary with ``errors`` and/or ``warnings`` keys.
        """
        if extra_state is None:
            extra_state = {}

        # Check for any unsafe/suspicious content on this line by passing
        # the raw source through any registered code safety checkers.
        results = []
        to_check = []

        if orig_line:
            to_check.append({
                'path': self.orig_filename,
                'lines': [orig_line],
                **extra_state,
            })

        if modified_line:
            to_check.append({
                'path': self.modified_filename,
                'lines': [modified_line],
                **extra_state,
            })

        if to_check:
            code_safety_configs = self.diff_settings.code_safety_configs

            # We have code to check. Let's go through each code checker
            # and see if we have any warnings or errors to display.
            for checker in code_safety_checker_registry:
                checker_config = code_safety_configs.get(checker.checker_id,
                                                         {})
                checker_results = checker.check_content(content_items=to_check,
                                                        **checker_config)

                if checker_results:
                    # Normalize the code checker results. We're going to
                    # extract only "errors" and "warnings" keys and set them
                    # only if they have a truthy value (present in the
                    # dictionary, non-None, and not an empty list).
                    norm_checker_results = {}

                    for key in ('errors', 'warnings'):
                        checker_result_ids = checker_results.get(key)

                        if checker_result_ids:
                            norm_checker_results[key] = checker_result_ids

                    if norm_checker_results:
                        # We have normalized checker results, so add them to
                        # the final list of results as documented in "Returns".
                        results.append((checker.checker_id,
                                        norm_checker_results))

        return results

    def normalize_source_string(
        self,
        s: bytes,
        encoding_list: Sequence[str],
        **kwargs,
    ) -> tuple[str, Sequence[str]]:
        """Normalize a source string of text to use for the diff.

        This will normalize the encoding of the string and the newlines,
        returning a tuple containing the normalized string and a list of
        lines split from the source.

        Both the original and modified strings used for the diff will be
        normalized independently.

        This is only used if the caller passes a string instead of a list for
        the original or new values.

        Subclasses can override this to provide custom behavior.

        Args:
            s (bytes):
                The string to normalize.

            encoding_list (list of str):
                The list of encodings to try when converting the string to
                Unicode.

            **kwargs (dict):
                Additional keyword arguments, for future expansion.

        Returns:
            tuple:
            A tuple containing:

            Tuple:
                0 (str):
                    The normalized string.

                1 (list of str):
                    The string, split into lines.

        Raises:
            UnicodeDecodeError:
                The string could not be converted to Unicode.
        """
        s_str = convert_to_unicode(s, encoding_list)[1]

        # Normalize the input so that if there isn't a trailing newline, we
        # add it.
        if s_str and not s_str.endswith('\n'):
            s_str += '\n'

        lines = self.NEWLINES_RE.split(s_str or '')

        # Remove the trailing newline, now that we've split this. This will
        # prevent a duplicate line number at the end of the diff.
        del lines[-1]

        return s_str, lines

    def normalize_source_list(
        self,
        lines: Sequence[bytes],
        encoding_list: Sequence[str],
        **kwargs,
    ) -> Sequence[str]:
        """Normalize a list of source lines to use for the diff.

        This will normalize the encoding of the lines.

        Both the original and modified lists of lines used for the diff will be
        normalized independently.

        This is only used if the caller passes a list instead of a string for
        the original or new values.

        Subclasses can override this to provide custom behavior.

        Args:
            lines (list of bytes):
                The list of lines to normalize.

            encoding_list (list of str):
                The list of encodings to try when converting the lines to
                Unicode.

            **kwargs (dict):
                Additional keyword arguments, for future expansion.

        Returns:
            list of str:
            The resulting list of normalized lines.

        Raises:
            UnicodeDecodeError:
                One or more lines could not be converted to Unicode.
        """
        return [
            convert_to_unicode(s, encoding_list)[1]
            for s in lines
        ]

    def normalize_path_for_display(
        self,
        filename: str,
    ) -> str:
        """Normalize a file path for display to the user.

        By default, this returns the filename as-is. Subclasses can override
        the behavior to return a variant of the filename.

        Args:
            filename (str):
                The filename to normalize.

        Returns:
            str:
            The normalized filename.
        """
        return filename

    def get_line_changed_regions(
        self,
        old_line_num: int | None,
        old_line: str | None,
        new_line_num: int | None,
        new_line: str | None,
    ) -> tuple[DiffRegions, DiffRegions]:
        """Return information on changes between two lines.

        This returns a tuple containing a list of tuples of ranges in the
        old line, and a list of tuples of ranges in the new line, that
        should be highlighted.

        This defaults to simply wrapping get_line_changed_regions() from
        diffutils. Subclasses can override to provide custom behavior.

        Args:
            old_line_num (int):
                The line number for the old line.

            old_line (str):
                The contents of the old line.

            new_line_num (int):
                The line number for the new line.

            new_line (str):
                The contents of the new line.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (reviewboard.diffviewer.diffutils.DiffRegions):
                    A list of (int, int) for changed regions in the old line.

                1 (reviewboard.diffviewer.diffutils.DiffRegions):
                    A list of (int, int) for changed regions in the new line.
        """
        return get_line_changed_regions(old_line, new_line)

    def _get_enable_syntax_highlighting(
        self,
        old: bytes,
        new: bytes,
        old_lines: Sequence[str],
        new_lines: Sequence[str],
    ) -> bool:
        """Return whether or not we'll be enabling syntax highlighting.

        This is based first on the value received when constructing the
        generator, and then based on heuristics to determine if it's fast
        enough to render with syntax highlighting on.

        The heuristics take into account the size of the files in bytes and
        the number of lines.

        Args:
            old (bytes):
                The contents of the old file as a single bytestring.

            new (bytes):
                The contents of the new file as a single bytestring.

            old_lines (list of str):
                The list of lines in the old file.

            new_lines (list of str):
                The list of lines in the new file.

        Returns:
            bool:
            Whether syntax highlighting should be applied for the file.
        """
        if not self.enable_syntax_highlighting:
            return False

        threshold = self.diff_settings.syntax_highlighting_threshold

        if threshold and (len(old_lines) > threshold or
                          len(new_lines) > threshold):
            return False

        # Very long files, especially XML files, can take a long time to
        # highlight. For files over a certain size, don't highlight them.
        if (len(old) > self.STYLED_MAX_LIMIT_BYTES or
            len(new) > self.STYLED_MAX_LIMIT_BYTES):
            return False

        # Don't style the file if we have any *really* long lines.
        # It's likely a minified file or data or something that doesn't
        # need styling, and it will just grind Review Board to a halt.
        for lines in (old_lines, new_lines):
            for line in lines:
                if len(line) > self.STYLED_MAX_LINE_LEN:
                    return False

        return True

    def _diff_line(
        self,
        tag: DiffOpcodeTag,
        meta: dict[str, Any],
        v_line_num: int,
        old_line_num: int | None,
        new_line_num: int | None,
        old_line: str | None,
        new_line: str | None,
        old_markup: str | None,
        new_markup: str | None,
    ) -> DiffLine:
        """Create a single line in the diff viewer.

        Information on the line will be returned, and later will be used
        for rendering the line. The line represents a single row of a
        side-by-side diff. It contains a row number, real line numbers,
        region information, syntax-highlighted HTML for the text,
        and other metadata.

        Version Changed:
            8.0:
            Changed to return a DiffLine tuple instead of a heterogenous list.

        Args:
            tag (reviewboard.diffviewer.differ.DiffOpcodeTag):
                The tag for the chunk the line is in.

            meta (dict):
                Metadata for the chunk.

            v_line_num (int):
                The row number of the line in the 2-column diff.

            old_line_num (int):
                The line number in the old version of the file.

            new_line_num (int):
                The line number in the new version of the file.

            old_line (str):
                The line content in the old version of the file.

            new_line (str):
                The line content in the new version of the file.

            old_markup (str):
                The HTML markup for the line in the old version of the file
                (e.g. the line with syntax highlighting applied).

            new_markup (str):
                The HTML markup for the line in the old version of the file
                (e.g. the line with syntax highlighting applied).

        Returns:
            DiffLine:
            The diff line.
        """
        if (tag == 'replace' and
            old_line and new_line and
            len(old_line) <= self.STYLED_MAX_LINE_LEN and
            len(new_line) <= self.STYLED_MAX_LINE_LEN and
            old_line != new_line):
            # Generate information on the regions that changed between the
            # two lines.
            old_regions, new_regions = \
                self.get_line_changed_regions(old_line_num, old_line,
                                              new_line_num, new_line)
        else:
            old_regions = new_regions = None

        old_markup = old_markup or ''
        new_markup = new_markup or ''

        line_pair = (old_line_num, new_line_num)

        indentation_changes = meta.get('indentation_changes', {})

        if line_pair[0] is not None and line_pair[1] is not None:
            indentation_change = indentation_changes.get(
                '{}-{}'.format(*line_pair))

            # We check the ranges against (0, 0) for compatibility with a bug
            # present in Review Board 4.0.6 and older, where bad indentation
            # calculation logic could incorrectly determine that two
            # "filtered-equal" lines in interdiffs had a 0-length indentation
            # change. This broke our serialization logic.
            #
            # Review Board 4.0.7 and higher address this problem, but we could
            # be showing something that's still in cache. Note however that
            # the "indentation" lines will still be broken up into their own
            # chunks in the diff viewer, but at least they'll render.
            if indentation_change and indentation_change[1:] != (0, 0):
                old_markup, new_markup = self._highlight_indentation(
                    old_markup, new_markup, *indentation_change)

        # NOTE: Prior to Review Board 5, this only contained moved info
        #       ("to"/"from" keys), and was not used for general line-level
        #       metadata. To avoid changing the structure of the line format
        #       too much (given that this can be consumed by third-parties),
        #       we have updated this to be a general-purpose metadata storage.
        line_meta = {}

        # Record all the moved line numbers, carefully making note of the
        # start of each range. Ranges start when the previous line number is
        # either not in a move range or does not immediately precede this
        # line.
        for direction, moved_line_num in (('to', old_line_num),
                                          ('from', new_line_num)):
            moved_meta = meta.get(f'moved-{direction}', {})
            direction_move_info = self._get_move_info(moved_line_num,
                                                      moved_meta)

            if direction_move_info is not None:
                line_meta[direction] = direction_move_info

        # Check for any unsafe/suspicious content on this line by passing
        # the raw source through any registered code safety checkers.
        code_safety_results = self.check_line_code_safety(
            orig_line=old_line,
            modified_line=new_line)

        if code_safety_results:
            # Store the code safety information for this line and in the
            # diff-wide all_code_safety_results.
            line_meta['code_safety'] = code_safety_results
            all_code_safety_results = self.all_code_safety_results

            for checker_id, checker_results in code_safety_results:
                all_code_checker_results = \
                    all_code_safety_results.setdefault(checker_id, {})

                for key, checker_result_ids in checker_results.items():
                    all_code_checker_results.setdefault(key, set()).update(
                        checker_result_ids)

        return (
            v_line_num,
            old_line_num,
            old_markup,
            old_regions,
            new_line_num,
            new_markup,
            new_regions,
            line_pair in meta['whitespace_lines'],
            line_meta or None,
        )

    def _get_move_info(
        self,
        line_num: int | None,
        moved_meta: Mapping[int, int],
    ) -> tuple[int, bool] | None:
        """Return information for a moved line.

        This will return a tuple containing the line number on the other end
        of the move for a line, and whether this is the beginning of a move
        range.

        Args:
            line_num (int):
                The line number that was part of a move.

            moved_meta (dict):
                Information on the move.

        Returns:
            tuple:
            A tuple of ``(other_line, is_first_in_range)``.
        """
        if not line_num or line_num not in moved_meta:
            return None

        other_line_num = moved_meta[line_num]

        return (
            other_line_num,
            (line_num - 1 not in moved_meta or
             other_line_num != moved_meta[line_num - 1] + 1),
        )

    def _highlight_indentation(
        self,
        old_markup: str,
        new_markup: str,
        is_indent: bool,
        raw_indent_len: int,
        norm_indent_len_diff: int,
    ) -> tuple[str, str]:
        """Highlight indentation in an HTML-formatted line.

         This will wrap the indentation in <span> tags, and format it in
         a way that makes it clear how many spaces or tabs were used.

        Args:
            old_markup (str):
                The markup for the old line.

            new_markup (str):
                The markup for the new line.

            is_indent (bool):
                If ``True``, the new line is indented compared to the old. If
                ``False``, the new line is dedented.

            raw_indent_len (int):
                The base amount of indentation in the line.

            norm_indent_len_diff (int):
                The difference in indentation between the old and new lines.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (str):
                    The changed markup for the old line.

                1 (str):
                    The changed markup for the new line.
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

    def _wrap_indentation_chars(
        self,
        class_name: str,
        markup: str,
        raw_indent_len: int,
        norm_indent_len_diff: int,
        serializer: Callable[[str, int], tuple[str, str]],
    ) -> str:
        """Wrap characters in a string with indentation markers.

        This will insert the indentation markers and its wrapper in the
        markup string. It's careful not to interfere with any tags that
        may be used to highlight that line.

        Args:
            class_name (str):
                The class name to apply to the new <span> element.

            markup (str):
                The markup for the line.

            raw_indent_len (int):
                The base amount of indentation in the line.

            norm_indent_len_diff (int):
                The difference in indentation between the old and new lines.

            serializer (callable):
                The method to call to serialize the indentation characters.

        Returns:
            str:
            The wrapped string.
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

        return (
            f'{markup[:start_pos]}'
            f'<span class="{class_name}">{serialized}</span>'
            f'{remainder + markup[end_pos:]}'
        )

    def _serialize_indentation(
        self,
        chars: str,
        norm_indent_len_diff: int,
    ) -> tuple[str, str]:
        """Serializes an indentation string into an HTML representation.

        This will show every space as ``>``, and every tab as ``------>|``.
        In the case of tabs, we display as much of it as possible (anchoring
        to the right-hand side) given the space we have within the tab
        boundary.

        Args:
            chars (str):
                The indentation characters to serialize.

            norm_indent_len_diff (int):
                The difference in indentation between the old and new lines.

        Returns:
            tuple:
            A 2-tuple containing:

            Tuple:
                0 (str):
                    The serialized indentation string.

                1 (str):
                    The remaining indentation characters not serialized.
        """
        assert chars

        s = ''
        i = 0
        j = 0

        tab_size = self.diff_settings.tab_size
        assert tab_size

        for j, c in enumerate(chars):
            if c == ' ':
                s += '&gt;'
                i += 1
            elif c == '\t':
                # Build "------>|" with the room we have available.
                in_tab_pos = i % tab_size

                if in_tab_pos < tab_size - 1:
                    if in_tab_pos < tab_size - 2:
                        num_dashes = (tab_size - 2 - in_tab_pos)
                        s += '&mdash;' * num_dashes
                        i += num_dashes

                    s += '&gt;'
                    i += 1

                s += '|'
                i += 1

            if i >= norm_indent_len_diff:
                break

        return s, chars[j + 1:]

    def _serialize_unindentation(
        self,
        chars: str,
        norm_indent_len_diff: int,
    ) -> tuple[str, str]:
        """Serialize an unindentation string into an HTML representation.

        This will show every space as ``<``, and every tab as ``|<------``.
        In the case of tabs, we display as much of it as possible (anchoring
        to the left-hand side) given the space we have within the tab
        boundary.

        Args:
            chars (str):
                The unindentation characters to serialize.

            norm_indent_len_diff (int):
                The difference in indentation between the old and new lines.

        Returns:
            tuple:
            A 2-tuple containing:

            Tuple:
                0 (str):
                    The serialized unindentation string.

                1 (str):
                    The remaining unindentation characters not serialized.
        """
        assert chars

        s = ''
        i = 0
        j = 0

        tab_size = self.diff_settings.tab_size
        assert tab_size

        for j, c in enumerate(chars):
            if c == ' ':
                s += '&lt;'
                i += 1
            elif c == '\t':
                # Build "|<------" with the room we have available.
                in_tab_pos = i % tab_size

                s += '|'
                i += 1

                if in_tab_pos < tab_size - 1:
                    s += '&lt;'
                    i += 1

                    if in_tab_pos < tab_size - 2:
                        num_dashes = (tab_size - 2 - in_tab_pos)
                        s += '&mdash;' * num_dashes
                        i += num_dashes

            if i >= norm_indent_len_diff:
                break

        return s, chars[j + 1:]

    def _new_chunk(
        self,
        all_lines: Sequence[DiffLine],
        start: int,
        end: int,
        collapsible: bool = False,
        tag: DiffChunkTag = 'equal',
        meta: (dict[str, Any] | None) = None,
    ) -> DiffChunk:
        """Create a chunk.

        A chunk represents an insert, delete, or equal region. The chunk
        contains a bunch of metadata for things like whether or not it's
        collapsible and any header information.

        This is what ends up being returned to the caller of this class.

        Args:
            all_lines (list of DiffLine):
                The lines in the chunk.

            start (int):
                The row number of the start of the chunk.

            end (int):
                The row number of the start of the next chunk.

            collapsible (bool, optional):
                Whether the chunk is collapsible.

            tag (str, optional):
                The change tag for the chunk.

            meta (dict, optional):
                Metadata for the chunk.

        Returns:
            DiffChunk:
            The new chunk.
        """
        if not meta:
            meta = {}

        left_headers = list(self._get_interesting_headers(
            lines=all_lines,
            start=start,
            end=end,
            is_modified_file=False))
        right_headers = list(self._get_interesting_headers(
            lines=all_lines,
            start=start,
            end=end,
            is_modified_file=True))

        meta['left_headers'] = left_headers
        meta['right_headers'] = right_headers

        lines = all_lines[start:end]
        num_lines = len(lines)

        self._last_header = compute_chunk_last_header(
            lines=lines,
            numlines=num_lines,
            meta=meta,
            last_header=self._last_header)

        if (collapsible and
            end < len(all_lines) and
            (self._last_header[0] or self._last_header[1])):
            meta['headers'] = list(self._last_header)

        chunk: DiffChunk = {
            'index': self._chunk_index,
            'lines': lines,
            'numlines': num_lines,
            'change': tag,
            'collapsable': collapsible,
            'meta': meta,
        }

        self._chunk_index += 1

        return chunk

    def _get_interesting_headers(
        self,
        *,
        lines: Sequence[DiffLine],
        start: int,
        end: int,
        is_modified_file: bool,
    ) -> Iterator[tuple[int, str]]:
        """Yield all headers for a region of a diff.

        This scans for all headers that fall within the specified range
        of the specified lines on both the original and modified files.

        Version Changed:
            8.0:
            Made the arguments keyword-only.

        Args:
            lines (list of DiffLine):
                The lines in the chunk.

            start (int):
                The row number of the start of the chunk.

            end (int):
                The row number of the start of the next chunk.

            is_modified_file (bool):
                If ``True``, get headers for the modified version of the file.
                If ``False``, get headers for the original version of the file.

        Yields:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (int):
                    The line number of the header.

                1 (str):
                    The contents of the line with the header.
        """
        assert self.differ is not None
        possible_functions = \
            self.differ.get_interesting_lines('header', is_modified_file)

        if not possible_functions:
            return

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
            return

        for i in range(last_index, len(possible_functions)):
            linenum, line = possible_functions[i]
            linenum += 1

            if i2 is not None and linenum > i2:
                break
            elif i1 is not None and linenum >= i1:
                last_index = i

                yield linenum, line

        if is_modified_file:
            self._last_header_index[1] = last_index
        else:
            self._last_header_index[0] = last_index

    def _apply_pygments(
        self,
        data: str,
        filename: str,
    ) -> Sequence[str] | None:
        """Apply Pygments syntax-highlighting to a file's contents.

        This will only apply syntax highlighting if a lexer is available and
        the file extension is not blacklisted.

        Args:
            data (str):
                The data to syntax highlight.

            filename (str):
                The name of the file. This is used to help determine a
                suitable lexer.

        Returns:
            list of str:
            A list of lines, all syntax-highlighted, if a lexer is found.
            If no lexer is available, this will return ``None``.
        """
        if filename.endswith(self.STYLED_EXT_BLACKLIST):
            return None

        custom_pygments_lexers = self.diff_settings.custom_pygments_lexers
        lexer = None

        for ext, lexer_name in custom_pygments_lexers.items():
            if ext and filename.endswith(ext):
                lexer_class = find_lexer_class(lexer_name)

                if lexer_class:
                    lexer = lexer_class(stripnl=False,
                                        encoding='utf-8')
                    break
                else:
                    logger.error(
                        'Pygments lexer "%s" for "%s" files in '
                        'Diff Viewer Settings was not found.',
                        lexer_name, ext)
        else:
            try:
                lexer = guess_lexer_for_filename(filename,
                                                 data,
                                                 stripnl=False,
                                                 encoding='utf-8')
            except pygments.util.ClassNotFound:
                return None

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

    #: The format version for data stored in the cache.
    #:
    #: This should be updated when the format of the data returned by
    #: :py:meth:`get_chunks` changes in a compatibility-breaking way. This
    #: compatibility version is considered internal to Review Board, but we
    #: don't want old data in the cache to cause errors.
    #:
    #: Version Added:
    #:     8.0
    CACHE_FORMAT_VERSION = 1

    @deprecate_non_keyword_only_args(RemovedInReviewBoard80Warning)
    def __init__(
        self,
        request: HttpRequest,
        filediff: FileDiff,
        interfilediff: (FileDiff | None) = None,
        force_interdiff: bool = False,
        base_filediff: (FileDiff | None) = None,
        *,
        diff_settings: DiffSettings,
    ) -> None:
        """Initialize the DiffChunkGenerator.

        Version Changed:
            6.0:
            * Removed the old ``enable_syntax_highlighting`` argument.
            * Made ``diff_settings`` mandatory.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            filediff (reviewboard.diffviewer.models.filediff.FileDiff):
                The FileDiff to generate chunks for.

            interfilediff (reviewboard.diffviewer.models.filediff.FileDiff,
                           optional):
                If provided, the chunks will be generated for the differences
                between the result of applying ``filediff`` and the result of
                applying ``interfilediff``.

            force_interdiff (bool, optional):
                Whether or not to force an interdiff.

            base_filediff (reviewboard.diffviewer.models.filediff.FileDiff,
                           optional):
                An ancestor of ``filediff`` that we want to use as the base.
                Using this argument will result in the history between
                ``base_filediff`` and ``filediff`` being applied.

            diff_settings (reviewboard.diffviewer.settings.DiffSettings):
                The settings used to control the display of diffs.
        """
        assert filediff

        self.request = request
        self.diffset = filediff.diffset
        self.filediff = filediff
        self.interfilediff = interfilediff
        self.force_interdiff = force_interdiff
        self.repository = filediff.get_repository()
        self.tool = self.repository.get_scmtool()
        self.base_filediff = base_filediff

        if base_filediff:
            orig_filename = base_filediff.source_file
        else:
            orig_filename = filediff.source_file

        super().__init__(
            old=None,
            new=None,
            orig_filename=orig_filename,
            modified_filename=filediff.dest_file,
            encoding_list=self.repository.get_encoding_list(),
            diff_compat=filediff.diffset.diffcompat,
            diff_settings=diff_settings)

    def make_cache_key(self) -> str:
        """Return a new cache key for any generated chunks.

        Returns:
            str:
            The new cache key.
        """
        key: list[str] = []

        key.append(f'diff-sidebyside-{self.CACHE_FORMAT_VERSION}')

        if self.base_filediff is not None:
            key.append(f'base-{self.base_filediff.pk}')

        if not self.force_interdiff:
            key.append(str(self.filediff.pk))
        elif self.interfilediff:
            key.append(f'interdiff-{self.filediff.pk}-{self.interfilediff.pk}')
        else:
            key.append(f'interdiff-{self.filediff.pk}-none')

        key += [
            self.diff_settings.state_hash,
            get_language(),
        ]

        return '-'.join(key)

    def get_opcode_generator(self) -> DiffOpcodeGenerator:
        """Return the DiffOpcodeGenerator used to generate diff opcodes.

        Returns:
            reviewboard.diffviewer.opcode_generator.DiffOpcodeGenerator:
            The opcode generator.
        """
        diff = self.filediff.diff

        if self.interfilediff:
            interdiff = self.interfilediff.diff
        else:
            interdiff = None

        return get_diff_opcode_generator(self.differ, diff, interdiff,
                                         request=self.request,
                                         diff_settings=self.diff_settings)

    def get_chunks(self) -> Iterator[DiffChunk]:
        """Yield the chunks for the given diff information.

        If the file is binary or is an added or deleted 0-length file, or if
        the file has moved with no additional changes, then an empty list of
        chunks will be returned.

        If there are chunks already computed in the cache, they will be
        yielded. Otherwise, new chunks will be generated, stored in cache,
        and yielded.

        Yields:
            DiffChunk:
            Each chunk in the diff.
        """
        filediff = self.filediff
        counts = filediff.get_line_counts()

        if (filediff.binary or
            filediff.source_revision == '' or
            ((filediff.is_new or filediff.deleted or
              filediff.moved or filediff.copied) and
             counts['raw_insert_count'] == 0 and
             counts['raw_delete_count'] == 0)):
            return

        cache_key = self.make_cache_key()

        yield from super().get_chunks(cache_key)

    def get_chunks_uncached(self) -> Iterator[DiffChunk]:
        """Yield the list of chunks, bypassing the cache.

        Yields:
            DiffChunk:
            Each chunk in the diff.
        """
        base_filediff = self.base_filediff
        filediff = self.filediff
        interfilediff = self.interfilediff
        request = self.request

        old, new = get_original_and_patched_files(
            filediff=filediff,
            request=request)

        old_encoding_list = get_filediff_encodings(filediff)
        new_encoding_list = old_encoding_list

        if base_filediff is not None:
            # The diff is against a commit that:
            #
            # 1. Follows the first commit in a series (the first won't have
            #    a base_commit/base_filediff that can be looked up)
            #
            # 2. Follows a commit that modifies this file, or is the base
            #    commit that modifies this file.
            #
            # We'll be diffing against the patched version of this commit's
            # version of the file.
            old = get_original_file(filediff=base_filediff,
                                    request=request)
            old = get_patched_file(source_data=old,
                                   filediff=base_filediff,
                                   request=request)
            old_encoding_list = get_filediff_encodings(base_filediff)
        elif filediff.commit_id:
            # This diff is against a commit, but no previous FileDiff
            # modifying this file could be found. As per the above comment,
            # this could end up being the very first commit in a series, or
            # it might not have been modified in the base commit or any
            # previous commit.
            #
            # We'll need to fetch the first ancestor of this file in the
            # commit history, if we can find one. We'll base the "old" version
            # of the file on the original version of this commit, meaning that
            # this commit and all modifications since will be shown as "new".
            # Basically, viewing the upstream of the file, before any commits.
            #
            # This should be safe because, without a base_filediff, there
            # should be no older commit containing modifications that we want
            # to diff against. This would be the first one, and we're using
            # its upstream changes.
            ancestors = filediff.get_ancestors(minimal=True)

            if ancestors:
                ancestor_filediff = ancestors[0]
                old = get_original_file(filediff=ancestor_filediff,
                                        request=request)
                old_encoding_list = get_filediff_encodings(ancestor_filediff)

        # Check whether we have a SHA256 checksum first. They were introduced
        # in Review Board 4.0, long after SHA1 checksums. If we already have
        # a SHA256 checksum, then we'll also have a SHA1 checksum, but the
        # inverse is not true.
        if filediff.orig_sha256 is None:
            if filediff.orig_sha1 is None:
                filediff.extra_data.update({
                    'orig_sha1': self._get_sha1(old),
                    'patched_sha1': self._get_sha1(new),
                })

            filediff.extra_data.update({
                'orig_sha256': get_sha256(old),
                'patched_sha256': get_sha256(new),
            })
            filediff.save(update_fields=['extra_data'])

        if interfilediff:
            old = new
            old_encoding_list = new_encoding_list

            interdiff_orig = get_original_file(filediff=interfilediff,
                                               request=request)
            new = get_patched_file(source_data=interdiff_orig,
                                   filediff=interfilediff,
                                   request=request)
            new_encoding_list = get_filediff_encodings(interfilediff)

            # Check whether we have a SHA256 checksum first. They were
            # introduced in Review Board 4.0, long after SHA1 checksums. If we
            # already have a SHA256 checksum, then we'll also have a SHA1
            # checksum, but the inverse is not true.
            if interfilediff.orig_sha256 is None:
                if interfilediff.orig_sha1 is None:
                    interfilediff.extra_data.update({
                        'orig_sha1': self._get_sha1(interdiff_orig),
                        'patched_sha1': self._get_sha1(new),
                    })

                interfilediff.extra_data.update({
                    'orig_sha256': get_sha256(interdiff_orig),
                    'patched_sha256': get_sha256(new),
                })
                interfilediff.save(update_fields=['extra_data'])
        elif self.force_interdiff:
            # Basically, revert the change.
            old, new = new, old
            old_encoding_list, new_encoding_list = \
                new_encoding_list, old_encoding_list

        timer_msg: str

        if interfilediff:
            timer_msg = (
                f'Generating diff chunks for interdiff ids '
                f'{filediff.pk}-{interfilediff.pk} ({filediff.source_file})'
            )
        else:
            timer_msg = (
                f'Generating diff chunks for filediff id {filediff.pk} '
                f'({filediff.source_file})'
            )

        with log_timed(timer_msg,
                       logger=logger,
                       request=request):
            yield from self.generate_chunks(
                old=old,
                new=new,
                old_encoding_list=old_encoding_list,
                new_encoding_list=new_encoding_list)

        if (not interfilediff and
            not self.base_filediff and
            not self.force_interdiff):
            insert_count = self.counts['insert']
            delete_count = self.counts['delete']
            replace_count = self.counts['replace']
            equal_count = self.counts['equal']

            filediff.set_line_counts(
                insert_count=insert_count,
                delete_count=delete_count,
                replace_count=replace_count,
                equal_count=equal_count,
                total_line_count=(insert_count + delete_count +
                                  replace_count + equal_count))

    def check_line_code_safety(
        self,
        orig_line: str,
        modified_line: str,
        extra_state: (dict[str, Any] | None) = None,
        **kwargs,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Check the safety of a line of code.

        This will run the original and modified line through all registered
        code safety checkers. If any checker produces warnings or errors,
        those will be associated with the line.

        This is a specialization of
        :py:meth:`RawDiffChunkGenerator.check_line_code_safety` that provides
        a ``repository`` key for each item to check, for use in the code
        safety checker.

        Version Added:
            5.0

        Args:
            orig_line (str):
                The original line to check.

            modified_line (str):
                The modiifed line to check.

            extra_state (dict, optional):
                Extra state to pass to the checker for the original or
                modified line content item. Used by subclasses to produce
                additional information that may be useful for some code safety
                checkers.

            **kwargs (dict, optional):
                Unused keyword arguments, for future expansion.

        Returns:
            list of tuple:
            A list of code safety results containing warnings or errors. Each
            item is a tuple containing:

            1. The registered checker ID.
            2. A dictionary with ``errors`` and/or ``warnings`` keys.
        """
        if extra_state is None:
            extra_state = {}

        return super().check_line_code_safety(
            orig_line=orig_line,
            modified_line=modified_line,
            extra_state={
                'repository': self.repository,
                **extra_state,
            },
            **kwargs)

    def normalize_path_for_display(
        self,
        filename: str,
    ) -> str:
        """Normalize a file path for display to the user.

        This uses the associated :py:class:`~reviewboard.scmtools.core.SCMTool`
        to normalize the filename.

        Args:
            filename (str):
                The filename to normalize.

        Returns:
            str:
            The normalized filename.
        """
        return self.tool.normalize_path_for_display(
            filename,
            extra_data=self.filediff.extra_data)

    def _get_sha1(
        self,
        content: bytes,
    ) -> str:
        """Return a SHA1 hash for the provided content.

        Args:
            content (bytes):
                The content to generate the hash for.

        Returns:
            str:
            The resulting hash.
        """
        return force_str(hashlib.sha1(content).hexdigest())


@deprecate_non_keyword_only_args(RemovedInReviewBoard10_0Warning)
def compute_chunk_last_header(
    *,
    lines: Sequence[DiffLine],
    numlines: int,
    meta: dict[str, Any],
    last_header: (tuple[HeaderInfo, HeaderInfo] | None) = None,
) -> tuple[HeaderInfo, HeaderInfo]:
    """Compute information for the displayed function/class headers.

    This will record the displayed headers, their line numbers, and expansion
    offsets relative to the header's collapsed line range.

    The last_header variable, if provided, will be modified, which is
    important when processing several chunks at once. It will also be
    returned as a convenience.

    Version Changed:
        8.0:
        * Made arguments keyword-only.
        * Changed to take in and return a 2-tuple instead of a 2-element list.

    Args:
        lines (list of DiffLine):
            The lines in the chunk.

        numlines (int):
            The number of lines in the chuck.

        meta (dict):
            Metadata for the chunk.

        last_header (tuple):
            A 2-tuple of the most recent header information.

    Returns:
        tuple:
        A 2-tuple of:

        Tuple:
            0 (dict):
                Header information for the original version of the file.

            1 (dict):
                Header information for the modified version of the file.
    """
    if last_header is not None:
        left, right = last_header
    else:
        left = None
        right = None

    if left_headers := meta['left_headers']:
        header = left_headers[-1]

        left = {
            'line': header[0],
            'text': header[1].strip(),
        }

    if right_headers := meta['right_headers']:
        header = right_headers[-1]

        right = {
            'line': header[0],
            'text': header[1].strip(),
        }

    return left, right


_generator: type[DiffChunkGenerator] = DiffChunkGenerator


def get_diff_chunk_generator_class() -> type[DiffChunkGenerator]:
    """Return the DiffChunkGenerator class used for generating chunks.

    Returns:
        type:
        The class for the DiffChunkGenerator to use.
    """
    return _generator


def set_diff_chunk_generator_class(
    renderer: type[DiffChunkGenerator],
) -> None:
    """Set the DiffChunkGenerator class used for generating chunks.

    Args:
        renderer (type):
            The class for the DiffChunkGenerator to use.
    """
    assert renderer

    globals()['_generator'] = renderer


def get_diff_chunk_generator(*args, **kwargs) -> DiffChunkGenerator:
    """Return a DiffChunkGenerator instance used for generating chunks.

    Args:
        *args (tuple):
            Positional arguments to pass to the DiffChunkGenerator.

        **kwargs (dict):
            Keyword arguments to pass to the DiffChunkGenerator.

    Returns:
        DiffChunkGenerator:
        The chunk generator instance.
    """
    return _generator(*args, **kwargs)
