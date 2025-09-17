#!/usr/bin/env python3
"""Update the TreeSitter language information.

Version Added:
    9.0
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from inspect import cleandoc
from pathlib import Path
from shutil import copy2
from typing import TYPE_CHECKING, get_args

from tree_sitter_language_pack import SupportedLanguage

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from typelets.json import JSONDict


logger = logging.getLogger(__name__)


#: MIME types for each supported language.
#:
#: Version Added:
#:     9.0
LANGUAGE_MIME_TYPES: Mapping[str, list[str]] = {
    'actionscript': [],
    'ada': ['text/x-ada'],
    'agda': [],
    'apex': ['text/x-apex'],
    'arduino': [],
    'asm': [
        'text/x-assembly',
        'text/x-asm',
        'text/x-nasm',
    ],
    'astro': [],
    'bash': [
        'text/x-shell',
        'text/x-shellscript',
        'application/x-shellscript',
        'application/x-sh',
        'text/x-sh',
        'text/x-bash',
    ],
    'beancount': [],
    'bibtex': [
        'application/x-bibtex',
        'text/x-bibtex',
    ],
    'bicep': [],
    'bitbake': ['text/x-bitbake'],
    'c': [
        'text/x-c',
        'text/x-csrc',
        'text/x-chdr',
    ],
    'cairo': [],
    'capnp': [],
    'chatito': [],
    'clarity': [],
    'clojure': [
        'text/x-clojure',
    ],
    'cmake': ['text/x-cmake'],
    'comment': [],
    'commonlisp': ['text/x-commonlisp'],
    'cpon': [],
    'cpp': [
        'text/x-c++',
        'text/x-cpp',
        'text/x-c++src',
        'text/x-cxx',
        'text/x-c++hdr',
    ],
    'csharp': [
        'text/x-csharp',
        'text/x-cs',
    ],
    'css': ['text/css'],
    'csv': [
        'text/csv',
        'application/csv',
    ],
    'cuda': [
        'text/x-cuda',
    ],
    'd': [
        'text/x-dlang',
    ],
    'dart': [
        'text/x-dart',
    ],
    'dockerfile': [
        'text/x-dockerfile',
        'application/x-dockerfile',
    ],
    'doxygen': [],
    'dtd': ['application/xml-dtd'],
    'elisp': ['text/x-elisp'],
    'elixir': ['text/x-elixir'],
    'elm': ['text/x-elm'],
    'embeddedtemplate': [],
    'erlang': ['text/x-erlang'],
    'fennel': [],
    'firrtl': [],
    'fish': ['text/x-fish'],
    'fortran': ['text/x-fortran'],
    'func': [],
    'gdscript': ['text/x-gdscript'],
    'gitattributes': [],
    'gitcommit': [],
    'gitignore': [],
    'gleam': [],
    'glsl': ['text/x-glsl'],
    'gn': [],
    'go': [
        'text/x-go',
        'text/x-golang',
    ],
    'gomod': [],
    'gosum': [],
    'graphql': [],
    'groovy': [],
    'gstlaunch': [],
    'hack': [
        'text/x-hack',
        'application/x-hack',
    ],
    'hare': [],
    'haskell': ['text/x-haskell'],
    'haxe': [],
    'hcl': ['text/x-hcl'],
    'hlsl': ['text/x-hlsl'],
    'html': [
        'application/html',
        'application/xhtml',
        'application/xhtml+xml',
        'text/html',
        'text/xtml',
    ],
    'hyprlang': [],
    'ini': [],
    'ispc': ['text/x-ispc'],
    'janet': [],
    'java': [
        'text/x-java',
        'text/x-java-source',
    ],
    'javascript': [
        'text/javascript',
        'application/javascript',
        'application/x-javascript',
        'application/ecmascript',
        'text/ecmascript',
        'text/jsx',
    ],
    'jsdoc': [],
    'json': [
        'application/json',
        'text/json',
        'application/json5',
    ],
    'jsonnet': [],
    'julia': ['text/x-julia'],
    'kconfig': [],
    'kdl': [],
    'kotlin': ['text/x-kotlin'],
    'latex': [
        'text/x-latex',
        'application/x-latex',
        'text/x-tex',
        'application/x-tex',
    ],
    'linkerscript': [],
    'llvm': [
        'text/x-llvm',
        'application/x-llvm',
    ],
    'lua': [
        'text/x-lua',
        'application/x-lua',
    ],
    'luadoc': [],
    'luap': [],
    'luau': ['text/x-luau'],
    'magik': ['text/x-magik'],
    'make': ['text/x-makefile'],
    'markdown': [
        'text/markdown',
        'text/x-markdown',
        'application/x-gfm',
    ],
    'markdown_inline': [],
    'matlab': [
        'text/x-matlab',
        'text/x-octave',
    ],
    'mermaid': [],
    'meson': ['text/x-meson'],
    'netlinx': [],
    'nim': [],
    'ninja': ['text/x-ninja'],
    'nix': [
        'application/x-nix',
        'text/x-nix',
    ],
    'objc': [
        'text/x-objective-c',
        'text/x-objcsrc',
        'text/x-objchdr',
    ],
    'ocaml': [
        'text/x-ocaml',
    ],
    'ocaml_interface': [],
    'odin': [],
    'org': [],
    'pascal': ['text/x-pascal'],
    'pem': [],
    'perl': [
        'text/x-perl',
        'application/x-perl',
    ],
    'pgn': [],
    'php': [
        'text/x-php',
        'application/x-httpd-php',
        'application/x-httpd-php-source',
    ],
    'po': ['text/x-po'],
    'pony': ['text/x-pony'],
    'powershell': [
        'text/x-powershell',
        'application/x-powershell',
    ],
    'printf': [],
    'prisma': ['text/x-prisma'],
    'properties': ['text/x-properties'],
    'proto': [
        'text/x-proto',
        'application/x-protobuf',
    ],
    'psv': ['text/x-psv'],
    'puppet': ['text/x-puppet'],
    'purescript': ['text/x-purescript'],
    'pymanifest': [],
    'python': [
        'text/x-python',
        'text/x-python3',
        'application/x-python',
        'application/x-python-code',
    ],
    'qmldir': [],
    'qmljs': [],
    'query': [],
    'r': [
        'text/x-r',
        'application/x-r',
    ],
    'racket': ['text/x-racket'],
    're2c': [],
    'readline': [],
    'rego': [],
    'requirements': [],
    'ron': [],
    'rst': [
        'text/x-rst',
        'text/x-restructuredtext',
    ],
    'ruby': [
        'text/x-ruby',
        'application/x-ruby',
    ],
    'rust': [
        'text/x-rust',
        'text/rust',
    ],
    'scala': ['text/x-scala'],
    'scheme': ['text/x-scheme'],
    'scss': ['text/scss'],
    'smali': [],
    'smithy': [],
    'solidity': ['text/x-solidity'],
    'sparql': [
        'application/x-sparql-query',
        'text/x-sparql',
    ],
    'sql': [
        'text/x-sql',
        'application/sql',
        'application/x-sql',
        'text/x-plsql',
    ],
    'squirrel': [],
    'starlark': [],
    'svelte': [],
    'swift': ['text/x-swift'],
    'tablegen': [],
    'tcl': [
        'text/x-tcl',
        'application/x-tcl',
    ],
    'terraform': [
        'text/x-terraform',
        'application/x-terraform',
    ],
    'test': [],
    'thrift': [
        'text/x-thrift',
        'application/x-thrift',
    ],
    'toml': [
        'text/x-toml',
        'application/toml',
    ],
    'tsv': ['text/tab-separated-values'],
    'tsx': [
        'text/tsx',
        'text/x-tsx',
    ],
    'typescript': [
        'text/typescript',
        'application/typescript',
        'text/x-typescript',
    ],
    'typst': [],
    'udev': [],
    'ungrammar': [],
    'uxntal': [],
    'v': [],
    'verilog': [],
    'vhdl': [],
    'vim': [],
    'vue': [],
    'wgsl': ['text/x-wgsl'],
    'xcompose': [],
    'xml': [
        'text/xml',
        'application/xml',
        'application/rss+xml',
        'application/atom+xml',
        'image/svg+xml',
    ],
    'yaml': [
        'text/x-yaml',
        'application/yaml',
        'application/x-yaml',
        'text/yaml',
        'text/vnd.yaml',
    ],
    'yuck': [],
    'zig': ['text/x-zig'],
}


#: A list of languages that we use the upstream queries files for.
#:
#: For these languages, we pull highlights.scm and injections.scm files out of
#: the grammar implementation, instead of using queries from nvim-treesitter.
UPSTREAM_GRAMMAR_QUERIES: set[tuple[str, str]] = {
    ('clarity', 'highlights.scm'),
    ('cmake', 'highlights.scm'),
    ('elisp', 'highlights.scm'),
    ('janet', 'highlights.scm'),
    ('org', 'highlights.scm'),
    ('magik', 'highlights.scm'),
    ('pgn', 'highlights.scm'),
    ('prisma', 'highlights.scm'),
    ('scss', 'highlights.scm'),
    ('squirrel', 'highlights.scm'),
    ('squirrel', 'injections.scm'),
    ('svelte', 'highlights.scm'),
    ('svelte', 'injections.scm'),
    ('tablegen', 'highlights.scm'),
    ('v', 'highlights.scm'),
    ('zig', 'highlights.scm'),
    ('zig', 'injections.scm'),

    # These are broken even in the vendor queries.
    # 'haxe',
    # 'netlinx',
    # 'vhdl',
}


#: reviewboard.treesitter module directory.
#: Version Added:
#:     9.0
module_dir = Path(__file__).parents[3] / 'reviewboard' / 'treesitter'


@dataclass
class GrammarInfo:
    """Information about a grammar.

    Version Added:
        9.0
    """

    #: A list of filename suffixes that this language applies to.
    file_suffixes: list[str]

    #: A regular expression to check against the first line of the file.
    first_line_regex: str | None

    #: The grammar name.
    name: str


def load_grammar_info(
    base_path: Path,
    data: JSONDict,
) -> GrammarInfo:
    """Load grammar info from JSON data.

    Version Added:
        9.0

    Args:
        base_path (pathlib.Path):
            The path to the grammar checkout.

        data (typelets.json.JSONDict):
            The loaded grammar data.

    Returns:
        GrammarInfo:
        The loaded grammar info.
    """
    file_suffixes = data.get('file-types')

    if file_suffixes is None:
        file_suffixes = []

    if not isinstance(file_suffixes, list):
        logger.warning(
            'Invalid data for key "file-types" in file suffixes %r from %s',
            file_suffixes, base_path)
        file_suffixes = []

    first_line_regex = data.get('first-line-regex')

    if first_line_regex is not None and not isinstance(first_line_regex, str):
        logger.warning(
            'Invalid data "%s" for key "first-line-regex" in data from %s',
            first_line_regex, base_path)
        first_line_regex = None

    return GrammarInfo(
        name=base_path.stem,
        file_suffixes=file_suffixes,
        first_line_regex=first_line_regex)


def get_grammars(
    path: Path,
) -> Iterator[GrammarInfo]:
    """Yield the grammar blobs for a package.

    Version Added:
        9.0

    Args:
        path (pathlib.Path):
            The path to the grammar.

    Yields:
        typelets.json.JSONDict:
        The loaded info about the grammar.
    """
    try:
        with (path / 'tree-sitter.json').open() as f:
            p = json.load(f)

            for grammar in p['grammars']:
                yield load_grammar_info(path, grammar)
    except OSError:
        # No tree-sitter.json file present.
        pass

    try:
        with (path / 'package.json').open() as f:
            p = json.load(f)

            if 'tree-sitter' in p:
                for grammar in p['tree-sitter']:
                    yield load_grammar_info(path, grammar)
    except OSError:
        # No package.json file present.
        pass


def load_grammars(
    vendor_path: Path,
    languages: set[str],
) -> dict[str, GrammarInfo]:
    """Load the grammar information.

    Version Added:
        9.0

    Args:
        vendor_path (pathlib.Path):
            The path to the vendor directory.

        languages (set of str):
            The set of languages to load grammars for.

    Returns:
        dict:
        A mapping from grammar name to grammar information.
    """
    # tree-sitter-language-pack directly depends on these Python packages, and
    # therefore those don't get cloned into vendor. We therefore hardcode the
    # data for these:
    #   * tree-sitter-c-sharp
    #   * tree-sitter-embedded-template
    #   * tree-sitter-yaml
    result: dict[str, list[GrammarInfo]] = defaultdict(list, {
        'csharp': [
            GrammarInfo(file_suffixes=['cs'], first_line_regex=None,
                        name='csharp'),
        ],
        'embeddedtemplate': [
            GrammarInfo(file_suffixes=['ejs', 'erb'], first_line_regex=None,
                        name='embeddedtemplate'),
        ],
        'yaml': [
            GrammarInfo(file_suffixes=['yml', 'yaml'], first_line_regex=None,
                        name='yaml'),
        ],
    })

    for language in languages:
        subdir = vendor_path / language

        for grammar in get_grammars(subdir):
            result[grammar.name].append(grammar)

    def merge_info(
        a: GrammarInfo,
        b: GrammarInfo,
    ) -> GrammarInfo:
        if a.name != b.name:
            raise ValueError(
                f'Error while merging GrammarInfo: names {a.name} and '
                f'{b.name} do not match!')

        return GrammarInfo(
            file_suffixes=list(
                set(a.file_suffixes) | set(b.file_suffixes)
            ),
            first_line_regex=a.first_line_regex or b.first_line_regex,
            name=a.name,
        )

    return {
        name: reduce(merge_info, infos)
        for name, infos in result.items()
    }


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


def get_git_remote(
    repo_path: Path,
) -> str:
    """Get the git remote URL from the given repository.

    Args:
        repo_path (pathlib.Path):
            The path to the git repository.

    Returns:
        str:
        The git remote URL.
    """
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def write_lock_file(
    lock_data: JSONDict,
) -> None:
    """Write the lock file.

    This function loads the existing lock file (if it exists) and merges
    the new data into it, only overwriting keys that are present in the
    new lock_data. This allows queries from other packages to be preserved.

    Args:
        lock_data (dict):
            The data to write to the lock file.
    """
    lock_file_path = module_dir / 'queries' / 'queries.lock'

    # Load existing lock file if it exists
    existing_data: JSONDict = {}

    if lock_file_path.exists():
        try:
            with lock_file_path.open('r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning('Failed to load existing lock file: %s', e)

    # Update top-level keys.
    for key, value in lock_data.items():
        existing_data[key] = value

    with lock_file_path.open('w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, sort_keys=True)
        f.write('\n')


def copy_queries(
    vendor_path: Path,
) -> None:
    """Copy queries files from vendor directories.

    Args:
        vendor_path (pathlib.Path):
            Th path to the vendor directory.
    """
    lock_data: JSONDict = {}

    for language, filename in UPSTREAM_GRAMMAR_QUERIES:
        repo_path = vendor_path / language
        queries_path = repo_path / 'queries' / filename
        target_dir = module_dir / 'queries' / language

        if not queries_path.exists():
            logger.warning('Queries file %s does not exist',
                           queries_path)

        if not target_dir.exists():
            target_dir.mkdir()

        git_remote = get_git_remote(repo_path)
        git_revision = get_git_revision(repo_path)

        copy2(queries_path, target_dir)

        lock_data[f'{language}/{filename}'] = {
            'commit': git_revision,
            'remote': git_remote,
        }

    write_lock_file(lock_data)


def parse_arguments(
    args: Sequence[str],
) -> argparse.Namespace:
    """Parse the command-line arguments and return the results.

    Version Added:
        9.0

    Args:
        args (list of bytes):
            The arguments to parse.
    """
    parser = argparse.ArgumentParser(
        'Update the TreeSitter language information.',
        usage='%(prog)s [options]',
    )

    parser.add_argument('tree_sitter_language_pack_checkout')
    parser.add_argument('-l', '--language', action='append')

    return parser.parse_args(args)


def main() -> None:
    """Extract data from the tree-sitter vendor packages."""
    args = parse_arguments(sys.argv[1:])

    tree_sitter_language_pack_path = \
        Path(args.tree_sitter_language_pack_checkout)

    vendor_path = tree_sitter_language_pack_path / 'vendor'

    if not vendor_path.exists():
        sys.stderr.write(
            f'Path {vendor_path} does not exist. Did you run '
            f'scripts/clone_vendors.py in your tree-sitter-language-pack '
            f'checkout?'
        )
        sys.exit(1)

    languages = set(args.language or get_args(SupportedLanguage))

    grammars = load_grammars(vendor_path, languages)

    with open(module_dir / '_languages.py', 'w', encoding='utf-8') as f:
        f.write(cleandoc('''
            """Language information for treesitter.

            Do not make changes directly to this file! This file is auto-
            generated by contrib/internal/treesitter/update-language-info.py.
            """

            from __future__ import annotations

            from collections import OrderedDict

            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from collections.abc import Mapping

                from tree_sitter_language_pack import SupportedLanguage
        '''))
        f.write('\n\n\n')

        # Generate the MIME_TYPE_TO_LANGUAGE mapping.
        f.write('MIME_TYPE_TO_LANGUAGE: Mapping[str, SupportedLanguage] = {\n')

        mime_to_lang = {}

        for lang in sorted(grammars.keys()):
            mime_types = LANGUAGE_MIME_TYPES.get(lang, [])

            for mime_type in mime_types:
                mime_to_lang[mime_type] = lang

        # Write the mapping sorted by MIME type
        for mime_type in sorted(mime_to_lang.keys()):
            lang = mime_to_lang[mime_type]
            f.write(f'    {mime_type!r}: {lang!r},\n')

        f.write('}\n')

        # Generate the FILE_SUFFIX_TO_LANGUAGES mapping.
        f.write('\n\n')
        f.write(
            'FILE_SUFFIX_TO_LANGUAGES: '
            'OrderedDict[str, list[SupportedLanguage]] = OrderedDict({\n'
        )

        suffix_to_langs: dict[str, list[str]] = defaultdict(list)

        for lang in sorted(grammars.keys()):
            info = grammars[lang]
            if info.file_suffixes:
                for suffix in info.file_suffixes:
                    # If the suffix is very short, we want to enforce it being
                    # a file extension. Otherwise we can have issues like
                    # {'t': ['perl']} matching .txt files.
                    if len(suffix) <= 4 and not suffix.startswith('.'):
                        suffix = f'.{suffix}'

                    suffix_to_langs[suffix].append(lang)

        # Sort by suffix length (longest first), then alphabetically.
        sorted_suffixes = sorted(suffix_to_langs.keys(),
                                 key=lambda suffix: (-len(suffix), suffix))

        for suffix in sorted_suffixes:
            langs = suffix_to_langs[suffix]
            f.write(f'    {suffix!r}: {langs!r},\n')

        f.write('})\n')

    copy_queries(vendor_path)


if __name__ == '__main__':
    main()
