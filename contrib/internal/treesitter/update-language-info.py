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
from inspect import cleandoc
from pathlib import Path
from typing import TYPE_CHECKING, get_args

from tree_sitter_language_pack import SupportedLanguage

from reviewboard.treesitter.query_utils import apply_standard_query_edits

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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
    ('abl', 'highlights.scm'),
    ('aiken', 'highlights.scm'),
    ('al', 'highlights.scm'),
    ('applescript', 'highlights.scm'),
    ('asciidoc', 'highlights.scm'),
    ('asciidoc', 'injections.scm'),
    ('avro', 'highlights.scm'),
    ('ballerina', 'highlights.scm'),
    ('baml', 'highlights.scm'),
    ('baml', 'injections.scm'),
    ('bsl', 'highlights.scm'),
    ('bsl', 'injections.scm'),
    ('caddy', 'highlights.scm'),
    ('cedar', 'highlights.scm'),
    ('cedarschema', 'highlights.scm'),
    ('cel', 'highlights.scm'),
    ('cel', 'injections.scm'),
    ('chuck', 'highlights.scm'),
    ('clarity', 'highlights.scm'),
    ('cmake', 'highlights.scm'),
    ('csharp', 'highlights.scm'),
    ('cst', 'highlights.scm'),
    ('cypher', 'highlights.scm'),
    ('cython', 'highlights.scm'),
    ('cython', 'injections.scm'),
    ('d2', 'highlights.scm'),
    ('d2', 'injections.scm'),
    ('dotenv', 'highlights.scm'),
    ('eiffel', 'highlights.scm'),
    ('elisp', 'highlights.scm'),
    ('fsharp_signature', 'highlights.scm'),
    ('fusion', 'highlights.scm'),
    ('gcode', 'highlights.scm'),
    ('gherkin', 'highlights.scm'),
    ('haml', 'highlights.scm'),
    ('haml', 'injections.scm'),
    ('haxe', 'highlights.scm'),
    ('haxe', 'injections.scm'),
    ('jai', 'highlights.scm'),
    ('janet', 'highlights.scm'),
    ('koka', 'highlights.scm'),
    ('koka', 'injections.scm'),
    ('lean', 'highlights.scm'),
    ('lean', 'injections.scm'),
    ('less', 'highlights.scm'),
    ('llvm_mir', 'highlights.scm'),
    ('magik', 'highlights.scm'),
    ('mojo', 'highlights.scm'),
    ('moonbit', 'highlights.scm'),
    ('moonbit', 'injections.scm'),
    ('motoko', 'highlights.scm'),
    ('nim', 'highlights.scm'),
    ('norg_meta', 'highlights.scm'),
    ('nushell', 'highlights.scm'),
    ('nushell', 'injections.scm'),
    ('openscad', 'highlights.scm'),
    ('openscad', 'injections.scm'),
    ('org', 'highlights.scm'),
    ('penrose', 'highlights.scm'),
    ('penrose', 'injections.scm'),
    ('pgn', 'highlights.scm'),
    ('picat', 'highlights.scm'),
    ('postgres', 'highlights.scm'),
    ('postgres', 'injections.scm'),
    ('prisma', 'highlights.scm'),
    ('promela', 'highlights.scm'),
    ('reason', 'highlights.scm'),
    ('reason', 'injections.scm'),
    ('roc', 'highlights.scm'),
    ('rshtml', 'highlights.scm'),
    ('rshtml', 'injections.scm'),
    ('sas', 'highlights.scm'),
    ('scss', 'highlights.scm'),
    ('slim', 'highlights.scm'),
    ('slim', 'injections.scm'),
    ('smalltalk', 'highlights.scm'),
    ('sml', 'highlights.scm'),
    ('spicedb', 'highlights.scm'),
    ('spicedb', 'injections.scm'),
    ('sql_bigquery', 'highlights.scm'),
    ('squirrel', 'highlights.scm'),
    ('squirrel', 'injections.scm'),
    ('stan', 'highlights.scm'),
    ('svelte', 'highlights.scm'),
    ('svelte', 'injections.scm'),
    ('sysml', 'highlights.scm'),
    ('tablegen', 'highlights.scm'),
    ('tmux', 'highlights.scm'),
    ('tmux', 'injections.scm'),
    ('v', 'highlights.scm'),
    ('vala', 'highlights.scm'),
    ('wdl', 'highlights.scm'),
    ('wdl', 'injections.scm'),
    ('wolfram', 'highlights.scm'),
    ('x86asm', 'highlights.scm'),
    ('xquery', 'highlights.scm'),
    ('zig', 'highlights.scm'),
    ('zig', 'injections.scm'),
    ('ziggy', 'highlights.scm'),
    ('ziggy_schema', 'highlights.scm'),

    # These are broken even in the upstream queries.
    # 'netlinx',
    # 'vhdl',
}


#: Extra file suffixes and file names for each language.
#:
#: tree-sitter-language-pack only lists file extensions for each language.
#: These fill in file names and extensions that it doesn't list. They are
#: written as-is, without adding a leading dot.
#:
#: Some of these also mark a suffix as shared by more than one language (such
#: as ``.m`` for MATLAB and Objective-C). Shared suffixes aren't matched to a
#: language unless they're listed in ``LANGUAGE_OVERRIDES``, so content-based
#: detection gets to decide.
#:
#: Version Added:
#:     9.0
EXTRA_FILE_SUFFIXES: Mapping[str, list[str]] = {
    'apex': ['.apex', '.cls'],
    'asm': ['.assembly'],
    'bash': ['.bash_profile', '.bashrc', '.ebuild', '.eclass'],
    'chatito': ['.chatl'],
    'clojure': ['.bb'],
    'cmake': ['CMakeLists.txt'],
    'cuda': ['.cuh'],
    'd': ['.dd'],
    'dockerfile': ['Containerfile', 'Dockerfile', 'dockerfile', '.container',
                   '.docker'],
    'embeddedtemplate': ['.ejs'],
    'erlang': ['rebar.config', '.app', '.app.src', '.escript'],
    'fortran': ['.F90', '.F95'],
    'gitignore': ['.fdignore', '.ignore', '.rgignore'],
    'glsl': ['.frag', '.fsh', '.vert', '.vsh'],
    'gomod': ['go.mod'],
    'gosum': ['go.sum'],
    'haskell': ['.hs-boot'],
    'heex': ['.neex'],
    'hyprlang': ['.conf'],
    'kconfig': ['Kconfig'],
    'latex': ['.aux', '.cls', '.sty'],
    'linkerscript': ['.ld', '.ldscript'],
    'llvm': ['.llvm'],
    'make': ['GNUmakefile', 'MAKEFILE', 'Makefile', 'makefile', '.dsp',
             '.mak'],
    'matlab': ['.m'],
    'netlinx': ['.axb', '.lib'],
    'nim': ['.nimble'],
    'objc': ['.objc'],
    'pascal': ['.dpr', '.lpr', '.pp'],
    'pem': ['.cer', '.crt', '.csr', '.key'],
    'perl': ['.t'],
    'pymanifest': ['MANIFEST.in'],
    'qmldir': ['qmldir'],
    'r': ['.R'],
    'requirements': ['requirements.txt', '.pip'],
    'scala': ['.sbt'],
    'scheme': ['.ss'],
    'sparql': ['.rq'],
    'tcl': ['.tk', '.tm'],
    'udev': ['.rules'],
    'ungrammar': ['.ungram'],
    'v': ['v.mod', '.vsh'],
    'xcompose': ['Compose', 'XCompose', '.XCompose'],
    'xml': ['.rng', '.svg', '.xsd'],
}


#: File suffixes that should never be matched to a language.
#:
#: tree-sitter-language-pack lists some common, generic extensions for niche
#: languages (such as ``.txt`` for Vim help files). Most files with these
#: extensions are something else, so we leave them out and let content-based
#: detection decide.
#:
#: Version Added:
#:     9.0
EXCLUDED_FILE_SUFFIXES: set[str] = {
    '.inc',
    '.mod',
    '.pro',
    '.res',
    '.txt',
}


#: reviewboard.treesitter module directory.
#: Version Added:
#:     9.0
module_dir = Path(__file__).parents[3] / 'reviewboard' / 'treesitter'


def load_language_definitions(
    language_pack_path: Path,
) -> JSONDict:
    """Load the language definitions from tree-sitter-language-pack.

    Version Added:
        9.0

    Args:
        language_pack_path (pathlib.Path):
            The path to the tree-sitter-language-pack checkout.

    Returns:
        typelets.json.JSONDict:
        A mapping from language name to its definition. Each definition
        includes the file extensions, the grammar repository, and the
        grammar revision.
    """
    definitions_path = (language_pack_path / 'sources' /
                        'language_definitions.json')

    with definitions_path.open() as f:
        return json.load(f)


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
    language_pack_path: Path,
    parsers_path: Path,
    definitions: JSONDict,
) -> None:
    """Copy queries files from the tree-sitter-language-pack parsers.

    Args:
        language_pack_path (pathlib.Path):
            The path to the tree-sitter-language-pack checkout.

        parsers_path (pathlib.Path):
            The path to the parsers in the tree-sitter-language-pack checkout.

        definitions (typelets.json.JSONDict):
            The language definitions from tree-sitter-language-pack.
    """
    parsers_path = language_pack_path / 'parsers'
    lock_data: JSONDict = {}

    for language, filename in UPSTREAM_GRAMMAR_QUERIES:
        queries_path = parsers_path / language / 'queries' / filename
        target_dir = module_dir / 'queries' / language

        if not queries_path.exists():
            logger.warning('Queries file %s does not exist',
                           queries_path)
            continue

        if not target_dir.exists():
            target_dir.mkdir()

        # Upstream queries are written for nvim-treesitter, so they need
        # the same rewrites (such as lua-match? to match?) as queries
        # pulled in by update-queries.py.
        (target_dir / filename).write_bytes(
            apply_standard_query_edits(queries_path.read_bytes()))

        definition = definitions[language]

        if 'local' in definition:
            # The grammar lives inside tree-sitter-language-pack itself.
            lock_data[f'{language}/{filename}'] = {
                'commit': get_git_revision(language_pack_path),
                'path': definition['local'],
                'remote': get_git_remote(language_pack_path),
            }
        else:
            lock_data[f'{language}/{filename}'] = {
                'commit': definition['rev'],
                'remote': definition['repo'],
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

    parsers_path = tree_sitter_language_pack_path / 'parsers'

    if not parsers_path.exists():
        sys.stderr.write(
            f'Path {parsers_path} does not exist. Did you run '
            f'scripts/clone_vendors.py in your tree-sitter-language-pack '
            f'checkout?'
        )
        sys.exit(1)

    languages = set(args.language or get_args(SupportedLanguage))
    definitions = load_language_definitions(tree_sitter_language_pack_path)
    language_extensions: dict[str, list[str]] = {
        lang: definitions[lang].get('extensions', [])
        for lang in languages
        if lang in definitions
    }
    language_keys = sorted(language_extensions.keys())

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

        for lang in language_keys:
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

        for lang in language_keys:
            suffixes = {
                f'.{extension}'
                for extension in language_extensions[lang]
            }
            suffixes.update(EXTRA_FILE_SUFFIXES.get(lang, []))
            suffixes -= EXCLUDED_FILE_SUFFIXES

            for suffix in suffixes:
                suffix_to_langs[suffix].append(lang)

        # Sort by suffix length (longest first), then alphabetically.
        sorted_suffixes = sorted(suffix_to_langs.keys(),
                                 key=lambda suffix: (-len(suffix), suffix))

        for suffix in sorted_suffixes:
            langs = suffix_to_langs[suffix]
            f.write(f'    {suffix!r}: {langs!r},\n')

        f.write('})\n')

    copy_queries(tree_sitter_language_pack_path, parsers_path, definitions)


if __name__ == '__main__':
    main()
