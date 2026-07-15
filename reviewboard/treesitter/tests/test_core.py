"""Tests for reviewboard.treesitter.core module.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.treesitter.core import get_language, get_parser


def test_get_language_is_cached() -> None:
    """Testing that get_language returns a shared Language instance"""
    assert get_language('python') is get_language('python')


def test_get_parser_returns_fresh_instances() -> None:
    """Testing that get_parser returns a new Parser for each call"""
    # Parser objects are stateful and not thread-safe. Sharing one
    # instance between threads (or between callers that mutate
    # included_ranges) can corrupt parse results.
    assert get_parser('python') is not get_parser('python')


def test_get_parser_state_does_not_leak() -> None:
    """Testing that mutations to one parser do not affect later parsers"""
    content = b'x = 1\ny = 2\n'

    parser = get_parser('python')
    first_stmt = parser.parse(content).root_node.children[0]
    parser.included_ranges = [first_stmt.range]

    # A new parser must not inherit the restricted ranges.
    tree = get_parser('python').parse(content)

    assert tree.root_node.end_byte == len(content)
