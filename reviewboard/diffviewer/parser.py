from __future__ import unicode_literals

import io
import logging
import re

from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.six.moves import cStringIO as StringIO
from django.utils.translation import ugettext as _
from djblets.util.properties import AliasProperty, TypedProperty

from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.diffviewer.errors import DiffParserError
from reviewboard.scmtools.core import Revision


class ParsedDiffFile(object):
    """A parsed file from a diff.

    This stores information on a single file represented in a diff, including
    the contents of that file's diff, as parsed by :py:class:`DiffParser` or
    one of its subclasses.

    Parsers should set the attributes on this based on the contents of the
    diff, and should add any data found in the diff.

    This class is meant to be used internally and by subclasses of
    :py:class:`DiffParser`.
    """

    #: The parsed original name of the file.
    orig_filename = TypedProperty(bytes)

    #: The parsed file details of the original file.
    #:
    #: This will usually be a revision.
    orig_file_details = TypedProperty((bytes, Revision))

    #: The parsed modified name of the file.
    #:
    #: This may be the same as :py:attr:`orig_filename`.
    modified_filename = TypedProperty(bytes)

    #: The parsed file details of the modified file.
    #:
    #: This will usually be a revision.
    modified_file_details = TypedProperty((bytes, Revision))

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

    def __init__(self):
        """Initialize the parsed file information."""
        self.origChangesetId = None
        self.binary = False
        self.deleted = False
        self.moved = False
        self.copied = False
        self.is_symlink = False
        self.insert_count = 0
        self.delete_count = 0

        self._data_io = io.BytesIO()
        self._data = None

    @property
    def data(self):
        """The data for this diff.

        This must be accessed after :py:meth:`finalize` has been called.
        """
        if self._data is None:
            raise ValueError('ParsedDiffFile.data cannot be accessed until '
                             'finalize() is called.')

        return self._data

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


class DiffParser(object):
    """
    Parses diff files into fragments, taking into account special fields
    present in certain types of diffs.
    """

    INDEX_SEP = b"=" * 67

    def __init__(self, data):
        from reviewboard.diffviewer.diffutils import split_line_endings

        if not isinstance(data, bytes):
            raise TypeError(
                _('%s expects bytes values for "data", not %s')
                % (self.__class__.__name__, type(data)))

        self.base_commit_id = None
        self.new_commit_id = None
        self.data = data
        self.lines = split_line_endings(data)

    def parse(self):
        """
        Parses the diff, returning a list of File objects representing each
        file in the diff.
        """
        logging.debug("DiffParser.parse: Beginning parse of diff, size = %s",
                      len(self.data))

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

        logging.debug("DiffParser.parse: Finished parsing diff.")

        return self.files

    def parse_diff_line(self, linenum, parsed_file):
        """Parse a line of data in a diff.

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
        """
        Parses part of the diff beginning at the specified line number, trying
        to find a diff header.
        """
        info = {}
        parsed_file = None
        start = linenum
        linenum = self.parse_special_header(linenum, info)
        linenum = self.parse_diff_header(linenum, info)

        if info.get('skip', False):
            return linenum, None

        # If we have enough information to represent a header, build the
        # file to return.
        if ('origFile' in info and 'newFile' in info and
            'origInfo' in info and 'newInfo' in info):
            if linenum < len(self.lines):
                linenum = self.parse_after_headers(linenum, info)

                if info.get('skip', False):
                    return linenum, None

            parsed_file = ParsedDiffFile()
            parsed_file.origChangesetId = info.get('origChangesetId')

            for attr in ('binary', 'deleted', 'moved', 'copied', 'is_symlink'):
                setattr(parsed_file, attr, info.get(attr, False))

            for parsed_file_attr, info_attr in (('orig_filename',
                                                 'origFile'),
                                                ('modified_filename',
                                                 'newFile')):
                filename = info.get(info_attr)

                if filename is not None:
                    assert isinstance(filename, bytes), (
                        '%s must be a byte string, not %s'
                        % (info_attr, type(filename)))

                setattr(parsed_file, parsed_file_attr, filename)

            for parsed_file_attr, info_attr in (('orig_file_details',
                                                 'origInfo'),
                                                ('modified_file_details',
                                                 'newInfo')):
                revision = info.get(info_attr)

                if revision is not None:
                    assert isinstance(revision, (bytes, Revision)), (
                        '%s must be a byte string or Revision, not %s'
                        % (info_attr, type(revision)))

                    if isinstance(revision, Revision):
                        revision = bytes(revision)

                setattr(parsed_file, parsed_file_attr, revision)

            # The header is part of the diff, so make sure it gets in the
            # diff content.
            lines = self.lines[start:linenum]

            for line in lines:
                parsed_file.append_data(line)
                parsed_file.append_data(b'\n')

        return linenum, parsed_file

    def parse_special_header(self, linenum, info):
        """
        Parses part of a diff beginning at the specified line number, trying
        to find a special diff header. This usually occurs before the standard
        diff header.

        The line number returned is the line after the special header,
        which can be multiple lines long.
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
                        info['index'] = index_line.split(None, 1)[1]
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

    def parse_diff_header(self, linenum, info):
        """
        Parses part of a diff beginning at the specified line number, trying
        to find a standard diff header.

        The line number returned is the line after the special header,
        which can be multiple lines long.
        """
        try:
            line1 = self.lines[linenum]
            line2 = self.lines[linenum + 1]

            is_diff_header = (
               (line1.startswith(b'--- ') and line2.startswith(b'+++ ')) or
               (line1.startswith(b'*** ') and line2.startswith(b'--- ') and
                not line1.endswith(b' ****'))
            )
        except IndexError:
            is_diff_header = False

        if is_diff_header:
            # This is a unified or context diff header. Parse the
            # file and extra info.
            try:
                info['origFile'], info['origInfo'] = \
                    self.parse_filename_header(self.lines[linenum][4:],
                                               linenum)
                linenum += 1

                info['newFile'], info['newInfo'] = \
                    self.parse_filename_header(self.lines[linenum][4:],
                                               linenum)
                linenum += 1
            except ValueError:
                raise DiffParserError(
                    'The diff file is missing revision information',
                    linenum)

        return linenum

    def parse_after_headers(self, linenum, info):
        """Parses data after the diff headers but before the data.

        By default, this does nothing, but a DiffParser subclass can
        override to look for special headers before the content.
        """
        return linenum

    def parse_filename_header(self, s, linenum):
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
        """
        if hasattr(diffset_or_commit, 'cumulative_files'):
            filediffs = diffset_or_commit.cumulative_files
        elif hasattr(diffset_or_commit, 'files'):
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
        """Returns the commit ID of the original revision for the diff.

        This is overridden by tools that only use commit IDs, not file
        revision IDs.
        """
        return None

    def normalize_diff_filename(self, filename):
        """Normalize filenames in diffs.

        This strips off any leading slashes, which might occur due to
        differences in various diffing methods or APIs.
        """
        if filename.startswith('/'):
            return filename[1:]
        else:
            return filename
