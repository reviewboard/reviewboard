from __future__ import unicode_literals

import logging
import re

from django.utils import six
from django.utils.six.moves import cStringIO as StringIO

from reviewboard.diffviewer.errors import DiffParserError


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

    def __init__(self):
        """Initialize the parsed file information."""
        self.origFile = None
        self.newFile = None
        self.origInfo = None
        self.newInfo = None
        self.origChangesetId = None
        self.binary = False
        self.deleted = False
        self.moved = False
        self.copied = False
        self.is_symlink = False
        self.insert_count = 0
        self.delete_count = 0

        self._data_io = StringIO()
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
            new_data_io = StringIO()
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

        preamble = StringIO()
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
                preamble = StringIO()

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

    def parse_diff_line(self, linenum, info):
        line = self.lines[linenum]

        if info.origFile is not None and info.newFile is not None:
            if line.startswith(b'-'):
                info.delete_count += 1
            elif line.startswith(b'+'):
                info.insert_count += 1

        info.append_data(line)
        info.append_data(b'\n')

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

            for attr in ('origFile', 'newFile', 'origInfo', 'newInfo'):
                attr_value = info.get(attr)

                if isinstance(attr_value, six.binary_type):
                    attr_value = attr_value.decode('utf-8')

                setattr(parsed_file, attr, attr_value)

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
        if b"\t" in s:
            # There's a \t separating the filename and info. This is the
            # best case scenario, since it allows for filenames with spaces
            # without much work.
            return s.split(b"\t", 1)

        # There's spaces being used to separate the filename and info.
        # This is technically wrong, so all we can do is assume that
        # 1) the filename won't have multiple consecutive spaces, and
        # 2) there's at least 2 spaces separating the filename and info.
        if b"  " in s:
            return re.split(r"  +", s, 1)

        raise DiffParserError("No valid separator after the filename was " +
                              "found in the diff header",
                              linenum)

    def raw_diff(self, diffset):
        """Returns a raw diff as a string.

        The returned diff as composed of all FileDiffs in the provided diffset.
        """
        return b''.join([filediff.diff for filediff in diffset.files.all()])

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
