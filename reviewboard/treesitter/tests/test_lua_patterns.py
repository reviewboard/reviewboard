"""Unit tests for reviewboard.treesitter.lua_patterns.

Version Added:
    8.0
"""

from __future__ import annotations

import re

import pytest

from reviewboard.treesitter.lua_patterns import (
    _translate_lua_char_class,
    lua_pattern_to_python,
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


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('%a', '[A-Za-z]'),
    ('%d', r'\d'),
    ('%s', r'\s'),
    ('%w', r'\w'),
    ('%l', '[a-z]'),
    ('%u', '[A-Z]'),
    ('%x', '[A-Fa-f0-9]'),
    ('%c', r'[\x00-\x1F\x7F]'),
    ('%p', r'[!"#$%&\'()*+,\-./:;<=>?@[\\\]^_`{|}~]'),
    ('%z', r'\x00]'),
    ('%A', '[^A-Za-z]'),
    ('%D', r'\D'),
    ('%S', r'\S'),
    ('%W', r'\W'),
    ('%L', '[^a-z]'),
    ('%U', '[^A-Z]'),
    ('%X', '[^A-Fa-f0-9]'),
    ('%C', r'[^\x00-\x1F\x7F]'),
    ('%P', r'[^!"#$%&\'()*+,\-./:;<=>?@[\\\]^_`{|}~]'),
    ('%Z', r'[^\x00]'),
    ('%%', '%'),
])
def test_lua_to_python_classes_basic(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test basic Lua character class mappings.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('^test', '^test'),
    ('test$', 'test$'),
    ('test.*', '(?s)test.*'),
    ('test.+', '(?s)test.+'),
    ('test.?', '(?s)test.?'),
    ('^test$', '^test$'),
    ('^test.*end$', '(?s)^test.*end$'),
])
def test_anchors_and_quantifiers(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test anchors and quantifiers pass through.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('%.', r'\.'),
    ('%^', r'\^'),
    ('%$', r'\$'),
    ('%*', r'\*'),
    ('%+', r'\+'),
    ('%?', r'\?'),
    ('%{', r'\{'),
    ('%}', r'\}'),
    ('%[', r'\['),
    ('%]', r'\]'),
    ('%\\', r'\\'),
    ('%|', r'\|'),
    ('%(', r'\('),
    ('%)', r'\)'),
])
def test_escaped_special_chars(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test escaping of special regex characters.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('abc', 'abc'),
    ('test123', 'test123'),
    ('hello_world', 'hello_world'),
    ('file.txt', '(?s)file.txt'),
    ('test-file', 'test-file'),
    ('test@example.com', '(?s)test@example.com'),
])
def test_literal_characters(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test literal character handling.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('test{', 'test\\{'),
    ('test}', 'test\\}'),
    ('test]', 'test\\]'),
    ('test\\', 'test\\\\'),
    ('test|', 'test\\|'),
    ('test(', 'test('),
    ('test)', 'test)'),
    ('{test}', '\\{test\\}'),
    ('(test)', '(test)'),
])
def test_regex_special_chars_escaping(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test that regex special chars are properly escaped.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('[abc]', '[abc]'),
    ('[a-z]', '[a-z]'),
    ('[A-Z]', '[A-Z]'),
    ('[0-9]', '[0-9]'),
    ('[a-zA-Z]', '[a-zA-Z]'),
    ('[a-zA-Z0-9]', '[a-zA-Z0-9]'),
    ('[^abc]', '[^abc]'),
    ('[^a-z]', '[^a-z]'),
])
def test_character_classes(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test character class handling.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('[%d]', '[\\d]'),
    ('[%s]', '[\\s]'),
    ('[%w]', '[\\w]'),
    ('[%a]', '[A-Za-z]'),
    ('[%l]', '[a-z]'),
    ('[%u]', '[A-Z]'),
    ('[%x]', '[A-Fa-f0-9]'),
    ('[%D]', '[\\D]'),
    ('[%S]', '[\\S]'),
    ('[%W]', '[\\W]'),
    ('[%A]', '[^A-Za-z]'),
    ('[%L]', '[^a-z]'),
    ('[%U]', '[^A-Z]'),
    ('[%X]', '[^A-Fa-f0-9]'),
    ('[%d%s]', '[\\d\\s]'),
    ('[a-z%d]', '[a-z\\d]'),
    ('[%w_]', '[\\w_]'),
])
def test_character_classes_with_lua_escapes(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test character classes containing Lua escapes.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('[\\]]', '[\\\\]\\]'),
    ('[\\\\]', '[\\\\\\\\]'),
    ('[a\\]b]', '[a\\\\]b\\]'),
    ('[\\\\]]', '[\\\\\\\\]\\]'),
])
def test_character_classes_with_escapes(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test character classes with escaped characters.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    ('^[A-Z]%w*$', '^[A-Z]\\w*$'),
    ('^%d+$', '^\\d+$'),
    ('^%d+%.%d+$', '^\\d+\\.\\d+$'),
    ('^[A-Z][A-Z%d_]*$', '^[A-Z][A-Z\\d_]*$'),
    ('^[_]*[A-Z][a-zA-Z0-9_]*$', '^[_]*[A-Z][a-zA-Z0-9_]*$'),
    ('^on[a-z]+$', '^on[a-z]+$'),
    ('^#!/', '^#!/'),
    ('^///$', '^///$'),
    ('^///[^/]', '^///[^/]'),

    # * is literal inside []
    ('^/[*][*][^*].*[*]/$', '(?s)^/[*][*][^*].*[*]/$'),
])
def test_complex_patterns(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test complex patterns combining multiple features.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    # From sql/highlights.scm
    ('^%d+$', '^\\d+$'),
    ('^[-]?%d*%.%d*$', '^[-]?\\d*\\.\\d*$'),
    ('^[-]?%d*\\.%d*$', '^[-]?\\d*\\.\\d*$'),

    # From zig/highlights.scm
    ('^[A-Z_][a-zA-Z0-9_]*', '^[A-Z_][a-zA-Z0-9_]*'),
    ('^[A-Z][A-Z_0-9]+$', '^[A-Z][A-Z_0-9]+$'),
    ('^//!', '^//!'),

    # From ruby/highlights.scm
    ('^[A-Z0-9_]+$', '^[A-Z0-9_]+$'),
    ('^#!/', '^#!/'),

    # From glsl/highlights.scm
    ('^[A-Z][A-Z0-9_]+$', '^[A-Z][A-Z0-9_]+$'),
    ('^__builtin_', '^__builtin_'),
    ('^/[*][*][^*].*[*]/$', '(?s)^/[*][*][^*].*[*]/$'),
    ('^gl_', '^gl_'),

    # From rust/highlights.scm
    ('^[A-Z]', '^[A-Z]'),
    ('^[A-Z][A-Z%d_]*$', '^[A-Z][A-Z\\d_]*$'),

    # From vue/injections.scm
    ('%slang%s*=', '\\slang\\s*='),
    ('%stype%s*=', '\\stype\\s*='),
    ('%${', '\\$\\{'),
    ('^on[a-z]+$', '^on[a-z]+$'),

    # From bash/highlights.scm
    ('^[0-9]+$', '^[0-9]+$'),
    ('^[A-Z][A-Z_0-9]*$', '^[A-Z][A-Z_0-9]*$'),

    # From vim/highlights.scm
    ('^[%d]+(%.[%d]+)?$', '^[\\d]+(\\.[\\d]+)?$'),

    # From javascript/highlights.scm
    ('^_*[A-Z][A-Z%d_]*$', '^_*[A-Z][A-Z\\d_]*$'),
    ('^[a-zA-Z][a-zA-Z0-9]*$', '^[a-zA-Z][a-zA-Z0-9]*$'),
    ('^`#graphql', '^`#graphql'),

    # From css/highlights.scm
    ('^[-][-]', '^[-][-]'),

    # From fish/highlights.scm
    ('^[-]', '^[-]'),

    # From lua/highlights.scm
    ('^[-][-][-]', '^[-][-][-]'),

    # From dart/highlights.scm
    ('^_?[%l]', '^_?[a-z]'),
    ('^[%u%l]', '^[A-Za-z]'),
    ('^_?[%u].*[%l]', '(?s)^_?[A-Z].*[a-z]'),

    # From lua/injections.scm
    ('^%s*;+%s?query', '^\\s*;+\\s?query'),
    ('^[-][%s]*[@|]', '^[-][\\s]*[@|]'),
    ('[-][-][-][%s]*@', '[-][-][-][\\s]*@'),

    # From c/injections.scm
    (r'/[*\/][!*\/]<?[^a-zA-Z]', r'/[*\\/][!*\\/]<?[^a-zA-Z]'),

    # From perl/injections.scm
    ('e.*e', '(?s)e.*e'),

    # From squirrel/injections.scm
    ('^@"<html', '^@"<html'),
    ('@"<!DOCTYPE html>', '@"<!DOCTYPE html>'),

    # From solidity/injections.scm
    ('^///[^/]', '^///[^/]'),
    ('^///$', '^///$'),
])
def test_real_patterns_from_queries(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test real patterns found in query files.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize('lua_pattern', [
    # Unsupported non-greedy quantifier
    'test*-',
    'test+-',
    'test?-',

    # Unterminated character class
    '[abc',
    '[',
    '[abc[def',

    # Unsupported balanced-parentheses operator
    'test%b()',
    'test%b[]',
    'test%b<>',
    'test%b%{%}',
])
def test_error_cases(
    lua_pattern: str,
) -> None:
    """Test error cases that should return None.

    Args:
        lua_pattern (str):
            The Lua pattern to test.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result is None


@pytest.mark.parametrize(('lua_pattern', 'expected'), [
    # Empty pattern
    ('', ''),

    # Pattern with only anchors
    ('^$', '^$'),

    # Pattern with only quantifiers (should work)
    ('.*', '(?s).*'),
    ('.+', '(?s).+'),
    ('.?', '(?s).?'),

    # Patterns with escaped percent
    ('%%', '%'),
    ('%%%%', '%%'),
    ('test%%end', 'test%end'),

    # Character class at end of pattern
    ('[abc]', '[abc]'),
    ('test[abc]', 'test[abc]'),

    # Multiple character classes
    ('[a-z][0-9]', '[a-z][0-9]'),
    ('[%d][%s]', '[\\d][\\s]'),
])
def test_edge_cases(
    lua_pattern: str,
    expected: str,
) -> None:
    """Test edge cases.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        expected (str):
            The expected value for the converted regex.
    """
    result = lua_pattern_to_python(lua_pattern)
    assert result == expected


@pytest.mark.parametrize(('lua_pattern', 'test_string', 'should_match'), [
    # Test basic character classes
    ('%d+', '123', True),
    ('%d+', 'abc', False),
    ('%s+', '   ', True),
    ('%s+', 'abc', False),
    ('%w+', 'abc123', True),
    ('%w+', '@#$', False),

    # Test complement character classes
    ('%D+', 'abc', True),
    ('%D+', '123', False),
    ('%S+', 'abc', True),
    ('%S+', '   ', False),
    ('%W+', '@#$', True),
    ('%W+', 'abc123', False),
    ('%A+', '123!', True),
    ('%A+', 'abc', False),
    ('%L+', 'ABC123', True),
    ('%L+', 'abc', False),
    ('%U+', 'abc123', True),
    ('%U+', 'ABC', False),

    # Test anchors
    ('^%d+$', '123', True),
    ('^%d+$', 'abc123', False),
    ('^%d+$', '123abc', False),

    # Test character classes
    ('[A-Z]+', 'ABC', True),
    ('[A-Z]+', 'abc', False),
    ('[%d%s]+', '123 456', True),
    ('[%d%s]+', 'abc', False),

    # Test complex patterns
    ('^[A-Z][A-Z%d_]*$', 'ABC_123', True),
    ('^[A-Z][A-Z%d_]*$', 'abc_123', False),
    ('^[A-Z][A-Z%d_]*$', '123ABC', False),

    # From SQL highlighting - number patterns
    ('^%d+$', '42', True),
    ('^%d+$', 'abc', False),
    ('^%d+$', '12.34', False),  # Should not match float
    ('^[-]?%d*%.%d*$', '3.14', True),
    ('^[-]?%d*%.%d*$', '-2.5', True),
    ('^[-]?%d*%.%d*$', '.5', True),
    ('^[-]?%d*%.%d*$', '10.', True),
    ('^[-]?%d*%.%d*$', '123', False),  # Should not match integer

    # From Zig/Rust - identifier patterns (uppercase constants)
    ('^[A-Z][A-Z_0-9]+$', 'MAX_SIZE', True),
    ('^[A-Z][A-Z_0-9]+$', 'VERSION_1_0', True),
    ('^[A-Z][A-Z_0-9]+$', 'DEBUG', True),
    ('^[A-Z][A-Z_0-9]+$', 'maxSize', False),  # camelCase
    ('^[A-Z][A-Z_0-9]+$', 'max_size', False),  # lowercase
    ('^[A-Z][A-Z_0-9]+$', '123_ABC', False),  # starts with number

    # From various languages - type patterns
    ('^[A-Z]', 'MyClass', True),
    ('^[A-Z]', 'String', True),
    ('^[A-Z]', 'myVar', False),
    ('^[A-Z]', 'function', False),

    # From Vue/Svelte/Astro - attribute patterns
    ('^on[a-z]+$', 'onclick', True),
    ('^on[a-z]+$', 'onsubmit', True),
    ('^on[a-z]+$', 'onkeypress', True),
    ('^on[a-z]+$', 'OnClick', False),  # Wrong case
    ('^on[a-z]+$', 'onclick123', False),  # Contains numbers
    ('^on[a-z]+$', 'on', False),  # Too short

    # From comment highlighting - shebang patterns
    ('^#!/', '#!/bin/bash', True),
    ('^#!/', '#!/usr/bin/env python', True),
    ('^#!/', '#! /bin/sh', False),  # Space after #!
    ('^#!/', '# !/bin/bash', False),  # Space in wrong place

    # From comment highlighting - documentation patterns
    ('^///$', '///', True),
    ('^///$', '/// Some comment', False),
    ('^///$', '//', False),
    ('^///[^/]', '/// This is a doc comment', True),
    ('^///[^/]', '/// ', True),  # Space counts as non-/
    ('^///[^/]', '///', False),  # Would match empty after ///
    ('^///[^/]', '////', False),  # Fourth / should not match

    # From JavaScript/TypeScript - constant patterns
    ('^_*[A-Z][A-Z%d_]*$', 'CONSTANT', True),
    ('^_*[A-Z][A-Z%d_]*$', '_PRIVATE_CONST', True),
    ('^_*[A-Z][A-Z%d_]*$', '__DUNDER_CONST', True),
    ('^_*[A-Z][A-Z%d_]*$', 'API_VERSION_2', True),
    ('^_*[A-Z][A-Z%d_]*$', 'camelCase', False),
    ('^_*[A-Z][A-Z%d_]*$', '_mixedCase', False),

    # From Dart - identifier patterns with lowercase/uppercase
    ('^_?[%l]', 'method', True),
    ('^_?[%l]', '_private', True),
    ('^_?[%l]', 'Method', False),  # Uppercase
    ('^_?[%l]', '123', False),  # Number
    ('^[%u%l]', 'MyClass', True),
    ('^[%u%l]', 'myVariable', True),
    ('^[%u%l]', '123abc', False),  # Starts with number
    ('^[%u%l]', '_private', False),  # Starts with underscore

    # From Bash - variable patterns
    ('^[A-Z][A-Z_0-9]*$', 'PATH', True),
    ('^[A-Z][A-Z_0-9]*$', 'USER_HOME', True),
    ('^[A-Z][A-Z_0-9]*$', 'DEBUG_LEVEL_2', True),
    ('^[A-Z][A-Z_0-9]*$', 'path', False),  # lowercase
    ('^[A-Z][A-Z_0-9]*$', '2PATH', False),  # starts with number

    # From CSS - variable patterns (custom properties)
    ('^[-][-]', '--main-color', True),
    ('^[-][-]', '--font-size', True),
    ('^[-][-]', '-single-dash', False),
    ('^[-][-]', 'no-dashes', False),

    # From Fish shell - option patterns
    ('^[-]', '--help', True),
    ('^[-]', '-v', True),
    ('^[-]', 'help', False),
    ('^[-]', '+option', False),

    # From GLSL - builtin patterns
    ('^gl_', 'gl_Position', True),
    ('^gl_', 'gl_FragColor', True),
    ('^gl_', 'myVariable', False),
    ('^gl_', 'GL_POSITION', False),  # Wrong case
    ('^__builtin_', '__builtin_sin', True),
    ('^__builtin_', '__builtin_cos', True),
    ('^__builtin_', 'builtin_sin', False),  # Missing prefix

    # From Vim - number patterns
    ('^[%d]+(%.[%d]+)?$', '42.5', True),
    ('^[%d]+(%.[%d]+)?$', '123.789', True),
    ('^[%d]+(%.[%d]+)?$', '42', True),

    # From Lua documentation patterns
    ('^[-][-][-]', '--- This is a doc comment', True),
    ('^[-][-][-]', '---', True),
    ('^[-][-][-]', '-- Regular comment', False),
    ('^[-][-][-]', '---- Also matches since pattern has no end anchor',
     True),

    # From injection patterns - template literals
    ('%${', 'Hello ${name}!', True),
    ('%${', 'const x = ${value}', True),
    ('%${', 'No interpolation here', False),
    ('%${', '${', True),  # Just the pattern

    # From query language patterns
    ('^%s*;+%s?query', '  ;;query', True),
    ('^%s*;+%s?query', ';query', True),
    ('^%s*;+%s?query', ';;;; query', True),
    ('^%s*;+%s?query', 'query', False),  # Missing semicolons
    ('^%s*;+%s?query', '  query', False),  # Missing semicolons

    # From language detection patterns
    ('^@"<html', '@"<html>', True),
    ('^@"<html', '@"<html lang="en">', True),
    ('^@"<html', '"<html>', False),  # Missing @
    ('^@"<html', '@"<XML>', False),  # Wrong tag
])
def test_functionality_with_regex(
    lua_pattern: str,
    test_string: str,
    should_match: bool,
) -> None:
    """Test that converted patterns work correctly with re module.

    Args:
        lua_pattern (str):
            The Lua pattern to test.

        test_string (str):
            The test string to match against.

        should_match (bool):
            Whether the pattern should match the test string.
    """
    python_pattern = lua_pattern_to_python(lua_pattern)
    assert python_pattern is not None

    match = re.search(python_pattern, test_string)

    if should_match:
        assert match is not None, \
            f'Pattern {python_pattern} should match "{test_string}"'
    else:
        assert match is None, \
            f'Pattern {python_pattern} should not match "{test_string}"'


@pytest.mark.parametrize(('contents', 'expected'), [
    ('abc', 'abc'),
    ('a-z', 'a-z'),
    ('A-Z', 'A-Z'),
    ('0-9', '0-9'),
    ('a-zA-Z', 'a-zA-Z'),
    ('a-zA-Z0-9', 'a-zA-Z0-9'),
    ('^abc', '^abc'),
    ('^a-z', '^a-z'),
])
def test_basic_character_class(
    contents: str,
    expected: str,
) -> None:
    """Test basic character class translation.

    Args:
        contents (str):
            The character class contents to test.

        expected (str):
            The expected value for the translated character class.
    """
    result = _translate_lua_char_class(contents, f'[{contents}]')
    assert result == expected


@pytest.mark.parametrize(('contents', 'expected'), [
    ('%d', '\\d'),
    ('%s', '\\s'),
    ('%w', '\\w'),
    ('%a', 'A-Za-z'),
    ('%l', 'a-z'),
    ('%u', 'A-Z'),
    ('%x', 'A-Fa-f0-9'),
    ('%c', '\\x00-\\x1F\\x7F'),
    ('%p', '!"#$%&\\\'()*+,\\-./:;<=>?@[\\\\\\]^_`{|}~'),
    ('%D', '\\D'),
    ('%S', '\\S'),
    ('%W', '\\W'),
    ('%A', '^A-Za-z'),
    ('%L', '^a-z'),
    ('%U', '^A-Z'),
    ('%X', '^A-Fa-f0-9'),
    ('%C', '^\\x00-\\x1F\\x7F'),
    ('%P', '^!"#$%&\\\'()*+,\\-./:;<=>?@[\\\\\\]^_`{|}~'),
    ('%Z', '^\\x00'),
    ('%%', '%'),
    ('%d%s', '\\d\\s'),
    ('a%db', 'a\\db'),
    ('%w_', '\\w_'),
])
def test_lua_escapes_in_class(
    contents: str,
    expected: str,
) -> None:
    """Test Lua escapes within character classes.

    Args:
        contents (str):
            The character class contents to test.

        expected (str):
            The expected value for the translated character class.
    """
    result = _translate_lua_char_class(contents, f'[{contents}]')
    assert result == expected


@pytest.mark.parametrize(('contents', 'expected'), [
    ('\\]', '\\\\\\]'),
    ('\\\\', '\\\\\\\\'),
    ('a\\]b', 'a\\\\\\]b'),
    ('\\\\]', '\\\\\\\\\\]'),
    ('abc\\]def', 'abc\\\\\\]def'),
])
def test_escaped_characters_in_class(
    contents: str,
    expected: str,
) -> None:
    """Test escaped characters within character classes.

    Args:
        contents (str):
            The character class contents to test.

        expected (str):
            The expected value for the translated character class.
    """
    result = _translate_lua_char_class(contents, f'[{contents}]')
    assert result == expected


@pytest.mark.parametrize(('contents', 'expected'), [
    ('A-Z%d_', 'A-Z\\d_'),
    ('a-z%s0-9', 'a-z\\s0-9'),
    ('^%w_', '^\\w_'),
    ('a%lb%uc', 'aa-zbA-Zc'),
    ('%x-', 'A-Fa-f0-9-'),
])
def test_mixed_content(
    contents: str,
    expected: str,
) -> None:
    """Test mixed content in character classes.

    Args:
        contents (str):
            The character class contents to test.

        expected (str):
            The expected value for the translated character class.
    """
    result = _translate_lua_char_class(contents, f'[{contents}]')
    assert result == expected


@pytest.mark.parametrize(('contents', 'expected'), [
    # Empty class
    ('', ''),

    # Just escapes
    ('%%', '%'),
    ('%%%%', '%%'),

    # Just character ranges
    ('a-z', 'a-z'),
    ('A-Z', 'A-Z'),
    ('0-9', '0-9'),

    # Complex combinations
    ('A-Za-z0-9_%d%s', 'A-Za-z0-9_\\d\\s'),
])
def test_edge_cases_translate_lua_char_class(
    contents: str,
    expected: str,
) -> None:
    """Test edge cases in character class translation.

    Args:
        contents (str):
            The character class contents to test.

        expected (str):
            The expected value for the translated character class.
    """
    result = _translate_lua_char_class(contents, f'[{contents}]')
    assert result == expected
