"""Tests for reviewboard.treesitter language detection functionality.

Version Added:
    8.0
"""

from __future__ import annotations

import pytest

from reviewboard.treesitter.language import (
    get_language_name_for_file,
    get_language_name_for_mimetype,
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


@pytest.mark.parametrize(('filename', 'expected_lang'), [
    ('script.py', 'python'),
    ('script.js', 'javascript'),
    ('main.cpp', 'cpp'),
    ('main.hpp', 'cpp'),
    ('main.c', 'c'),
    ('header.h', 'c'),
    ('main.rs', 'rust'),
    ('main.go', 'go'),
    ('component.ts', 'typescript'),
    ('component.tsx', 'tsx'),
    ('package.json', 'json'),
    ('config.yaml', 'yaml'),
    ('config.xml', 'xml'),
    ('index.html', 'html'),
    ('styles.css', 'css'),
    ('styles.scss', 'scss'),
    ('test.scm', 'scheme'),
    ('README.md', 'markdown'),
    ('setup.sh', 'bash'),
])
def test_get_language_name_for_file_extensions(
    filename: str,
    expected_lang: str,
) -> None:
    """Test get_language_name_for_file with various file extensions.

    Args:
        filename (str):
            The filename to test.

        expected_lang (str):
            The expected language result.
    """
    result = get_language_name_for_file(filename)
    assert result == expected_lang


@pytest.mark.parametrize(('filename', 'expected_lang'), [
    ('Makefile', 'make'),
    ('Dockerfile', 'dockerfile'),
    ('CMakeLists.txt', 'cmake'),
    ('requirements.txt', 'requirements'),
    ('.gitignore', 'gitignore'),
    ('.bashrc', 'bash'),
    ('go.mod', 'gomod'),
])
def test_get_language_name_for_file_special_names(
    filename: str,
    expected_lang: str,
) -> None:
    """Test get_language_name_for_file with special filenames.

    Args:
        filename (str):
            The filename to test.

        expected_lang (str):
            The expected language result.
    """
    result = get_language_name_for_file(filename)
    assert result == expected_lang


@pytest.mark.parametrize(('filename', 'expected_lang'), [
    ('file.unknown', None),  # unknown extension
    ('filename', None),  # no extension
    ('', None),  # empty filename
    ('file.config.json', 'json'),  # multiple extensions
    ('path/to/my-file_v1.2.py', 'python'),  # complex filename
    ('file.PY', None),  # case sensitivity
])
def test_get_language_name_for_file_edge_cases(
    filename: str,
    expected_lang: str | None,
) -> None:
    """Test get_language_name_for_file with edge cases.

    Args:
        filename (str):
            The filename to test.

        expected_lang (str):
            The expected language result.
    """
    result = get_language_name_for_file(filename)
    assert result == expected_lang


@pytest.mark.parametrize(('filename', 'expected_lang'), [
    ('header.h', 'c'),      # First in ['c', 'cpp', 'objc']
    ('file.m', 'matlab'),   # First in ['matlab', 'objc']
])
def test_get_language_name_for_file_ambiguous_extensions(
    filename: str,
    expected_lang: str,
) -> None:
    """Test get_language_name_for_file with ambiguous extensions.

    Args:
        filename (str):
            The filename to test.

        expected_lang (str):
            The expected language result.
    """
    result = get_language_name_for_file(filename)
    assert result == expected_lang


@pytest.mark.parametrize(('filename', 'mimetype', 'expected_lang'), [
    # (filename, mimetype, expected_lang)
    ('header.h', 'text/x-c', 'c'),
    ('header.h', 'text/x-c++hdr', 'cpp'),
    ('header.h', 'text/x-objective-c', 'objc'),
    ('script.js', 'text/javascript', 'javascript'),
    ('script.js', 'text/x-typescript', 'typescript'),
    ('script.js', 'text/x-tsx', 'tsx'),
    ('data.csv', 'text/csv', 'csv'),
    ('data.csv', 'text/tab-separated-values', 'tsv'),
    ('config.scm', 'text/x-scheme', 'scheme'),
])
def test_get_language_name_for_file_with_mimetype(
    filename: str,
    mimetype: str,
    expected_lang: str,
) -> None:
    """Test get_language_name_for_file with MIME type disambiguation.

    Args:
        filename (str):
            The filename to test.

        mimetype (str):
            The mimetype to test.

        expected_lang (str):
            The expected language result.
    """
    result = get_language_name_for_file(filename, mimetype)
    assert result == expected_lang


@pytest.mark.parametrize(('filename', 'mimetype', 'expected_lang'), [
    # Files with unknown extensions but recognizable MIME types
    ('unknown.xyz', 'text/javascript', 'javascript'),
    ('mystery.abc', 'text/x-c', 'c'),
    ('test.foo', 'text/csv', 'csv'),
])
def test_get_language_name_for_file_mimetype_fallback(
    filename: str,
    mimetype: str,
    expected_lang: str,
) -> None:
    """Test get_language_name_for_file using MIME type as fallback.

    Args:
        filename (str):
            The filename to test.

        mimetype (str):
            The mimetype to test.

        expected_lang (str):
            The expected language result.
    """
    result = get_language_name_for_file(filename, mimetype)
    assert result == expected_lang


@pytest.mark.parametrize(('mimetype', 'expected_lang'), [
    ('text/javascript', 'javascript'),
    ('application/javascript', 'javascript'),
    ('text/x-c', 'c'),
    ('text/x-c++', 'cpp'),
    ('text/x-objective-c', 'objc'),
    ('text/csv', 'csv'),
    ('text/tab-separated-values', 'tsv'),
    ('text/x-scheme', 'scheme'),
    ('text/x-typescript', 'typescript'),
    ('text/x-tsx', 'tsx'),
    ('unknown/type', None),

    # Test x- prefix stripping fallback
    ('foo/x-java', 'java'),
    ('application/x-rust', 'rust'),
])
def test_get_language_name_for_mimetype(
    mimetype: str,
    expected_lang: str | None,
) -> None:
    """Test get_language_name_for_mimetype function.

    Args:
        mimetype (str):
            The mimetype to test.

        expected_lang (str):
            The expected language result.
    """
    result = get_language_name_for_mimetype(mimetype)
    assert result == expected_lang
