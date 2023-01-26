#!/usr/bin/env python3
"""Write node.js dependencies to reviewboard/dependencies.py.

Version Added:
    6.0
"""

import json
import os
from typing import Dict, TextIO


MARKER_START = '# Auto-generated Node.js dependencies {\n'
MARKER_END = '# } Auto-generated Node.js dependencies\n'


def _write_deps(
    *,
    fp: TextIO,
    doc: str,
    name: str,
    deps: Dict[str, str],
) -> None:
    """Write dependencies to the file.

    This will write the Python code to list each dependency and the
    matching version.

    Args:
        fp (io.TextIO):
            The file to write to.

        doc (str):
            The doc comment contents.

        name (str):
            The name of the variable to write to.

        deps (dict):
            The dependencies to write.
    """
    fp.write(
        '#: %(doc)s\n'
        '%(name)s: Dict[str, str] = {\n'
        '%(deps)s\n'
        '}\n'
        '\n'
        % {
            'doc': doc,
            'name': name,
            'deps': '\n'.join(
                f"    '{dep_name}': '{dep_ver}',"
                for dep_name, dep_ver in deps.items()
                if not dep_ver.startswith('file:')
            ),
        })


def main() -> None:
    """Embed package.json into reviewboard/dependencies.py."""
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    top_dir = os.path.abspath(os.path.join(scripts_dir, '..', '..'))
    deps_py_path = os.path.join(top_dir, 'reviewboard', 'dependencies.py')

    # Load the dependencies and organize them.
    with open(os.path.join(top_dir, 'package.json'), 'r') as fp:
        package_json = json.load(fp)

    deps: Dict[str, str] = package_json['dependencies']

    # Parse out the existing dependencies.py and grab everything outside the
    # markers.
    new_lines_pre: str = ''
    new_lines_post: str = ''

    with open(deps_py_path, 'r') as fp:
        data = fp.read()

        i = data.find(MARKER_START)
        assert i != -1

        j = data.find(MARKER_END, i)
        assert j != -1

        new_lines_pre = data[:i]
        new_lines_post = data[j + len(MARKER_END) + 1:]

    # Write out the new dependencies.py.
    with open(deps_py_path, 'w') as fp:
        fp.write(new_lines_pre)
        fp.write(f'{MARKER_START}\n\n')

        _write_deps(
            fp=fp,
            doc='Dependencies required for runtime or static media building.',
            name='runtime_npm_dependencies',
            deps=deps)

        fp.write(f'\n{MARKER_END}\n')
        fp.write(new_lines_post)


if __name__ == '__main__':
    main()
