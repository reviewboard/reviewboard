"""Unit tests for Tree Sitter predicates.

Version Added:
    9.0
"""

from __future__ import annotations

from textwrap import dedent

import pytest
import tree_sitter
from tree_sitter_language_pack import get_parser

from reviewboard.treesitter.predicates import create_predicate_handler


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


def test_any_contains_predicate_positive() -> None:
    """Test any-contains? predicate with matching text."""
    content = '<div><span>Hello</span><span>World</span></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#any-contains? @content "World"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'content' in captures
    nodes = captures['content']

    assert len(nodes) == 1
    assert nodes[0].text == b'World'


def test_any_contains_predicate_multiple_partial() -> None:
    """Test any-contains? predicate with multiple arguments."""
    content = '<div><span>Hello</span><span>World</span></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#any-contains? @content "Hello" "Everyone"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'content' in captures
    nodes = captures['content']

    assert len(nodes) == 1
    assert nodes[0].text == b'Hello'


def test_any_contains_predicate_multiple_positive() -> None:
    """Test any-contains? predicate with multiple matching arguments."""
    content = '<div><span>Hello</span><span>World</span></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#any-contains? @content "Hello" "World"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'content' in captures
    nodes = captures['content']

    assert len(nodes) == 2
    assert nodes[0].text == b'Hello'
    assert nodes[1].text == b'World'


def test_any_contains_predicate_negative() -> None:
    """Test any-contains? predicate with non-matching text."""
    content = '<div><span>Hello</span><span>World</span></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#any-contains? @content "NotFound"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}


def test_any_contains_predicate_multiple_negative() -> None:
    """Test any-contains? predicate with multiple non-matching arguments."""
    content = '<div><span>Hello</span><span>World</span></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#any-contains? @content "Hi" "Everyone"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}


def test_contains_predicate_positive() -> None:
    """Test contains? predicate with matching text."""
    content = '<div class="highlight">Hello World</div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#contains? @content "World"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'content' in captures
    nodes = captures['content']

    assert len(nodes) == 1
    assert nodes[0].text == b'Hello World'


def test_contains_predicate_multiple_positive() -> None:
    """Test contains? predicate with multiple matching arguments."""
    content = '<div class="highlight">Hello World</div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#contains? @content "Hello" "World"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'content' in captures
    nodes = captures['content']

    assert len(nodes) == 1
    assert nodes[0].text == b'Hello World'


def test_contains_predicate_negative() -> None:
    """Test contains? predicate with non-matching text."""
    content = '<div class="highlight">Hello World</div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#contains? @content "NotFound"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}


def test_contains_predicate_multiple_negative() -> None:
    """Test contains? predicate with multiple arguments and no match."""
    content = '<div class="highlight">Hello World</div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (element
         (text) @content
         (#contains? @content "Hello" "Dolly"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}


def test_gsub_directive() -> None:
    """Test gsub! directive."""
    content = (
        '<script type="application/javascript">console.log("test");</script>'
    )
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        (attribute_name) @tag.attribute

        (script_element
          (start_tag
            (attribute
              (attribute_name) @_attr
              (#eq? @_attr "type")
              (quoted_attribute_value
                (attribute_value) @injection.language)))
          (raw_text) @injection.content
          (#gsub! @injection.language "(?s)(.+)/(.+)" "\\\\2"))
    """)
    query = tree_sitter.Query(ts_language, queries)

    # The gsub! directive should have stored the transformed language in
    # pattern_settings.
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    matches = cursor.matches(tree.root_node, predicate_handler)

    for pattern_index, _match in matches:
        settings = query.pattern_settings(pattern_index)

        if 'injection.language' in settings:
            assert settings['injection.language'] == 'javascript'
            break
    else:
        pytest.fail(
            '"injection.language" was not found in pattern settings')


def test_gsub_directive_invalid_regex() -> None:
    """Test gsub! directive with an invalid regex."""
    content = '<script type="text/javascript">test</script>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    # Test that an invalid regex still matches, but transformation should fail
    # gracefully.
    queries = dedent("""
        (script_element
          (start_tag
            (attribute
              (quoted_attribute_value
                (attribute_value) @lang)))
          (#gsub! @lang "[invalid" "replacement"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    matches = cursor.matches(tree.root_node, predicate_handler)

    for pattern_index, _match in matches:
        settings = query.pattern_settings(pattern_index)
        # Should contain original text since regex failed
        if 'lang' in settings:
            assert settings['lang'] == 'text/javascript'
            break
    else:
        pytest.fail('gsub match was not found')


def test_has_parent_predicate_positive() -> None:
    """Test has-parent? predicate with matching parent."""
    content = 'Outer<div><p>Inner <span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((text) @text
         (#has-parent? @text "element"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'text' in captures
    nodes = captures['text']

    assert len(nodes) == 2
    assert nodes[0].text == b'Inner'
    assert nodes[1].text == b'Text'


def test_has_parent_predicate_negative() -> None:
    """Test has-parent? predicate with non-matching parent."""
    content = '<div><p><span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((text) @text
         (#has-parent? @text "nonexistent"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}


def test_has_ancestor_predicate_positive() -> None:
    """Test has-ancestor? predicate with matching ancestor."""
    content = 'A<div><p><span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((start_tag
          (tag_name) @tag)
         (#has-ancestor? @tag "element"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'tag' in captures
    nodes = captures['tag']

    assert len(nodes) == 3

    matches = {
        node.text
        for node in nodes
    }
    assert matches == {b'div', b'p', b'span'}


def test_has_ancestor_predicate_negative() -> None:
    """Test has-ancestor? predicate with non-matching ancestor."""
    content = '<div><p><span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((start_tag
          (tag_name) @tag)
         (#has-ancestor? @tag "nonexistent"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}


def test_not_has_parent_predicate_positive() -> None:
    """Test not-has-parent? predicate with non-matching parent."""
    content = '<div><p><span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((start_tag
          (tag_name) @tag)
         (#not-has-parent? @tag "nonexistent"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'tag' in captures
    nodes = captures['tag']

    assert len(nodes) == 3

    matches = {
        node.text
        for node in nodes
    }
    assert matches == {b'div', b'p', b'span'}


def test_not_has_parent_predicate_negative() -> None:
    """Test not-has-parent? predicate with matching parent."""
    content = '<div><p><span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((start_tag
          (tag_name) @tag)
         (#not-has-ancestor? @tag "element"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}


def test_not_has_ancestor_predicate_positive() -> None:
    """Test not-has-ancestor? predicate with non-matching ancestor."""
    content = '<div><p><span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((start_tag
          (tag_name) @tag)
         (#not-has-ancestor? @tag "nonexistent"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert 'tag' in captures
    nodes = captures['tag']

    assert len(nodes) == 3

    matches = {
        node.text
        for node in nodes
    }
    assert matches == {b'div', b'p', b'span'}


def test_not_has_ancestor_predicate_negative() -> None:
    """Test not-has-ancestor? predicate with matching ancestor."""
    content = '<div><p><span>Text</span></p></div>'
    content_bytes = content.encode()

    parser = get_parser('html')
    tree = parser.parse(content_bytes)

    ts_language = parser.language
    assert ts_language is not None

    queries = dedent("""
        ((start_tag
          (tag_name) @tag)
         (#not-has-ancestor? @tag "element"))
    """)
    query = tree_sitter.Query(ts_language, queries)
    predicate_handler = create_predicate_handler(query)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node, predicate_handler)

    assert captures == {}
