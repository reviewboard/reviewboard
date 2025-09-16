"""Tests for reviewboard.treesitter.highlight module.

Version Added:
    9.0
"""

from __future__ import annotations

from pathlib import Path

import pytest
import tree_sitter
from tree_sitter_language_pack import SupportedLanguage, get_parser

from reviewboard.treesitter.core import get_language, get_queries
from reviewboard.treesitter.highlight import (
    EVENT_POSITION,
    EVENT_TAG,
    NODE_NAME,
    NODE_START,
    NODE_END,
    _apply_events,
    _find_matching_highlight_tag,
    _get_events_by_line,
    _get_nodes_by_line,
    highlight,
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


def test_get_queries_with_python_highlights() -> None:
    """Test get_queries with Python highlights."""
    queries = get_queries('python', 'highlights.scm')
    assert queries is not None

    language = get_language('python')
    query = tree_sitter.Query(language, queries)

    # This may have to update when queries are updated from
    # nvim-treesitter.
    assert query.pattern_count == 83


def test_get_queries_with_python_injections() -> None:
    """Test get_queries with Python injections."""
    queries = get_queries('python', 'injections.scm')
    assert queries is not None

    language = get_language('python')
    query = tree_sitter.Query(language, queries)

    # This may have to update when queries are updated from
    # nvim-treesitter.
    assert query.pattern_count == 3


def test_get_queries_with_nonexistent_language() -> None:
    """Test get_queries with non-existent language."""
    queries = get_queries('nonexistent', 'highlights.scm')

    assert queries is None


def test_get_queries_with_nonexistent_file() -> None:
    """Test get_queries with non-existent query file."""
    queries = get_queries('python', 'nonexistent.scm')

    assert queries is None


@pytest.mark.parametrize(('capture_name', 'expected_tag'), [
    ('function', '<span class="ts-function">'),
    ('function.builtin', '<span class="ts-function-builtin">'),
    ('function.method.unknown', '<span class="ts-function">'),
    ('punctuation', None),
    ('unknown.class', None),
])
def test_find_matching_highlight_tag_exact_match(
    capture_name: str,
    expected_tag: str | None,
) -> None:
    """Test _find_matching_highlight_tag.

    Args:
        capture_name (str):
            The capture name from the Tree Sitter queries.

        expected_tag (str or None):
            The expected result.
    """
    result = _find_matching_highlight_tag(capture_name)
    assert result == expected_tag


def test_get_nodes_by_line_single_line() -> None:
    """Test _get_nodes_by_line with single line nodes."""
    captures = [
        ('function', 0, 4, 0, 12, b'function'),
        ('string', 0, 15, 0, 22, b'"hello"'),
    ]
    lines = ['def function("hello"):']

    result = list(_get_nodes_by_line(captures, lines))

    assert len(result) == 1
    nodes = result[0]
    assert len(nodes) == 2

    # Nodes should be sorted by start position.
    assert nodes[0][NODE_NAME] == 'function'
    assert nodes[0][NODE_START] == 4
    assert nodes[0][NODE_END] == 12

    assert nodes[1][NODE_NAME] == 'string'
    assert nodes[1][NODE_START] == 15
    assert nodes[1][NODE_END] == 22


def test_get_nodes_by_line_multi_line() -> None:
    """Test _get_nodes_by_line with multi-line nodes."""
    captures = [
        ('string', 0, 4, 2, 3, b'"""\\nMulti-line\\nstring\\n"""'),
    ]
    lines = [
        '    """',
        'Multi-line',
        'string',
        '"""',
    ]

    result = list(_get_nodes_by_line(captures, lines))

    assert len(result) == 4

    # First line: from start to end of line.
    nodes = result[0]
    assert len(nodes) == 1
    assert nodes[0][NODE_NAME] == 'string'
    assert nodes[0][NODE_START] == 4
    assert nodes[0][NODE_END] == len(lines[0])

    # Middle line: entire line.
    nodes = result[1]
    assert len(nodes) == 1
    assert nodes[0][NODE_NAME] == 'string'
    assert nodes[0][NODE_START] == 0
    assert nodes[0][NODE_END] == len(lines[1])

    # Last line of the multi-line node: from start to end column.
    nodes = result[2]
    assert len(nodes) == 1
    assert nodes[0][NODE_NAME] == 'string'
    assert nodes[0][NODE_START] == 0
    assert nodes[0][NODE_END] == 3

    # Line after the multi-line node: no nodes.
    nodes = result[3]
    assert len(nodes) == 0


def test_get_nodes_by_line_overlapping_nodes() -> None:
    """Test _get_nodes_by_line with overlapping nodes."""
    captures = [
        ('function', 0, 4, 0, 12, b'function'),
        ('function.call', 0, 4, 0, 12, b'function'),
        ('function.outer', 0, 4, 0, 14, b'function'),
    ]
    lines = ['def function():']

    result = list(_get_nodes_by_line(captures, lines))

    assert len(result) == 1
    nodes = result[0]
    assert len(nodes) == 3

    # Should be sorted by start position, then by length (longest first).
    assert nodes[0][0] == 'function.outer'
    assert nodes[1][0] == 'function'
    assert nodes[2][0] == 'function.call'


def test_get_events_by_line_single_node() -> None:
    """Test _get_events_by_line with single node."""
    nodes_by_line = [
        [('function', 4, 12)],
    ]

    result = list(_get_events_by_line(nodes_by_line))

    assert len(result) == 1
    events = result[0]
    assert len(events) == 2

    # Events should be sorted by position.
    assert events[0][EVENT_TAG] == '<span class="ts-function">'
    assert events[0][EVENT_POSITION] == 4

    assert events[1][EVENT_TAG] == '</span>'
    assert events[1][EVENT_POSITION] == 12


def test_get_events_by_line_multiple_nodes() -> None:
    """Test _get_events_by_line with multiple nodes."""
    nodes_by_line = [
        [
            ('function', 4, 12),
            ('string', 15, 22),
        ],
    ]

    result = list(_get_events_by_line(nodes_by_line))

    assert len(result) == 1
    events = result[0]
    assert len(events) == 4

    # Events should be sorted by position.
    assert events[0][EVENT_POSITION] == 4
    assert events[1][EVENT_POSITION] == 12
    assert events[2][EVENT_POSITION] == 15
    assert events[3][EVENT_POSITION] == 22


def test_get_events_by_line_ignored_nodes() -> None:
    """Test _get_events_by_line with ignored highlight classes."""
    nodes_by_line = [
        [
            ('function', 4, 12),
            ('punctuation', 12, 13),
        ],
    ]

    result = list(_get_events_by_line(nodes_by_line))

    assert len(result) == 1
    events = result[0]

    # Only function node should generate events, punctuation is ignored.
    assert len(events) == 2

    assert events[0][EVENT_TAG] == '<span class="ts-function">'
    assert events[1][EVENT_TAG] == '</span>'


def test_apply_events_no_events() -> None:
    """Test _apply_events with no events."""
    lines = ['def function():']
    events_by_line = [[]]

    result = _apply_events(lines, events_by_line)

    assert result == ['def function():']


def test_apply_events_with_highlighting() -> None:
    """Test _apply_events with highlighting events."""
    lines = ['def function():']
    events_by_line = [[
        ('<span class="ts-function">', 4),
        ('</span>', 12),
    ]]

    result = _apply_events(lines, events_by_line)

    expected = [
        'def <span class="ts-function">function</span>():'
    ]
    assert result == expected


def test_apply_events_with_html_escaping() -> None:
    """Test _apply_events with HTML character escaping."""
    lines = ['if x < 5 & y > 3:']
    events_by_line = [[]]

    result = _apply_events(lines, events_by_line)

    expected = ['if x &lt; 5 &amp; y &gt; 3:']
    assert result == expected


def test_apply_events_with_quotes() -> None:
    """Test _apply_events with quote escaping."""
    lines = ['print("It\'s a test")']
    events_by_line = [[]]

    result = _apply_events(lines, events_by_line)

    expected = ['print(&quot;It&#39;s a test&quot;)']
    assert result == expected


def test_apply_events_complex_case() -> None:
    """Test _apply_events with complex highlighting and escaping."""
    lines = ['print("Hello & <world>")']
    events_by_line = [[
        ('<span class="ts-function">', 0),
        ('</span>', 5),
        ('<span class="ts-string">', 6),
        ('</span>', 23),
    ]]

    result = _apply_events(lines, events_by_line)

    expected = [
        '<span class="ts-function">print</span>'
        '(<span class="ts-string">'
        '&quot;Hello &amp; &lt;world&gt;&quot;'
        '</span>)'
    ]
    assert result == expected


def test_apply_events_multiple_lines() -> None:
    """Test _apply_events with multiple lines."""
    lines = [
        'def function():',
        '    return "value"',
        'print(42)'
    ]
    events_by_line = [
        [
            ('<span class="ts-function">', 4),
            ('</span>', 12),
        ],
        [
            ('<span class="ts-string">', 11),
            ('</span>', 18),
        ],
        [
            ('<span class="ts-function">', 0),
            ('</span>', 5),
            ('<span class="ts-number">', 6),
            ('</span>', 8),
        ]
    ]

    result = _apply_events(lines, events_by_line)

    expected = [
        (
            'def <span class="ts-function">function</span>():'
        ),
        (
            '    return <span class="ts-string">&quot;value&quot;'
            '</span>'
        ),
        (
            '<span class="ts-function">print</span>('
            '<span class="ts-number">42</span>)'
        ),
    ]
    assert result == expected


@pytest.mark.parametrize(('filename', 'language'), [
    ('sample.py', 'python'),
    ('sample.js', 'javascript'),
    ('sample.cpp', 'cpp'),
    ('sample.html', 'html'),
    ('sample.md', 'markdown'),
    ('sample.c', 'c'),
    ('sample.go', 'go'),
    ('sample.java', 'java'),
    ('sample.json', 'json'),
    ('sample.rb', 'ruby'),
    ('sample.rs', 'rust'),
    ('sample.sh', 'bash'),
    ('sample.ts', 'typescript'),
    ('sample.yaml', 'yaml'),
])
def test_highlight_language_files(
    filename: str,
    language: SupportedLanguage,
) -> None:
    """Test highlighting for various language sample files.

    Args:
        filename (str):
            The sample file name (e.g., 'sample.py').

        language (reviewboard.treesitter.language.SupportedLanguage):
            The language name for TreeSitter (e.g., 'python').
    """
    testdata_dir = Path(__file__).parent / 'testdata'
    test_file = testdata_dir / filename
    expected_file = testdata_dir / f'{filename}.expected'

    with test_file.open(encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    content_bytes = content.encode()

    parser = get_parser(language)
    tree = parser.parse(content_bytes)

    result = highlight(content_bytes, lines, tree, language)
    assert result is not None

    with expected_file.open(encoding='utf-8') as f:
        expected = f.read().splitlines()

    assert result == expected


def test_highlight_unsupported_language() -> None:
    """Test highlight with unsupported language."""
    lines = ['test content']
    parser = get_parser('python')
    content_bytes = b'test content'
    tree = parser.parse(content_bytes)

    # Use a language that's not in SUPPORTED_LANGUAGES.
    result = highlight(
        content_bytes,
        lines,
        tree,
        'unsupported',  # type:ignore
    )

    assert result is None


def test_highlight_empty_file() -> None:
    """Test highlight with empty file."""
    lines = []
    parser = get_parser('python')
    content_bytes = b''
    tree = parser.parse(content_bytes)

    result = highlight(content_bytes, lines, tree, 'python')
    assert result is None


def test_highlight_single_line() -> None:
    """Test highlight with single line."""
    lines = ['def hello():']
    parser = get_parser('python')
    content_bytes = lines[0].encode()
    tree = parser.parse(content_bytes)

    result = highlight(content_bytes, lines, tree, 'python')

    # This may need to be updated when we update treesitter parsers or queries.
    assert result == [
        '<span class="ts-keyword">def</span> <span class="ts-function">'
        '<span class="ts-variable">hello</span></span>():'
    ]


def test_highlight_with_injections() -> None:
    """Test highlight with language injections."""
    # HTML with JavaScript injection.
    html_content = (
        '<script>\n'
        'function test() {\n'
        '    console.log("Hello");\n'
        '}\n'
        '</script>'
    )

    lines = html_content.splitlines()
    parser = get_parser('html')
    content_bytes = html_content.encode()
    tree = parser.parse(content_bytes)

    result = highlight(content_bytes, lines, tree, 'html')
    assert result is not None

    assert len(result) == len(lines)

    # This may need to be updated when we update treesitter parsers or queries.
    assert result == [
        (
            '&lt;<span class="ts-tag">script</span>&gt;'
        ),
        (
            '<span class="ts-keyword">function</span> '
            '<span class="ts-function"><span class="ts-variable">test'
            '</span></span>() {'
        ),
        (
            '    <span class="ts-variable-builtin">'
            '<span class="ts-variable">console</span></span>.'
            '<span class="ts-function-method-call">'
            '<span class="ts-variable">log</span></span>('
            '<span class="ts-string">&quot;Hello&quot;</span>);'
        ),
        (
            '}'
        ),
        (
            '&lt;/<span class="ts-tag">script</span>&gt;'
        ),
    ]


def test_highlight_with_multibyte_unicode_character() -> None:
    """Test highlight a multibyte unicode character."""
    content = '/* Say hello; newline\u2067 /*/ return 0 ;'

    lines = [content]
    parser = get_parser('c')
    content_bytes = content.encode('utf-8')
    tree = parser.parse(content_bytes)

    result = highlight(content_bytes, lines, tree, 'c')
    assert result is not None

    assert len(result) == 1
    assert result[0] == (
        '<span class="ts-comment">/* Say hello; newline\u2067 /*/</span> '
        '<span class="ts-keyword">return</span> '
        '<span class="ts-number">0</span> ;'
    )
