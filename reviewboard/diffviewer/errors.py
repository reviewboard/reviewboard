from __future__ import unicode_literals

from django.utils.translation import ugettext as _


class UserVisibleError(Exception):
    """A user-visible error shown in the rendered output."""


class DiffCompatError(Exception):
    """Unknown diff compatibility version error."""


class DiffTooBigError(ValueError):
    """The supplied diff file was too large."""

    def __init__(self, message, max_diff_size):
        """Initialize the error.

        Args:
            message (unicode):
                The error message to display.

            max_diff_size (int):
                The maximum allowable diff size, in bytes.
        """
        super(DiffTooBigError, self).__init__(message)
        self.max_diff_size = max_diff_size


class EmptyDiffError(ValueError):
    """A supplied diff file was empty."""


class DiffParserError(Exception):
    """An error encountered when parsing a diff file."""

    def __init__(self, message, linenum=None):
        """Initialize the error.

        Args:
            message (unicode):
                The error message to display.

            linenum (int):
                The line number in the diff file where the parse error
                occurred.
        """
        super(DiffParserError, self).__init__(message)
        self.linenum = linenum


class PatchError(UserVisibleError):
    """An error which occurred when trying to apply a patch."""

    def __init__(self, filename, error_output, orig_file, new_file,
                 diff, rejects):
        """Initialize the error.

        Args:
            filename (unicode):
                The name of the file being patched.

            error_output (unicode):
                The error output from the ``patch`` command.

            orig_file (bytes):
                The original contents of the file.

            new_file (bytes):
                The new contents of the file, if available.

            diff (bytes):
                The contents of the diff.

            rejects (bytes):
                The contents of the rejects file, if available.
        """
        self.filename = filename
        self.error_output = error_output
        self.orig_file = orig_file
        self.new_file = new_file
        self.diff = diff
        self.rejects = rejects

        super(PatchError, self).__init__(
            _('The patch to "%s" did not apply cleanly.') % filename)
