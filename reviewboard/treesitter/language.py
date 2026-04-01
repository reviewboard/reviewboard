"""Utilities for and information about Tree Sitter languages.

Version Added:
    9.0
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, get_args

from tree_sitter_language_pack import SupportedLanguage

from reviewboard.treesitter._languages import (
    FILE_SUFFIX_TO_LANGUAGES,
    MIME_TYPE_TO_LANGUAGE,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


#: The supported languages as a set.
#:
#: Version Added:
#:     9.0
SUPPORTED_LANGUAGES: set[SupportedLanguage] = set(get_args(SupportedLanguage))


#: Overrides for specific languages.
#:
#: There are some filenames that have multiple possible languages where the one
#: that appears first in the list isn't ideal. This provides overrides to
#: select the most likely one.
#:
#: Version Added:
#:     9.0
# TODO: make this configurable the way we do with Pygments lexers.
LANGUAGE_OVERRIDES: Mapping[str, SupportedLanguage] = {
    '.h': 'c',
    '.js': 'javascript',
    '.scm': 'scheme',
    '.ts': 'typescript',
    '.xml': 'xml',
}


#: Markdown info string to language mappings for injection.
#:
#: Version Added:
#:     9.0
MARKDOWN_INFO_STRING_LANGUAGES: Mapping[str, SupportedLanguage] = {
    'asm': 'asm',
    'assembly': 'asm',
    'c': 'c',
    'c++': 'cpp',
    'cc': 'cpp',
    'clj': 'clojure',
    'cljs': 'clojure',
    'clojure': 'clojure',
    'cmake': 'cmake',
    'cpp': 'cpp',
    'cs': 'csharp',
    'csharp': 'csharp',
    'css': 'css',
    'cxx': 'cpp',
    'dart': 'dart',
    'docker': 'dockerfile',
    'dockerfile': 'dockerfile',
    'elisp': 'elisp',
    'elixir': 'elixir',
    'erl': 'erlang',
    'erlang': 'erlang',
    'ex': 'elixir',
    'exs': 'elixir',
    'fish': 'bash',
    'go': 'go',
    'groovy': 'groovy',
    'h': 'c',
    'h++': 'cpp',
    'haskell': 'haskell',
    'hh': 'cpp',
    'hpp': 'cpp',
    'hs': 'haskell',
    'html': 'html',
    'hxx': 'cpp',
    'java': 'java',
    'jl': 'julia',
    'js': 'javascript',
    'json': 'json',
    'json5': 'json',
    'jsonc': 'json',
    'jsx': 'javascript',
    'julia': 'julia',
    'kotlin': 'kotlin',
    'kt': 'kotlin',
    'latex': 'latex',
    'lua': 'lua',
    'make': 'make',
    'makefile': 'make',
    'markdown': 'markdown',
    'matlab': 'matlab',
    'md': 'markdown',
    'mdown': 'markdown',
    'mdx': 'markdown',
    'mkd': 'markdown',
    'ml': 'ocaml',
    'mysql': 'sql',
    'nix': 'nix',
    'ocaml': 'ocaml',
    'octave': 'matlab',
    'perl': 'perl',
    'php': 'php',
    'pl': 'perl',
    'postgres': 'sql',
    'postgresql': 'sql',
    'powershell': 'powershell',
    'ps1': 'powershell',
    'py': 'python',
    'r': 'r',
    'rb': 'ruby',
    'rs': 'rust',
    'rst': 'rst',
    's': 'asm',
    'scala': 'scala',
    'scheme': 'scheme',
    'scm': 'scheme',
    'scss': 'scss',
    'sh': 'bash',
    'shell': 'bash',
    'sol': 'solidity',
    'solidity': 'solidity',
    'sql': 'sql',
    'sqlite': 'sql',
    'swift': 'swift',
    'tcl': 'tcl',
    'tex': 'latex',
    'thrift': 'thrift',
    'toml': 'toml',
    'ts': 'typescript',
    'tsx': 'typescript',
    'vim': 'vim',
    'viml': 'vim',
    'xml': 'xml',
    'yaml': 'yaml',
    'yml': 'yaml',
    'zig': 'zig',
    'zsh': 'bash',
}


def get_language_name_for_file(
    filename: str,
    mimetype: (str | None) = None,
) -> SupportedLanguage | None:
    """Get the Tree Sitter language name for a given file.

    Version Added:
        9.0

    Args:
        filename (str):
            The name of the file.

        mimetype (str, optional):
            The MIME type of the file.

    Returns:
        str:
        The matching language name. This will be ``None`` if there is no
        matching language.
    """
    # If we have a known mimetype, always prefer that.
    if mimetype:
        language_name = get_language_name_for_mimetype(mimetype)

        if language_name:
            return language_name

    for suffix, languages in FILE_SUFFIX_TO_LANGUAGES.items():
        if filename.endswith(suffix):
            return LANGUAGE_OVERRIDES.get(suffix, languages[0])

    return None


@lru_cache
def get_language_name_for_info_string(
    info_string: str,
) -> SupportedLanguage | None:
    """Get the Tree Sitter language name from Markdown code block info string.

    Version Added:
        9.0

    Args:
        info_string (str):
            The info string from a Markdown fenced code block.

    Returns:
        reviewboard.treesitter.language.SupportedLanguage:
        The corresponding language name, or None if not supported.
    """
    info_string = info_string.lower().strip()

    # Use markdown languages first.
    if language_name := MARKDOWN_INFO_STRING_LANGUAGES.get(info_string):
        assert language_name in SUPPORTED_LANGUAGES
        return language_name

    if info_string in SUPPORTED_LANGUAGES:
        return info_string

    return None


@lru_cache
def get_language_name_for_mimetype(
    mimetype: str,
) -> SupportedLanguage | None:
    """Get language name for a mimetype.

    Version Added:
        9.0

    Args:
        mimetype (str):
            The MIME type.

    Returns:
        reviewboard.treesitter.language.SupportedLanguage:
        The corresponding language name, or None if not supported.
    """
    if language_name := MIME_TYPE_TO_LANGUAGE.get(mimetype):
        assert language_name in SUPPORTED_LANGUAGES

        return language_name

    # See if there's a matching language name in "type/language"
    if '/' in mimetype:
        parts = mimetype.split('/')
        subtype = parts[-1]

        if subtype in SUPPORTED_LANGUAGES:
            return subtype

        # Also check to see if we have "type/x-language"
        if subtype.startswith('x-'):
            subtype = subtype.removeprefix('x-')

            if subtype in SUPPORTED_LANGUAGES:
                return subtype

    return None


__all__ = [
    'SUPPORTED_LANGUAGES',
    'SupportedLanguage',
    'get_language_name_for_file',
    'get_language_name_for_info_string',
    'get_language_name_for_mimetype',
]
