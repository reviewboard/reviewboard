from __future__ import unicode_literals

import io
import logging
import re
import weakref

from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.translation import ugettext as _
from djblets.util.properties import AliasProperty, TypedProperty

from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.diffviewer.errors import DiffParserError
from reviewboard.scmtools.core import Revision


logger = logging.getLogger(__name__)


class ParsedDiff(object):
    """Parsed information from a diff.

    This stores information on the diff as a whole, along with a list of
    commits made to the diff and a list of files within each.

    Extra data can be stored by the parser, which will be made available in
    :py:attr:`DiffSet.extra_data
    <reviewboard.diffviewer.models.diffset.DiffSet.extra_data>`.

    This is flexible enough to accommodate a variety of diff formats,
    including DiffX files.

    This class is meant to be used internally and by subclasses of
    :py:class:`BaseDiffParser`.

    Version Added:
        4.0.5

    Attributes:
        changes (list of ParsedDiffChange):
            The list of changes parsed in this diff. There should always be
            at least one.

        exta_data (dict):
            Extra data to store along with the information on the diff. The
            contents will be stored directly in :py:attr:`DiffSet.extra_data
            <reviewboard.diffviewer.models.diffset.DiffSet.extra_data>`.

        parser (BaseDiffParser):
            The diff parser that parsed this file.
    """

    def __init__(self, parser):
        """Initialize the parsed diff information.

        Args:
            parser (BaseDiffParser):
                The diff parser that parsed this file.
        """
        self.parser = parser
        self.extra_data = {}
        self.changes = []


class ParsedDiffChange(object):
    """Parsed change information from a diff.

    This stores information on a change to a tree, consisting of a set of
    parsed files and extra data to store (in :py:attr:`DiffCommit.extra_data
    <reviewboard.diffviewer.models.diffcommit.DiffCommit.extra_data>.

    This will often map to a commit, or just a typical collection of files in a
    diff. Traditional diffs will have only one of these. DiffX files may have
    many (but for the moment, only diffs with a single change can be handled
    when processing these results).

    Version Added:
        4.0.5

    Attributes:
        exta_data (dict):
            Extra data to store along with the information on the change. The
            contents will be stored directly in :py:attr:`DiffCommit.extra_data
            <reviewboard.diffviewer.models.diffcommit.DiffCommit.extra_data>`.

        files (list of ParsedDiffFile):
            The list of files parsed for this change. There should always be
            at least one.
    """

    def __init__(self, parsed_diff):
        """Initialize the parsed diff information.

        Args:
            parsed_diff (ParsedDiff):
                The parent parsed diff information.
        """
        assert parsed_diff is not None

        self._parent = weakref.ref(parsed_diff)
        self.extra_data = {}
        self.files = []

        parsed_diff.changes.append(self)

    @property
    def parent_parsed_diff(self):
        """The parent diff object.

        Type:
            ParsedDiff
        """
        if self._parent:
            return self._parent()

        return None


class ParsedDiffFile(object):
    """A parsed file from a diff.

    This stores information on a single file represented in a diff, including
    the contents of that file's diff, as parsed by :py:class:`DiffParser` or
    one of its subclasses.

    Parsers should set the attributes on this based on the contents of the
    diff, and should add any data found in the diff.

    This class is meant to be used internally and by subclasses of
    :py:class:`BaseDiffParser`.

    Version Changed:
        4.0.5:
        Diff parsers that manually construct instances must pass in
        ``parsed_diff_change`` instead of ``parser`` when constructing the
        object, and must call :py:meth:`discard` after construction if the
        file isn't wanted in the results.

    Attributes:
        binary (bool);
            Whether this represents a binary file.

        copied (bool):
            Whether this represents a file that has been copied. The file
            may or may not be modified in the process.

        deleted (bool):
            Whether this represents a file that has been deleted.

        delete_count (int):
            The number of delete (``-``) lines found in the file.

        insert_count (int):
            The number of insert (``+``) lines found in the file.

        is_symlink (bool):
            Whether this represents a file that is a symbolic link to another
            file.

        moved (bool):
            Whether this represents a file that has been moved/renamed. The
            file may or may not be modified in the process.

        parser (BaseDiffParser):
            The diff parser that parsed this file.

        skip (bool):
            Whether this file should be skipped by the parser. If any of the
            parser methods set this, the file will stop parsing and will be
            excluded from results.
    """

    #: The parsed original name of the file.
    #:
    #: Type:
    #:     bytes
    orig_filename = TypedProperty(bytes)

    #: The parsed file details of the original file.
    #:
    #: This will usually be a revision.
    #:
    #: Type:
    #:     bytes or reviewboard.scmtools.core.Revision
    orig_file_details = TypedProperty((bytes, Revision))

    #: The parsed modified name of the file.
    #:
    #: This may be the same as :py:attr:`orig_filename`.
    #:
    #: Type:
    #:     bytes
    modified_filename = TypedProperty(bytes)

    #: The parsed file details of the modified file.
    #:
    #: This will usually be a revision.
    #:
    #: Type:
    #:     bytes or reviewboard.scmtools.core.Revision
    modified_file_details = TypedProperty((bytes, Revision))

    #: The parsed value for an Index header.
    #:
    #: If present in the diff, this usually contains a filename, but may
    #: contain other content as well, depending on the variation of the diff
    #: format.
    #:
    #: Type:
    #:     bytes
    index_header_value = TypedProperty(bytes)

    #: The parsed original name of the file.
    #:
    #: Deprecated:
    #:     4.0:
    #:     Use :py:attr:`orig_filename` instead.
    origFile = AliasProperty('orig_filename',
                             convert_to_func=force_bytes,
                             deprecated=True,
                             deprecation_warning=RemovedInReviewBoard50Warning)

    #: The parsed file details of the original file.
    #:
    #: Deprecated:
    #:     4.0:
    #:     Use :py:attr:`orig_file_details` instead.
    origInfo = AliasProperty('orig_file_details',
                             convert_to_func=force_bytes,
                             deprecated=True,
                             deprecation_warning=RemovedInReviewBoard50Warning)

    #: The parsed original name of the file.
    #:
    #: Deprecated:
    #:     4.0:
    #:     Use :py:attr:`modified_filename` instead.
    newFile = AliasProperty('modified_filename',
                            convert_to_func=force_bytes,
                            deprecated=True,
                            deprecation_warning=RemovedInReviewBoard50Warning)

    #: The parsed file details of the modified file.
    #:
    #: Deprecated:
    #:     4.0:
    #:     Use :py:attr:`modified_file_details` instead.
    newInfo = AliasProperty('modified_file_details',
                            convert_to_func=force_bytes,
                            deprecated=True,
                            deprecation_warning=RemovedInReviewBoard50Warning)

    #: The parsed value for an Index header.
    #:
    #: Deprecated:
    #:     4.0:
    #:     Use :py:attr:`index_header_value` instead.
    index = AliasProperty('index_header_value',
                          convert_to_func=force_bytes,
                          deprecated=True,
                          deprecation_warning=RemovedInReviewBoard50Warning)

    def __init__(self, parser=None, parsed_diff_change=None, **kwargs):
        """Initialize the parsed file information.

        Version Changed:
            4.0.5
            Added the ``parsed_diff_change`` argument (which will be required
            in Review Board 5.0).

            Deprecated the ``parser`` argument (which will be removed in
            Review Board 5.0).

        Args:
            parser (reviewboard.diffviewer.parser.BaseDiffParser, optional):
                The diff parser that parsed this file.

                This is deprecated and will be remoed in Review Board 5.0.

            parsed_diff_change (ParsedDiffChange, optional):
                The diff change that owns this file.

                This will be required in Review Board 5.0.
        """
        if parsed_diff_change is None:
            RemovedInReviewBoard50Warning.warn(
                'Diff parsers must pass a ParsedDiffChange as the '
                'parsed_diff_change= parameter when creating a '
                'ParsedDiffFile. They should no longer pass a parser= '
                'parameter. This will be mandatory in Review Board 5.0.')

        if parsed_diff_change is not None:
            parsed_diff_change.files.append(self)
            parser = parsed_diff_change.parent_parsed_diff.parser

            parsed_diff_change = weakref.ref(parsed_diff_change)

        self._parent = parsed_diff_change
        self.parser = parser
        self.binary = False
        self.deleted = False
        self.moved = False
        self.copied = False
        self.is_symlink = False
        self.insert_count = 0
        self.delete_count = 0
        self.skip = False
        self.extra_data = {}

        self._data_io = io.BytesIO()
        self._data = None

        self._deprecated_info = {}

    @property
    def parent_parsed_diff_change(self):
        """The parent change object.

        Version Added:
            4.0.5

        Type:
            ParsedDiffChange
        """
        if self._parent:
            return self._parent()

        return None

    def __setitem__(self, key, value):
        """Set information on the parsed file from a diff.

        This is a legacy implementation used to help diff parsers retain
        compatibility with the old dictionary-based ways of setting parsed
        file information. Callers should be updated to set attributes instead.

        Deprecated:
            4.0:
            This will be removed in Review Board 5.0.

        Args:
            key (str):
                The key to set.

            value (object):
                The value to set.
        """
        self._warn_old_usage_deprecation()

        self._deprecated_info[key] = value
        setattr(self, key, value)

    def __getitem__(self, key):
        """Return information on the parsed file from a diff.

        This is a legacy implementation used to help diff parsers retain
        compatibility with the old dictionary-based ways of setting parsed
        file information. Callers should be updated to access attributes
        instead.

        Deprecated:
            4.0:
            This will be removed in Review Board 5.0.

        Args:
            key (str):
                The key to retrieve.

        Returns:
            object:
            The resulting value.

        Raises:
            KeyError:
                The key is invalid.
        """
        self._warn_old_usage_deprecation()

        return self._deprecated_info[key]

    def __contains__(self, key):
        """Return whether an old parsed file key has been explicitly set.

        This is a legacy implementation used to help diff parsers retain
        compatibility with the old dictionary-based ways of setting parsed
        file information. Callers should be updated to check attribute values
        instead.

        Deprecated:
            4.0:
            This will be removed in Review Board 5.0.

        Args:
            key (str):
                The key to check.

        Returns:
            bool:
            ``True`` if the key has been explicitly set by a diff parser.
            ``False`` if it has not.
        """
        self._warn_old_usage_deprecation()

        return key in self._deprecated_info

    def set(self, key, value):
        """Set information on the parsed file from a diff.

        This is a legacy implementation used to help diff parsers retain
        compatibility with the old dictionary-based ways of setting parsed
        file information. Callers should be updated to set attributes instead.

        Deprecated:
            4.0:
            This will be removed in Review Board 5.0.

        Args:
            key (str):
                The key to set.

            value (object):
                The value to set.
        """
        self._warn_old_usage_deprecation()

        self._deprecated_info[key] = value
        setattr(self, key, value)

    def get(self, key, default=None):
        """Return information on the parsed file from a diff.

        This is a legacy implementation used to help diff parsers retain
        compatibility with the old dictionary-based ways of setting parsed
        file information. Callers should be updated to access attributes
        instead.

        Deprecated:
            4.0:
            This will be removed in Review Board 5.0.

        Args:
            key (str):
                The key to retrieve.

            default (object, optional):
                The default value to return.

        Returns:
            object:
            The resulting value.
        """
        self._warn_old_usage_deprecation()

        return self._deprecated_info.get(key, default)

    def update(self, items):
        """Update information on the parsed file from a diff.

        This is a legacy implementation used to help diff parsers retain
        compatibility with the old dictionary-based ways of setting parsed
        file information. Callers should be updated to set individual
        attributes instead.

        Deprecated:
            4.0:
            This will be removed in Review Board 5.0.

        Args:
            items (dict):
                The keys and values to set.
        """
        self._warn_old_usage_deprecation()

        for key, value in six.iteritems(items):
            self._deprecated_info[key] = value
            setattr(self, key, value)

    @property
    def data(self):
        """The data for this diff.

        This must be accessed after :py:meth:`finalize` has been called.
        """
        if self._data is None:
            raise ValueError('ParsedDiffFile.data cannot be accessed until '
                             'finalize() is called.')

        return self._data

    def discard(self):
        """Discard this from the parent change.

        This will remove it from the list of files. It's intended for use
        when a diff parser is populating the diff but then determines the
        file is no longer needed.

        Version Added:
            4.0.5
        """
        assert self.parent_parsed_diff_change

        self.parent_parsed_diff_change.files.remove(self)

    def finalize(self):
        """Finalize the parsed diff.

        This makes the diff data available to consumers and closes the buffer
        for writing.
        """
        self._data = self._data_io.getvalue()
        self._data_io.close()

    def prepend_data(self, data):
        """Prepend data to the buffer.

        Args:
            data (bytes):
                The data to prepend.
        """
        if data:
            new_data_io = io.BytesIO()
            new_data_io.write(data)
            new_data_io.write(self._data_io.getvalue())

            self._data_io.close()
            self._data_io = new_data_io

    def append_data(self, data):
        """Append data to the buffer.

        Args:
            data (bytes):
                The data to append.
        """
        if data:
            self._data_io.write(data)

    def _warn_old_usage_deprecation(self):
        """Warn that a DiffParser is populating information in an old way."""
        if self.parser is None:
            message = (
                'Diff parsers must be updated to populate attributes on a '
                'ParsedDiffFile, instead of setting the information in a '
                'dictionary. This will be required in Review Board 5.0.'
            )
        else:
            message = (
                '%r must be updated to populate attributes on a '
                'ParsedDiffFile, instead of setting the information in a '
                'dictionary. This will be required in Review Board 5.0.'
                % type(self.parser)
            )

        RemovedInReviewBoard50Warning.warn(message, stacklevel=3)


class BaseDiffParser(object):
    """Base class for a diff parser.

    This is a low-level, basic foundational interface for a diff parser. It
    performs type checking of the incoming data and a couple of methods for
    subclasses to implement.

    Most SCM implementations will want to either subclass
    :py:class:`DiffParser` or use :py:class:`DiffXParser`.

    Version Added:
        4.0.5
    """

    def __init__(self, data):
        """Initialize the parser.

        Args:
            data (bytes):
                The diff content to parse.

        Raises:
            TypeError:
                The provided ``data`` argument was not a ``bytes`` type.
        """
        if not isinstance(data, bytes):
            raise TypeError(
                _('%s expects bytes values for "data", not %s')
                % (type(self).__name__, type(data)))

        self.data = data

    def parse_diff(self):
        """Parse the diff.

        This will parse the content of the file, returning any files that
        were found.

        This must be implemented by subclasses.

        Returns:
            ParsedDiff:
            The resulting parsed diff information.

        Raises:
            NotImplementedError:
                This wasn't implemented by a subclass.

            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing part of the diff. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        raise NotImplementedError

    def raw_diff(self, diffset_or_commit):
        """Return a raw diff as a string.

        This takes a DiffSet or DiffCommit and generates a new, single diff
        file that represents all the changes made. It's used to regenerate
        a diff and serve it up for other tools or processes to use.

        This must be implemented by subclasses.

        Args:
            diffset_or_commit (reviewboard.diffviewer.models.diffset.DiffSet or
                               reviewboard.diffviewer.models.diffcommit
                               .DiffCommit):
                The DiffSet or DiffCommit to render.

                If passing in a DiffSet, only the cumulative diff's file
                contents will be returned.

                If passing in a DiffCommit, only that commit's file contents
                will be returned.

        Returns:
            bytes:
            The diff composed of all the component FileDiffs.

        Raises:
            NotImplementedError:
                This wasn't implemented by a subclass.

            TypeError:
                The provided ``diffset_or_commit`` wasn't of a supported type.
        """
        raise NotImplementedError


class DiffParser(BaseDiffParser):
    """Parses diff files, allowing subclasses to specialize parsing behavior.

    This class provides the base functionality for parsing Unified Diff files.
    It looks for common information present in many variations of diffs,
    such as ``Index:`` lines, in order to extract files and their modified
    content from a diff.

    Subclasses can extend the parsing behavior to extract additional metadata
    or handle special representations of changes. They may want to override the
    following methods:

    * :py:meth:`parse_special_header`
    * :py:meth:`parse_diff_header`
    * :py:meth:`parse_filename_header`
    * :py:meth:`parse_after_headers`
    * :py:meth:`get_orig_commit_id`
    * :py:meth:`normalize_diff_filename`
    """

    #: A separator string below an Index header.
    #:
    #: This is commonly found immediately below an ``Index:`` header, meant
    #: to help locate the beginning of the metadata or changes made to a file.
    #:
    #: Its presence and location is not guaranteed.
    INDEX_SEP = b'=' * 67

    def __init__(self, data):
        """Initialize the parser.

        Args:
            data (bytes):
                The diff content to parse.

        Raises:
            TypeError:
                The provided ``data`` argument was not a ``bytes`` type.
        """
        from reviewboard.diffviewer.diffutils import split_line_endings

        super(DiffParser, self).__init__(data)

        self.base_commit_id = None
        self.new_commit_id = None
        self.lines = split_line_endings(data)

        self.parsed_diff = ParsedDiff(parser=self)
        self.parsed_diff_change = ParsedDiffChange(
            parsed_diff=self.parsed_diff)

    def parse_diff(self):
        """Parse the diff.

        Subclasses should override this if working with a diff format that
        extracts more than one change from a diff.

        Version Added:
            4.0.5:
            Historically, :py:meth:`parse` was the main method used to parse a
            diff. That's now used exclusively to parse a list of files for
            the default :py:attr:`parsed_diff_change`. The old method is
            around for compatibility, but is no longer called directly outside
            of this class.

        Returns:
            ParsedDiff:
            The resulting parsed diff information.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing part of the diff. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        class_name = type(self).__name__
        logger.debug('%s.parse_diff: Beginning parse of diff, size = %s',
                     class_name, len(self.data))

        parsed_diff_files = self.parse()
        parsed_diff_change = self.parsed_diff_change

        for parsed_diff_file in parsed_diff_files:
            if parsed_diff_file.parent_parsed_diff_change is None:
                parsed_diff_change.files.append(parsed_diff_file)

        logger.debug('%s.parse_diff: Finished parsing diff.', class_name)

        return self.parsed_diff

    def parse(self):
        """Parse the diff and return a list of files.

        This will parse the content of the file, returning any files that
        were found.

        Version Change:
            4.0.5:
            Historically, this was the main method used to parse a diff. It's
            now used exclusively to parse a list of files for the default
            :py:attr:`parsed_diff_change`, and :py:meth:`parse_diff` is the
            main method used to parse a diff. This method is around for
            compatibility, but is no longer called directly outside of this
            class.

        Returns:
            list of ParsedDiffFile:
            The resulting list of files.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing part of the diff. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        preamble = io.BytesIO()
        self.files = []
        parsed_file = None
        i = 0

        # Go through each line in the diff, looking for diff headers.
        while i < len(self.lines):
            next_linenum, new_file = self.parse_change_header(i)

            if new_file:
                # This line is the start of a new file diff.
                #
                # First, finalize the last one.
                if self.files:
                    self.files[-1].finalize()

                parsed_file = new_file

                # We need to prepend the preamble, if we have one.
                parsed_file.prepend_data(preamble.getvalue())

                preamble.close()
                preamble = io.BytesIO()

                self.files.append(parsed_file)
                i = next_linenum
            else:
                if parsed_file:
                    i = self.parse_diff_line(i, parsed_file)
                else:
                    preamble.write(self.lines[i])
                    preamble.write(b'\n')
                    i += 1

        if self.files:
            self.files[-1].finalize()

        preamble.close()

        return self.files

    def parse_diff_line(self, linenum, parsed_file):
        """Parse a line of data in a diff.

        This will append the line to the parsed file's data, and if the
        content represents active changes to a file, its insert/delete counts
        will be updated to reflect them.

        Args:
            linenum (int):
                The 0-based line number.

            parsed_file (ParsedDiffFile):
                The current parsed diff file info.

        Returns:
            int:
            The next line number to parse.
        """
        line = self.lines[linenum]

        if (parsed_file.orig_filename is not None and
            parsed_file.modified_filename is not None):
            if line.startswith(b'-'):
                parsed_file.delete_count += 1
            elif line.startswith(b'+'):
                parsed_file.insert_count += 1

        parsed_file.append_data(line)
        parsed_file.append_data(b'\n')

        return linenum + 1

    def parse_change_header(self, linenum):
        """Parse a header before a change to a file.

        This will attempt to parse the following information, starting at the
        specified line in the diff:

        1. Any special file headers (such as ``Index:`` lines) through
           :py:meth:`parse_special_header`
        2. A standard Unified Diff file header (through
           :py:meth:`parse_diff_header`)
        3. Any content after the header (through
           :py:meth:`parse_after_headers`)

        If the special or diff headers are able to populate the original and
        modified filenames and revisions/file details, and none of the methods
        above mark the file as skipped (by setting
        :py:attr:`ParsedDiffFile.skip`), then this will finish by appending
        all parsed data and returning a parsed file entry.

        Subclasses that need to control parsing logic should override one or
        more of the above methods.

        Args:
            linenum (int):
                The line number to begin parsing.

        Returns:
            tuple:
            A tuple containing the following:

            1. The next line number to parse
            2. The populated :py:class:`ParsedDiffFile` instance for this file

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the change header. This may be
                a corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        parsed_file = \
            ParsedDiffFile(parsed_diff_change=self.parsed_diff_change)
        start = linenum

        linenum = self.parse_special_header(linenum, parsed_file)
        linenum = self.parse_diff_header(linenum, parsed_file)

        skip = (
            parsed_file.skip or
            parsed_file.orig_filename is None or
            parsed_file.orig_file_details is None or
            parsed_file.modified_filename is None or
            parsed_file.modified_file_details is None
        )

        if not skip:
            # If we have enough information to represent a header, build the
            # file to return.
            if linenum < len(self.lines):
                linenum = self.parse_after_headers(linenum, parsed_file)

                skip = parsed_file.skip

        if skip:
            parsed_file.discard()
            parsed_file = None
        else:
            # The header is part of the diff, so make sure it gets in the
            # diff content.
            for line in self.lines[start:linenum]:
                parsed_file.append_data(line)
                parsed_file.append_data(b'\n')

        return linenum, parsed_file

    def parse_special_header(self, linenum, parsed_file):
        """Parse a special diff header marking the start of a new file's info.

        This attempts to locate an ``Index:`` line at the specified line
        number, which usually indicates the beginning of file's information in
        a diff (for Unified Diff variants that support it). By default, this
        method expects the line to be found at ``linenum``.

        If present, the value found immediately after the ``Index:`` will be
        stored in :py:attr:`ParsedDiffFile.index_header_value`, allowing
        subclasses to make a determination based on its contents (which may
        vary between types of diffs, but should include at least a filename.

        If the ``Index:`` line is not present, this won't do anything by
        default.

        Subclasses can override this to parse additional information before the
        standard diff header. They may also set :py:attr:`ParsedFileDiff.skip`
        to skip the rest of this file and begin parsing a new entry at the
        returned line number.

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the special header. This may be
                a corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        try:
            index_line = self.lines[linenum]
            is_index = index_line.startswith(b'Index: ')
        except IndexError:
            is_index = False

        if is_index:
            # Try to find the "====" line.
            temp_linenum = linenum + 1

            while temp_linenum + 1 < len(self.lines):
                line = self.lines[temp_linenum]

                if line == self.INDEX_SEP:
                    # We found the line. This is looking like a valid diff
                    # for CVS, Subversion, and other systems. Try to parse
                    # the data from the line.
                    try:
                        parsed_file.index_header_value = \
                            index_line.split(None, 1)[1]

                        # Set these for backwards-compatibility.
                        #
                        # This should be removed in Review Board 5.0.
                        parsed_file._deprecated_info['index'] = \
                            parsed_file.index_header_value
                    except ValueError:
                        raise DiffParserError('Malformed Index line', linenum)

                    linenum = temp_linenum + 1
                    break
                elif line.startswith((b'---', b'+++')):
                    # We never found that line, but we did hit the start of
                    # a diff file. We can't treat the "Index:" line as special
                    # in this case.
                    break

                temp_linenum += 1

        return linenum

    def parse_diff_header(self, linenum, parsed_file):
        """Parse a standard header before changes made to a file.

        This attempts to parse the ``---`` (original) and ``+++`` (modified)
        file lines, which are usually present right before any changes to the
        file. By default, this method expects the ``---`` line to be found at
        ``linenum``.

        If found, this will populate :py:attr:`ParsedDiffFile.orig_filename`,
        :py:attr:`ParsedDiffFile.orig_file_details`,
        :py:attr:`ParsedDiffFile.modified_filename`, and
        :py:attr:`ParsedDiffFile.modified_file_details`.

        This calls out to :py:meth:`parse_filename_header` to help parse
        the contents immediately after the ``---`` or ``+++``.

        Subclasses can override this to parse these lines differently, or to
        to process the results of these lines (such as converting special
        filenames to states like "deleted" or "new file"). They may also set
        :py:class:`ParsedFileDiff.skip` to skip the rest of this file and begin
        parsing a new entry at the returned line number.

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the diff header. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        try:
            line1 = self.lines[linenum]
            line2 = self.lines[linenum + 1]

            is_diff_header = (
                # Unified diff headers
                (line1.startswith(b'--- ') and line2.startswith(b'+++ ')) or

                # Context diff headers
                (line1.startswith(b'*** ') and line2.startswith(b'--- ') and
                 not line1.endswith(b' ****'))
            )
        except IndexError:
            is_diff_header = False

        if is_diff_header:
            # This is a unified or context diff header. Parse the
            # file and extra info.
            try:
                (parsed_file.orig_filename,
                 parsed_file.orig_file_details) = \
                    self.parse_filename_header(self.lines[linenum][4:],
                                               linenum)
                linenum += 1

                (parsed_file.modified_filename,
                 parsed_file.modified_file_details) = \
                    self.parse_filename_header(self.lines[linenum][4:],
                                               linenum)

                # Set these for backwards-compatibility.
                #
                # This should be removed in Review Board 5.0.
                parsed_file._deprecated_info['origFile'] = \
                    parsed_file.orig_filename
                parsed_file._deprecated_info['origInfo'] = \
                    parsed_file.orig_file_details
                parsed_file._deprecated_info['newFile'] = \
                    parsed_file.modified_filename
                parsed_file._deprecated_info['newInfo'] = \
                    parsed_file.modified_file_details

                linenum += 1
            except ValueError:
                raise DiffParserError(
                    'The diff file is missing revision information',
                    linenum)

        return linenum

    def parse_after_headers(self, linenum, parsed_file):
        """Parse information after a diff header but before diff data.

        This attempts to parse the information found after
        :py:meth:`parse_diff_headers` is called, but before gathering any lines
        that are part of the diff contents. It's intended for the few diff
        formats that may place content at this location.

        By default, this does nothing.

        Subclasses can override this to provide custom parsing of any lines
        that may exist here. They may also set :py:class:`ParsedFileDiff.skip`
        to skip the rest of this file and begin parsing a new entry at the
        returned line number.

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the diff header. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        return linenum

    def parse_filename_header(self, s, linenum):
        """Parse the filename found in a diff filename line.

        This parses the value after a ``---`` or ``+++`` indicator (or a
        special variant handled by a subclass), normalizing the filename and
        any following file details, and returning both for processing and
        storage.

        Often times, the file details will be a revision for the original
        file, but this is not guaranteed, and is up to the variation of the
        diff format.

        By default, this will assume that a filename and file details are
        separated by either a single tab, or two or more spaces. If neither
        are found, this will fail to parse.

        This must parse only the provided value, and cannot parse subsequent
        lines.

        Subclasses can override this behavior to parse these lines another
        way, or to normalize filenames (handling escaping or filenames with
        spaces as needed by that particular diff variation).

        Args:
            s (bytes):
                The value to parse.

            linenum (int):
                The line number containing the value to parse.

        Returns:
            tuple:
            A tuple containing:

            1. The filename (as bytes)
            2. The additional file information (as bytes)

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the diff header. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        if b'\t' in s:
            # There's a \t separating the filename and info. This is the
            # best case scenario, since it allows for filenames with spaces
            # without much work.
            return s.split(b'\t', 1)

        # There's spaces being used to separate the filename and info.
        # This is technically wrong, so all we can do is assume that
        # 1) the filename won't have multiple consecutive spaces, and
        # 2) there's at least 2 spaces separating the filename and info.
        if b'  ' in s:
            return re.split(br'  +', s, 1)

        raise DiffParserError('No valid separator after the filename was '
                              'found in the diff header',
                              linenum)

    def raw_diff(self, diffset_or_commit):
        """Return a raw diff as a string.

        This takes a DiffSet or DiffCommit and generates a new, single diff
        file that represents all the changes made. It's used to regenerate
        a diff and serve it up for other tools or processes to use.

        Subclasses can override this to provide any special logic for building
        the diff.

        Args:
            diffset_or_commit (reviewboard.diffviewer.models.diffset.DiffSet or
                               reviewboard.diffviewer.models.diffcommit
                               .DiffCommit):
                The DiffSet or DiffCommit to render.

                If passing in a DiffSet, only the cumulative diff's file
                contents will be returned.

                If passing in a DiffCommit, only that commit's file contents
                will be returned.

        Returns:
            bytes:
            The diff composed of all the component FileDiffs.

        Raises:
            TypeError:
                The provided ``diffset_or_commit`` wasn't of a supported type.
        """
        if hasattr(diffset_or_commit, 'cumulative_files'):
            # This will be a DiffSet.
            filediffs = diffset_or_commit.cumulative_files
        elif hasattr(diffset_or_commit, 'files'):
            # This will be a DiffCommit.
            filediffs = diffset_or_commit.files.all()
        else:
            raise TypeError('%r is not a valid value. Please pass a DiffSet '
                            'or DiffCommit.'
                            % diffset_or_commit)

        return b''.join(
            filediff.diff
            for filediff in filediffs
        )

    def get_orig_commit_id(self):
        """Return the commit ID of the original revision for the diff.

        By default, this returns ``None``. Subclasses would override this if
        they work with repositories that always look up changes to a file by
        the ID of the commit that made the changes instead of a per-file
        revision or ID.

        Non-``None`` values returned by this method will override the values
        being stored in :py:attr:`FileDiff.source_revision
        <reviewboard.diffviewer.models.filediff.FileDiff.source_revision>`.

        Implementations would likely want to parse out the commit ID from
        some prior header and return it here. By the time this is called, all
        files will have been parsed already.

        Returns:
            bytes:
            The commit ID used to override the source revision of any created
            :py:class:`~reviewboard.diffviewer.models.filediff.FileDiff`
            instances.
        """
        return None

    def normalize_diff_filename(self, filename):
        """Normalize filenames in diffs.

        This returns a normalized filename suitable for populating in
        :py:attr:`FileDiff.source_file
        <reviewboard.diffviewer.models.filediff.FileDiff.source_file>` or
        :py:attr:`FileDiff.dest_file
        <reviewboard.diffviewer.models.filediff.FileDiff.dest_file>`, or
        for when presenting a filename to the UI.

        By default, this strips off any leading slashes, which might occur due
        to differences in various diffing methods or APIs.

        Subclasses can override this to provide additional methods of
        normalization.

        Args:
            filename (unicode):
                The filename to normalize.

        Returns:
            unicode:
            The normalized filename.
        """
        if filename.startswith('/'):
            return filename[1:]
        else:
            return filename
