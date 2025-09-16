#!/usr/bin/env python3
"""Generate expected highlight output files for testing.

Version Added:
    9.0
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tree_sitter_language_pack import get_parser

from reviewboard.treesitter.highlight import highlight

if TYPE_CHECKING:
    from collections.abc import Sequence

    from reviewboard.treesitter.language import SupportedLanguage


def generate_expected_output(
    input_file: Path,
    language: SupportedLanguage,
) -> None:
    """Generate expected highlight output for a sample file.

    Args:
        input_file (pathlib.Path):
            The input for the highlighting test.

        language (reviewboard.treesitter.language.SupportedLanguage):
            The language name to use for highlighting.
    """
    with open(input_file, encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    content_bytes = content.encode()

    parser = get_parser(language)
    tree = parser.parse(content_bytes)

    result = highlight(content_bytes, lines, tree, language)

    if result is None:
        print(f'No highlighting result for {input_file}')
        return

    output_file = input_file.with_suffix(f'{input_file.suffix}.expected')

    with open(output_file, 'w', encoding='utf-8') as f:
        for line in result:
            f.write(line + '\n')

    print(f'Generated expected output: {output_file}')


def main() -> None:
    """Generate all expected output files."""
    testdata_dir = (
        Path(__file__).parents[3] / 'reviewboard' / 'treesitter' /
        'tests' / 'testdata'
    ).resolve()

    files_and_languages: Sequence[tuple[str, SupportedLanguage]] = [
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
    ]

    for filename, language in files_and_languages:
        input_file = testdata_dir / filename

        if input_file.exists():
            generate_expected_output(input_file, language)
        else:
            print(f'File not found: {input_file}')


if __name__ == '__main__':
    main()
