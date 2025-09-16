"""Tests for queries.

Version Added:
    8.0
"""

from __future__ import annotations

import pytest
import tree_sitter
from textwrap import dedent

from reviewboard.treesitter.core import get_language, get_queries
from reviewboard.treesitter.debug import DEBUG_TREESITTER
from reviewboard.treesitter.language import (
    SUPPORTED_LANGUAGES,
    SupportedLanguage,
)
from reviewboard.treesitter.query_utils import (
    apply_edits,
    get_gsub_edits,
    get_lua_match_edits,
    get_query_language,
    get_set3_edits,
)


@pytest.fixture(autouse=True, scope='session')
def django_db_setup() -> None:
    """Perform django database setup.

    These tests don't use the django database at all, and because of
    parameterize(), that ends up being a pretty big performance hit. This
    overrides db setup to be a no-op.
    """
    pass


@pytest.fixture
def _django_db_helper() -> None:  # pyright:ignore[reportUnusedFunction]
    """Perform internal django database work.

    These tests don't use the django database at all, and because of
    parameterize(), that ends up being a pretty big performance hit. This
    overrides db setup to be a no-op.
    """
    pass


SKIPPED_HIGHLIGHT_LANGUAGES: set[SupportedLanguage] = {
    # actionscript just doesn't have any highlights available.
    'actionscript',
}

HIGHLIGHT_TEST_PARAMS = [
    pytest.param('actionscript', marks=pytest.mark.xfail(
        reason='actionscript has no highlights available')),
]

if not DEBUG_TREESITTER:
    # These query files are currently known to be broken or missing.
    BROKEN_HIGHLIGHT_LANGUAGES: set[SupportedLanguage] = {
        'clarity',
        'cmake',
        'elisp',
        'fennel',
        'groovy',
        'haxe',
        'janet',
        'magik',
        'netlinx',
        'org',
        'pgn',
        'prisma',
        'scss',
        'squirrel',
        'svelte',
        'tablegen',
        'test',
        'v',
        'verilog',
        'vhdl',
        'vue',
        'zig',
    }
    SKIPPED_HIGHLIGHT_LANGUAGES |= BROKEN_HIGHLIGHT_LANGUAGES

    HIGHLIGHT_TEST_PARAMS += [
        pytest.param(language, marks=pytest.mark.xfail(
            reason=f'{language} has known broken highlights'))
        for language in sorted(BROKEN_HIGHLIGHT_LANGUAGES)
    ]


@pytest.mark.parametrize('language', [
    *HIGHLIGHT_TEST_PARAMS,
    *sorted(SUPPORTED_LANGUAGES - SKIPPED_HIGHLIGHT_LANGUAGES),
])
def test_load_highlights_queries(
    language: SupportedLanguage,
) -> None:
    """Test loading highlights queries.

    Args:
        language (str):
            The language to load queries for.
    """
    queries = get_queries(language, 'highlights.scm')
    assert queries is not None

    tree_sitter.Query(get_language(language), queries)


SKIPPED_INJECTION_LANGUAGES: set[SupportedLanguage] = set()
INJECTION_TEST_PARAMS = [
]

if not DEBUG_TREESITTER:
    # These query files are currently known to be broken.
    BROKEN_INJECTION_LANGUAGES: set[SupportedLanguage] = {
        'fennel',
        'groovy',
        'prisma',
        'squirrel',
    }
    SKIPPED_INJECTION_LANGUAGES |= BROKEN_INJECTION_LANGUAGES

    INJECTION_TEST_PARAMS += [
        pytest.param(language, marks=pytest.mark.xfail(
            reason=f'{language} has known broken injections'))
        for language in sorted(BROKEN_INJECTION_LANGUAGES)
    ]


@pytest.mark.parametrize('language', [
    *INJECTION_TEST_PARAMS,
    *sorted(SUPPORTED_LANGUAGES - SKIPPED_INJECTION_LANGUAGES),
])
def test_load_injections_queries(
    language: SupportedLanguage,
) -> None:
    """Test loading injections queries.

    Args:
        language (str):
            The language to load queries for.
    """
    queries = get_queries(language, 'injections.scm')

    if queries is None:
        pytest.skip(f'No injections queries for {language}')

    tree_sitter.Query(get_language(language), queries)


def test_apply_edits_no_matches() -> None:
    """Test applying no edits returns original content."""
    content = b'original content'
    result = apply_edits(content, [])
    assert result == content


def test_apply_edits_single_edit() -> None:
    """Test applying a single edit."""
    content = b'hello world'
    edits = [(6, 11, b'everyone')]
    result = apply_edits(content, edits)
    assert result == b'hello everyone'


def test_apply_edits_multiple_non_overlapping_edits() -> None:
    """Test applying multiple non-overlapping edits."""
    content = b'the quick brown fox'
    edits = [
        (4, 9, b'slow'),  # replace 'quick'
        (16, 19, b'dog')  # replace 'fox'
    ]
    result = apply_edits(content, edits)
    assert result == b'the slow brown dog'


def test_apply_edits_edits_applied_in_reverse_order() -> None:
    """Test that edits are applied in reverse byte order."""
    content = b'abc def ghi'
    edits = [
        (0, 3, b'xyz'),  # replace 'abc'
        (8, 11, b'123')  # replace 'ghi'
    ]
    result = apply_edits(content, edits)
    assert result == b'xyz def 123'


def test_apply_edits_deletion_edit() -> None:
    """Test deleting content with empty replacement."""
    content = b'remove this text'
    edits = [(7, 12, b'')]  # remove 'this '
    result = apply_edits(content, edits)
    assert result == b'remove text'


def test_apply_edits_insertion_edit() -> None:
    """Test inserting content with zero-length range."""
    content = b'hello world'
    edits = [(5, 5, b' beautiful')]  # insert at position 5
    result = apply_edits(content, edits)
    assert result == b'hello beautiful world'


def test_set3_edits_no_match() -> None:
    """Test with query containing no set! directives with 3 args."""
    content = '((identifier) @name)'
    content_bytes = content.encode()
    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_set3_edits(tree))
    assert edits == []


def test_set3_edits_single() -> None:
    """Test removal of set! directive with 3 arguments."""
    content = dedent("""
        ((identifier) @name
         (#set! @name foo bar))
    """).strip()
    content_bytes = content.encode()

    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_set3_edits(tree))
    assert len(edits) == 1

    result = apply_edits(content_bytes, edits)
    assert result.strip() == b''


def test_set3_edits_multiple() -> None:
    """Test removal of multiple set! directives with 3 arguments."""
    content = dedent("""
        ((identifier) @name
         (#set! @name foo bar))

        ((string) @str
         (#set! @str baz qux))
    """).strip()
    content_bytes = content.encode()

    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_set3_edits(tree))
    assert len(edits) == 2

    result = apply_edits(content_bytes, edits)
    assert result.strip() == b''


def test_set3_edits_with_set2() -> None:
    """Test that set! directives with 2 arguments are left intact."""
    content = dedent("""
        ((identifier) @name
         (#set! @name foo))
        ((identifier) @name
         (#set! @name bar baz))
    """).strip()
    content_bytes = content.encode()

    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_set3_edits(tree))
    assert len(edits) == 1

    result = apply_edits(content_bytes, edits)
    assert result == (
        b'((identifier) @name\n'
        b' (#set! @name foo))\n'
    )


def test_lua_match_edits_no_matches() -> None:
    """Test with query containing no lua-match? predicates."""
    content = dedent("""
        ((identifier) @name
         (#eq? @name "test"))
    """)
    content_bytes = content.encode()
    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_lua_match_edits(tree))
    assert edits == []


def test_lua_match_converts_predicate_name() -> None:
    """Test conversion of lua-match? to match?."""
    content = dedent("""
        ((identifier) @name
         (#lua-match? @name "test"))
        ((identifier) @name
         (#not-lua-match? @name "test"))
    """)
    content_bytes = content.encode()
    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_lua_match_edits(tree))
    assert len(edits) == 2

    result = apply_edits(content_bytes, edits)
    assert result == (
        b'\n((identifier) @name\n'
        b' (#match? @name "test"))'
        b'\n((identifier) @name\n'
        b' (#not-match? @name "test"))\n'
    )


def test_lua_match_edits_pattern_conversion() -> None:
    """Test conversion of Lua patterns to Python regex."""
    # Simple pattern that should convert cleanly
    content = dedent("""
        ((identifier) @name
         (#lua-match? @name "^%a$"))
    """)
    content_bytes = content.encode()
    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_lua_match_edits(tree))
    assert len(edits) == 1

    result = apply_edits(content_bytes, edits)
    assert result == (
        b'\n((identifier) @name\n'
        b' (#match? @name "^[A-Za-z]$"))\n'
    )


def test_gsub_edits_no_match() -> None:
    """Test with query containing no gsub! directives."""
    content = dedent("""
        ((identifier) @name
         (#eq? @name "test"))
    """)
    content_bytes = content.encode()
    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_gsub_edits(tree))
    assert edits == []


def test_gsub_edits_pattern_conversion() -> None:
    """Test conversion of Lua patterns in gsub! directive."""
    # Simple pattern conversion
    content = dedent("""
        ((identifier) @name
         (#gsub! @name "^%a$" "replacement"))
    """)
    content_bytes = content.encode()
    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_gsub_edits(tree))
    assert len(edits) == 1

    result = apply_edits(content_bytes, edits)
    assert result == (
        b'\n((identifier) @name'
        b'\n (#gsub! @name "^[A-Za-z]$" "replacement"))\n'
    )


def test_gsub_edits_backref_conversion() -> None:
    """Test conversion of Lua backreferences to Python format."""
    content = dedent("""
        ((identifier) @name
         (#gsub! @name "(.*)" "%1"))
    """)
    content_bytes = content.encode()
    language = get_query_language()
    tree = tree_sitter.Parser(language).parse(content_bytes)

    edits = list(get_gsub_edits(tree))
    assert len(edits) == 1

    result = apply_edits(content_bytes, edits)
    assert result == (
        b'\n((identifier) @name\n'
        b' (#gsub! @name "(?s)(.*)" "\\\\1"))\n'
    )
