"""Base definitions for differ implementations."""

from __future__ import annotations

import os
from typing import Any, Literal, TYPE_CHECKING

from django.utils.translation import gettext as _

from reviewboard.diffviewer.errors import DiffCompatError
from reviewboard.diffviewer.filetypes import (HEADER_REGEXES,
                                              HEADER_REGEX_ALIASES)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from re import Pattern

    from typing_extensions import TypeAlias


class DiffCompatVersion:
    """Diff compatibility versions."""

    #: Python SequenceMatcher differ.
    SMDIFFER = 0

    #: Myers differ.
    MYERS = 1

    #: Myers differ with bailing on a too high SMS cost.
    #:
    #: This prevents very long diff times for certain files.
    MYERS_SMS_COST_BAIL = 2

    #: The default compatibility version to use.
    DEFAULT = MYERS_SMS_COST_BAIL

    #: Versions that use the Myers diff algorithm.
    MYERS_VERSIONS = (MYERS, MYERS_SMS_COST_BAIL)


#: The potential values for opcode tags.
#:
#: Version Added:
#:     8.0
DiffOpcodeTag: TypeAlias = Literal[
    'delete',
    'equal',
    'filtered-equal',
    'insert',
    'replace',
]


#: The structure used for opcodes.
#:
#: Version Added:
#:     8.0
DiffOpcode: TypeAlias = tuple[
    DiffOpcodeTag,  # tag
    int,  # i1
    int,  # i2
    int,  # j1
    int,  # j2
]


#: The structure used for opcodes with metadata.
#:
#: Version Added:
#:     8.0
DiffOpcodeWithMetadata: TypeAlias = tuple[
    DiffOpcodeTag,  # tag
    int,  # i1
    int,  # i2
    int,  # j1
    int,  # j2
    dict[str, Any] | None,  # metadata
]


class Differ:
    """Base class for differs."""

    ######################
    # Instance variables #
    ######################

    #: The original version of the file, split into lines.
    a: Sequence[str]

    #: The modified version of the file, split into lines.
    b: Sequence[str]

    #: The diff compatibility version.
    #:
    #: Version Changed:
    #:     8.0:
    #:     Changed to not allow ``None`` values.
    compat_version: int

    #: Whether to ignore whitespace.
    ignore_space: bool

    #: Regular expressions for finding interesting lines.
    interesting_line_regexes: list[tuple[str, Pattern[str]]]

    #: Interesting lines in the file.
    #:
    #: Version Changed:
    #:     8.0:
    #:     Changed from a 2-element list to a 2-tuple.
    interesting_lines: tuple[
        dict[str, list[tuple[int, str]]],
        dict[str, list[tuple[int, str]]],
    ]

    def __init__(
        self,
        a: Sequence[str],
        b: Sequence[str],
        ignore_space: bool = False,
        compat_version: int = DiffCompatVersion.DEFAULT,
    ) -> None:
        """Initialize the differ.

        Args:
            a (list of str):
                The original version of the file, split into lines.

            b (list of str):
                The modified version of the file, split into lines.

            ignore_space (bool, optional):
                Whether to ignore whitespace changes.

            compat_version (int, optional):
                The diff compatibility version.
        """
        if type(a) is not type(b):
            raise TypeError

        self.a = a
        self.b = b
        self.ignore_space = ignore_space
        self.compat_version = compat_version
        self.interesting_line_regexes = []
        self.interesting_lines = ({}, {})

    def add_interesting_line_regex(
        self,
        name: str,
        regex: Pattern[str],
    ) -> None:
        """Register a regular expression used to look for interesting lines.

        All interesting lines found that match the regular expression will
        be stored and tagged with the given name. Callers can use
        get_interesting_lines to get the results.

        Args:
            name (str):
                The name of the regex to register.

            regex (re.Pattern):
                The compiled regular expression.
        """
        self.interesting_line_regexes.append((name, regex))
        self.interesting_lines[0][name] = []
        self.interesting_lines[1][name] = []

    def add_interesting_lines_for_headers(
        self,
        filename: str,
    ) -> None:
        """Register patterns for interesting lines for headers.

        This is a convenience over add_interesting_line_regex that will watch
        for headers (functions, classes, etc.) for the file type matching
        the given filename.

        Args:
            filename (str):
                The filename of the file being diffed.
        """
        regexes = []

        if filename in HEADER_REGEX_ALIASES:
            regexes = HEADER_REGEXES[HEADER_REGEX_ALIASES[filename]]
        else:
            ext = os.path.splitext(filename)[1]

            if ext in HEADER_REGEXES:
                regexes = HEADER_REGEXES[ext]
            elif ext in HEADER_REGEX_ALIASES:
                regexes = HEADER_REGEXES[HEADER_REGEX_ALIASES[ext]]

        for regex in regexes:
            self.add_interesting_line_regex('header', regex)

    def get_interesting_lines(
        self,
        name: str,
        is_modified_file: bool,
    ) -> list[tuple[int, str]]:
        """Return the interesting lines tagged with the given name.

        Args:
            name (str):
                The name of the type of interesting lines to get.

            is_modified_file (bool):
                If ``True``, get interesting lines for the modified version of
                the file. If ``False``, get interesting lines for the original
                version of the file.

        Returns:
            list of tuple:
            A list of interesting lines in the file. Each item is a 2-tuple of
            (line number, line).
        """
        if is_modified_file:
            index = 1
        else:
            index = 0

        return self.interesting_lines[index].get(name, [])

    def get_opcodes(self) -> Iterator[DiffOpcode]:
        """Yield the opcodes for the diff.

        Yields:
            DiffOpcode:
            The opcodes for the diff.
        """
        raise NotImplementedError


def get_differ(
    a: Sequence[str],
    b: Sequence[str],
    ignore_space: bool = False,
    compat_version: int = DiffCompatVersion.DEFAULT,
) -> Differ:
    """Return a differ for with the given settings.

    By default, this will return the MyersDiffer. Older differs can be used
    by specifying a compat_version, but this is only for *really* ancient
    diffs, currently.

    Args:
        a (list of str):
            The original file, split into lines.

        b (list of str):
            The modified file, split into lines.

        ignore_space (bool):
            Whether to ignore whitespace when performing the diff.

        compat_version (int):
            The diff compatibility version.

    Returns:
        Differ:
        The new differ instance.

    Raises:
        reviewboard.diffviewer.errors.DiffCompatError:
            The compatibility version was not valid.
    """
    cls = None

    if compat_version in DiffCompatVersion.MYERS_VERSIONS:
        from reviewboard.diffviewer.myersdiff import MyersDiffer
        cls = MyersDiffer
    elif compat_version == DiffCompatVersion.SMDIFFER:
        from reviewboard.diffviewer.smdiff import SMDiffer
        cls = SMDiffer
    else:
        raise DiffCompatError(
            _(
                'Invalid diff compatibility version ({compat_version}) passed '
                'to Differ'
            ).format(compat_version=compat_version)
        )

    return cls(a, b, ignore_space, compat_version=compat_version)
