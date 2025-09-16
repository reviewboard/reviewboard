#!/usr/bin/env python3
"""Update the TreeSitter queries files.

Version Added:
    8.0
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import tree_sitter
from tqdm import tqdm
from tree_sitter_language_pack import get_language, get_parser

from reviewboard.treesitter.language import SUPPORTED_LANGUAGES
from reviewboard.treesitter.query_utils import (
    apply_standard_query_edits,
    get_all_predicate_names,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from typelets.django.json import SerializableDjangoJSONDict

    from reviewboard.treesitter.language import SupportedLanguage


logger = logging.getLogger(__name__)


#: Languages for which we have custom queries.
EXCLUDED_LANGUAGES: set[SupportedLanguage] = {
    # The HTML queries in nvim-treesitter are extremely inefficient, and don't
    # buy us anything. We have custom ones based on the tree-sitter-html
    # queries but with improved injections support.
    'html',

    # nvim-treesitter uses a different tree-sitter-prisma than
    # tree-sitter-language-pack.
    'prisma',

    # nvim-treesitter uses a different tree-sitter-scss than
    # tree-sitter-language-pack.
    'scss',

    # This one I don't understand at all. nvim-treesitter uses the same grammar
    # at the same commit.
    'squirrel',

    # nvim-treesitter uses a different fork of tree-sitter-tablegen than
    # tree-sitter-language-pack.
    'tablegen',

    # nvim-treesitter uses a different tree-sitter-vhdl than
    # tree-sitter-language-pack.
    'vhdl',
}


#: Directory names for languages where nvim-treesitter uses a different name.
LANGUAGE_DIR_NAMES: Mapping[str, str] = {
    'csharp': 'c_sharp',
    'embeddedtemplate': 'embedded_template',
}


#: Storage for all predicates across all files.
#:
#: This is used to show a warning if query files contain a predicate that we
#: don't have implemented in
#: :py:func:`reviewboard.treesitter.highlight.predicate_handler`.
all_predicates: set[str] = set()


#: Directory for queries files.
queries_dir = \
    Path(__file__).parents[3] / 'reviewboard' / 'treesitter' / 'queries'


def get_git_revision(
    repo_path: Path,
) -> str:
    """Get the current git revision from the given repository.

    Args:
        repo_path (pathlib.Path):
            The path to the git repository.

    Returns:
        str:
        The current git revision hash.
    """
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def write_lock_file(
    lock_data: SerializableDjangoJSONDict,
) -> None:
    """Write the lock file.

    This function loads the existing lock file (if it exists) and merges
    the new data into it, only overwriting keys that are present in the
    new lock_data. This allows queries from other packages to be preserved.

    Args:
        lock_data (dict):
            The data to write to the lock file.
    """
    lock_file_path = queries_dir / 'nvim-treesitter.lock'

    # Load existing lock file if it exists
    existing_data: SerializableDjangoJSONDict = {}

    if lock_file_path.exists():
        try:
            with lock_file_path.open('r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning('Failed to load existing lock file: %s', e)

    # Update top-level keys.
    for key, value in lock_data.items():
        if (key == 'files' and isinstance(value, dict) and
            'files' in existing_data):
            # For the 'files' key, merge the dictionaries.
            if not isinstance(existing_data['files'], dict):
                existing_data['files'] = {}

            existing_data['files'].update(value)
        else:
            # For other keys, overwrite.
            existing_data[key] = value

    with lock_file_path.open('w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, sort_keys=True)
        f.write('\n')


def validate_queries_with_grammar(
    language: SupportedLanguage,
    queries: bytes,
) -> bool:
    """Validate that queries work with the available grammar version.

    Args:
        language (str):
            The language name.

        queries (bytes):
            The queries content to validate.

    Returns:
        bool:
        True if the queries are compatible with the grammar, False otherwise.
    """
    try:
        ts_language = get_language(language)
        tree_sitter.Query(ts_language, queries.decode())

        return True
    except Exception:
        return False


def get_file_commit_history(
    repo_path: Path,
    file_path: Path,
    max_commits: int = 50,
) -> list[str]:
    """Get the commit history for a specific file.

    Args:
        repo_path (pathlib.Path):
            The path to the git repository.

        file_path (pathlib.Path):
            The path to the file within the repository.

        max_commits (int, optional):
            Maximum number of commits to retrieve.

    Returns:
        list of str:
        List of commit hashes in reverse chronological order.
    """
    try:
        result = subprocess.run(
            ['git', 'log', '--format=%H', f'-{max_commits}', '--',
             file_path.relative_to(repo_path)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout.strip()

        if output:
            return output.split('\n')
    except subprocess.CalledProcessError:
        pass

    return []


def get_file_at_commit(
    repo_path: Path,
    file_path: Path,
    commit_hash: str,
) -> bytes | None:
    """Get the content of a file at a specific commit.

    Args:
        repo_path (pathlib.Path):
            The path to the git repository.

        file_path (str):
            The relative path to the file within the repository.

        commit_hash (str):
            The commit hash to retrieve the file from.

    Returns:
        bytes or None:
        The file content, or None if the file doesn't exist at that commit.
    """
    relative_path = file_path.relative_to(repo_path)

    try:
        result = subprocess.run(
            ['git', 'show', f'{commit_hash}:{relative_path}'],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        return result.stdout
    except subprocess.CalledProcessError:
        return None


def read_queries(
    *,
    repo_path: Path,
    queries_path: Path,
    language: str,
    filename: str,
    commit_hash: (str | None) = None,
) -> bytes | None:
    """Read queries for a language.

    Args:
        repo_path (pathlib.Path):
            The path to the nvim-treesitter git repository.

        queries_path (pathlib.Path):
            The path to the nvim-treesitter queries directory.

        language (str):
            The name of the language to process.

        filename (str):
            The name of the queries file to process.

        commit_hash (str, optional):
            The commit hash to read the queries content from.

    Returns:
        bytes:
        The queries content.

    Raises:
        ValueError:
            The file was not found at the given commit.
    """
    language_dir = LANGUAGE_DIR_NAMES.get(language, language)
    file_path = queries_path / language_dir / filename

    if commit_hash:
        content = get_file_at_commit(
            repo_path,
            file_path,
            commit_hash)

        if content is None:
            raise ValueError(
                f'{file_path} was not found in nvim-treesitter tree at commit '
                f'{commit_hash}'
            )
    else:
        if not file_path.exists():
            return None

        with file_path.open('rb') as f:
            content = f.read()

    if content.startswith(b'; inherits'):
        prefix, data = content.split(b'\n', 1)
        inherited = (
            prefix
            .removeprefix(b'; inherits')
            .removeprefix(b':')
            .strip()
            .decode()
            .split(',')
        )

        content = b''

        for parent_lang in inherited:
            parent_content = read_queries(
                repo_path=repo_path,
                queries_path=queries_path,
                language=parent_lang,
                filename=filename,
                commit_hash=commit_hash)

            if parent_content is None:
                raise ValueError(
                    f'Inherited file {filename} does not exist for language '
                    f'{language} at commit {commit_hash}'
                )

            content += parent_content
            content += b'\n\n'

        content += data

    return content.strip()


def read_queries_with_fallback(
    *,
    repo_path: Path,
    queries_path: Path,
    language: SupportedLanguage,
    filename: str,
    query_parser: tree_sitter.Parser,
    verbose: bool,
) -> tuple[bytes | None, str | None]:
    """Read queries with fallback to older commits if validation fails.

    Args:
        repo_path (pathlib.Path):
            The path to the nvim-treesitter git repository.

        queries_path (pathlib.Path):
            The path to the nvim-treesitter queries directory.

        language (str):
            The name of the language to process.

        filename (str):
            The name of the queries filename to process.

        query_parser (tree_sitter.Parser):
            The Tree Sitter parser for queries files.

        verbose (bool):
            Whether to use verbose output.

    Returns:
        tuple:
        A 2-tuple of:

        Tuple:
            0 (bytes):
                The queries content.

            1 (str or None):
                A commit hash. If the current version works, this will be None.
                If a fallback was required, this will be the commit containing
                the working queries file.
    """
    # Try current version first.
    queries = read_queries(
        repo_path=repo_path,
        queries_path=queries_path,
        language=language,
        filename=filename)

    if not queries:
        return None, None

    queries = apply_standard_query_edits(queries)

    if validate_queries_with_grammar(language, queries):
        if verbose:
            print(f'  ✓ Current queries work for {language}/{filename}')

        return queries, None

    if verbose:
        print(
            f'  ⚠ Current queries incompatible with grammar for '
            f'{language}/{filename}, scanning commit history...'
        )

    # Get the relative path to the query file
    language_dir = LANGUAGE_DIR_NAMES.get(language, language)
    file_path = queries_path / language_dir / filename

    # Get commit history for this specific file
    commits = get_file_commit_history(
        repo_path,
        file_path)

    if not commits:
        print(f'    No commit history found for {file_path}')

        return None, None

    # Try each commit until we find one that works
    for i, commit_hash in enumerate(commits):
        try:
            queries = read_queries(
                repo_path=repo_path,
                queries_path=queries_path,
                language=language,
                filename=filename,
                commit_hash=commit_hash,
            )

            # This should never happen.
            assert queries is not None

            queries = apply_standard_query_edits(queries)

            if validate_queries_with_grammar(language, queries):
                if verbose:
                    print(
                        f'    ✓ Found compatible queries at commit '
                        f'{commit_hash[:8]} (going back {i + 1} commits)'
                    )

                return queries, commit_hash
        except Exception as e:
            logger.warning('    Error testing commit %s: %s',
                           commit_hash[:8], e)

            continue

    if verbose:
        print(f'    ✗ No compatible queries found in {len(commits)} commits')

    return None, None


def find_predicate_names(
    parser: tree_sitter.Parser,
    queries: bytes,
) -> None:
    """Find all predicate names in the given queries.

    Queries files use a variety of directives and predicates. Some of these are
    built in to py-tree-sitter, and some are implemented in
    :py:mod:`reviewboard.treesitter.predicates`. This will save all predicate
    names found in the queries to a global set so we can print a warning if any
    query files include predicates or directives which are not implemented in
    our code.

    Args:
        parser (tree_sitter.Parser):
            The Tree Sitter parser for queries files.

        queries (bytes):
            The loaded queries.
    """
    tree = parser.parse(queries)

    global all_predicates
    all_predicates |= get_all_predicate_names(tree)


def process_language(
    *,
    query_parser: tree_sitter.Parser,
    repo_path: Path,
    queries_path: Path,
    language: SupportedLanguage,
    main_revision: str,
    verbose: bool,
) -> dict[str, dict[str, str]]:
    """Process a language.

    Args:
        query_parser (tree_sitter.Parser):
            The Tree Sitter parser for queries files.

        repo_path (pathlib.Path):
            The path to the nvim-treesitter git repository.

        queries_path (pathlib.Path):
            The path to the nvim-treesitter queries directory.

        language (str):
            The name of the language to process.

        main_revision (str):
            The main nvim-treesitter revision.

        verbose (bool):
            Whether to use verbose output.

    Returns:
        dict:
        A dictionary mapping query file paths to their package and commit info.
    """
    output_dir = queries_dir / language

    if not output_dir.exists():
        output_dir.mkdir()

    file_info = {}

    for filename in ['highlights.scm', 'injections.scm']:
        if verbose:
            print(f'Processing {language}/{filename}')

        queries, commit_hash = read_queries_with_fallback(
            repo_path=repo_path,
            queries_path=queries_path,
            language=language,
            filename=filename,
            query_parser=query_parser,
            verbose=verbose)

        if queries:
            find_predicate_names(query_parser, queries)

            output_file = output_dir / filename

            with output_file.open('wb') as f:
                f.write(queries)

                if not queries.endswith(b'\n'):
                    f.write(b'\n')

            # Record file info with package and commit
            file_key = f'{language}/{filename}'
            file_info[file_key] = {
                'source': 'nvim-treesitter',
                'commit': commit_hash if commit_hash else main_revision
            }
        elif verbose:
            print('    ✗ No queries found')

        if verbose:
            print()

    return file_info


def parse_arguments(
    args: Sequence[str],
) -> argparse.Namespace:
    """Parse the command-line arguments and return the results.

    Args:
        args (list of bytes):
            The arguments to parse.

    Returns:
        argparse.Namespace:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        'Update the TreeSitter queries files.',
        usage='%(prog)s [options]',
    )

    parser.add_argument('nvim_treesitter_checkout')
    parser.add_argument('-l', '--language', action='append', dest='languages')
    parser.add_argument('-v', '--verbose', action='store_true')

    return parser.parse_args(args)


def main() -> None:
    """Update the TreeSitter queries files."""
    args = parse_arguments(sys.argv[1:])

    nvim_treesitter_path = Path(args.nvim_treesitter_checkout)
    queries_path = nvim_treesitter_path / 'runtime' / 'queries'

    if not queries_path.exists():
        logger.error(f'Path {queries_path} does not exist')
        sys.exit(1)

    query_parser = get_parser('query')

    verbose = args.verbose
    languages = args.languages

    if languages:
        unknown_languages = set(languages) - SUPPORTED_LANGUAGES

        if unknown_languages:
            for language in unknown_languages:
                logger.error(f'Language "{language}" is not supported.')

            sys.exit(1)
    else:
        languages = SUPPORTED_LANGUAGES - EXCLUDED_LANGUAGES

    # Get the git revision first, as we need it for processing
    try:
        main_revision = get_git_revision(nvim_treesitter_path)
    except subprocess.CalledProcessError as e:
        logger.error('Failed to get git revision: %s', e)
        sys.exit(1)

    # Track all processed files with their package and commit info
    all_file_info = {}

    print('Processing query files from nvim-treesitter...')

    t = tqdm(
        sorted(languages),
        bar_format='{desc} {bar} [{n_fmt}/{total_fmt}]',
        ncols=80,
        disable=verbose)

    for language in t:
        if language in EXCLUDED_LANGUAGES:
            logger.warning(
                'Language "%s" has been explicitly excluded from '
                'nvim-treesitter loading, likely due to incompatible or '
                'broken queries. Make sure to test that things work!',
                language)

        file_info = process_language(
            query_parser=query_parser,
            repo_path=nvim_treesitter_path,
            queries_path=queries_path,
            language=language,
            main_revision=main_revision,
            verbose=verbose,
        )

        all_file_info.update(file_info)

    known_predicates = {
        'any-contains',
        'any-eq',
        'any-match',
        'any-not-eq',
        'any-not-match',
        'any-of',
        'contains',
        'eq',
        'gsub',
        'has-ancestor',
        'has-parent',
        'is-not',
        'is',
        'match',
        'not-any-of',
        'not-eq',
        'not-has-ancestor',
        'not-has-parent',
        'not-match',
        'set',
    }

    unknown_predicates = all_predicates - known_predicates

    if unknown_predicates:
        logger.warning(
            '\n'.join([
                'Warning: queries contained unknown predicates:',
                *[
                    f'    {p}' for p in unknown_predicates
                ],
                '',
            ])
        )

    # Report fallback commit usage
    fallback_files = {
        file_path: info
        for file_path, info in all_file_info.items()
        if info['commit'] != main_revision
    }

    if fallback_files:
        logger.warning('\n'.join([
            'Files that required fallback to older commits:',
            *[
                f'    {file_path}: {info["commit"][:8]}'
                for file_path, info in fallback_files.items()
            ],
            '',
        ]))

    lock_data: SerializableDjangoJSONDict = {
        'nvim_treesitter_revision': main_revision,
        'files': all_file_info,
    }

    write_lock_file(lock_data)

    if verbose:
        print(f'Lock file updated with revision: {main_revision}')


if __name__ == '__main__':
    main()
