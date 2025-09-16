"""Core interfaces for working with Tree Sitter.

Version Added:
    8.0
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_language as lp_get_language

if TYPE_CHECKING:
    from reviewboard.treesitter.language import SupportedLanguage


@lru_cache
def get_language(
    language_name: SupportedLanguage,
) -> Language:
    """Get a tree sitter language object.

    Version Added:
        8.0

    Args:
        language_name (str):
            The language name to use.

    Returns:
        tree_sitter.Language:
        The language object.

    Raises:
        LookupError:
            A matching grammar for the language name could not be loaded.
    """
    return lp_get_language(language_name)


@lru_cache
def get_parser(
    language_name: SupportedLanguage,
) -> Parser:
    """Get a tree sitter parser.

    Version Added:
        8.0

    Args:
        language_name (str):
            The language name to use.

    Returns:
        tree_sitter.Parser:
        The parser object.

    Raises:
        LookupError:
            A matching grammar for the language name could not be loaded.
    """
    return Parser(get_language(language_name))


@lru_cache
def get_queries(
    language_name: SupportedLanguage,
    filename: str,
) -> str | None:
    """Get queries for a given language.

    Version Added:
        8.0

    Args:
        language_name (reviewboard.treesitter.language.SupportedLanguage):
            The language name for cache key.

        filename (str):
            The query filename (e.g., 'highlights.scm').

    Returns:
        str or None:
        The cached query instance, or None if no query exists.
    """
    base_path = Path(__file__).parent / 'queries' / language_name
    path = base_path / filename

    try:
        with path.open(encoding='utf-8') as f:
            return f.read()
    except OSError:
        return None
