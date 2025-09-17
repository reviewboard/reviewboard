from __future__ import annotations

from reviewboard.diffviewer.interesting_lines import (
    HEADER_REGEXES,
    HEADER_REGEX_ALIASES,
)


#: Common extensions for source code header files.
#:
#: This is largely geared toward C-like languages.
#:
#: Version Added:
#:     7.0.2
HEADER_EXTENSIONS = {
    'h',
    'H',
    'hh',
    'hpp',
    'hxx',
    'h++',
}


#: Common extensions for source code implementation files.
#:
#: This is largely geared toward C-like languages.
#:
#: Version Added:
#:     7.0.2
IMPL_EXTENSIONS = {
    'c',
    'C',
    'cc',
    'cpp',
    'cxx',
    'c++',
    'm',
    'mm',
    'M',
}


__all__ = [
    'HEADER_EXTENSIONS',
    'HEADER_REGEXES',
    'HEADER_REGEX_ALIASES',
    'IMPL_EXTENSIONS',
]


__autodoc_excludes__ = __all__
