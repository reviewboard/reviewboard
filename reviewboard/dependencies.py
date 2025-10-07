"""Version information for Review Board dependencies.

This contains constants that other parts of Review Board (primarily packaging)
can use to look up information on major dependencies of Review Board.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

from __future__ import annotations

import sys
import textwrap
from typing import TYPE_CHECKING

try:
    from djblets.dependencies import (
        npm_dependencies as djblets_npm_dependencies,
    )
except ImportError:
    # We're probably being called as part of the build backend process.
    # Don't worry too much about this dependency.
    djblets_npm_dependencies = []

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


###########################################################################
# Python and Django compatibility
###########################################################################

#: The minimum supported version of Python.
PYTHON_MIN_VERSION = (3, 8)

#: A string representation of the minimum supported version of Python.
PYTHON_MIN_VERSION_STR = '%s.%s' % (PYTHON_MIN_VERSION)


# NOTE: This file may not import other (non-Python) modules! (Except for
#       the parent reviewboard module, which must be importable anyway). This
#       module is used for packaging and be needed before any dependencies
#       have been installed.


#: The major version of Django we're using for documentation.
django_doc_major_version = '4.2'

#: The major version of Djblets we're using for documentation.
djblets_doc_major_version = '5.x'

#: The version of Django required for the current version of Python.
django_version = '~=4.2.23'

#: The version range required for Djblets.
djblets_version = '~=5.3.0a0.dev0'


###########################################################################
# Python dependencies
###########################################################################

#: All dependencies required to install Review Board.
package_dependencies = {
    'bleach': '~=6.0.0',
    'cryptography': '~=41.0.7',
    'Django': django_version,
    'django-cors-headers': '~=3.11.0',
    'django_evolution': '~=2.4.2',
    'django-haystack': '~=3.2.1',
    'django_oauth_toolkit': '~=1.6.3',
    'django-storages': '~=1.14.2',
    'Djblets': djblets_version,
    'docutils': '',
    'markdown': '~=3.3.7',
    'mimeparse': '~=0.1.3',
    'packaging': '>=23.1',
    'paramiko': '~=3.4.1',
    'pydantic': '~=2.5',
    'pydiffx': '~=1.1',
    'Pygments': '~=2.19.0',

    # While we don't directly use pyOpenSSL, we do use cryptography, and
    # older versions of pyOpenSSL can break a system badly with newer
    # cryptography (impacting pip as well). So we pin a compatible version.
    #
    # This must match cryptography compatibility.
    'pyOpenSSL': '~=23.2.0',

    # TODO: We can migrate to the latest pymdown-extensions release now that
    # we're Python 3+ only.
    'pymdown-extensions': '~=6.3.0',
    'pymemcache': '',
    'pytz': '>=2015.2',
    'tqdm': '~=4.66.2',
    'Whoosh': '>=2.6',

    # The following are pinned versions/ranges needed to satisfy dependency
    # conflicts between multiple projects. We are not using these directly.
    # These should be removed in future versions of Review Board as
    # dependencies change.

    # django-oauth-toolkit dependencies:
    'django-braces': '==1.13.0',
}

#: Dependencies only specified during the packaging process.
#:
#: These dependencies are not used when simply developing Review Board.
#: The dependencies here are generally intended to be those that themselves
#: require Review Board.
package_only_dependencies = {
    'rbintegrations': '~=4.0.2',
}


###########################################################################
# JavaScript dependencies
#
# These are auto-generated when running `npm install --save ...` (if the
# package is not already in node_modules).
#
# To re-generate manually, run: `./contrib/internal/build-npm-deps.py`.
###########################################################################

# Auto-generated Node.js dependencies {


#: Dependencies required for runtime or static media building.
runtime_npm_dependencies: Mapping[str, str] = {
    '@beanbag/djblets': '*',
    '@prantlf/jsonlint': '^16.0.0',
    '@tabler/icons': '^3.35.0',
    'codemirror': '^5.65.20',
    'core-js': '^3.46.0',
    'jquery-flot': '^0.8.3',
    'jquery-form': '^4.3.0',
    'jquery.cookie': '^1.4.1',
    'masonry-layout': '^4.2.2',
    'moment': '^2.30.1',
    'moment-timezone': '^0.6.0',
}


# } Auto-generated Node.js dependencies


#: Node dependencies required to package/develop/test Djblets.
npm_dependencies: dict[str, str] = {}
npm_dependencies.update(djblets_npm_dependencies)
npm_dependencies.update(runtime_npm_dependencies)


###########################################################################
# Packaging utilities
###########################################################################
_dependency_error_count = 0
_dependency_warning_count = 0


def build_dependency_list(
    deps: Mapping[str, (str | Sequence[Mapping[str, str]])],
    version_prefix: str = '',
    *,
    local_packages: Mapping[str, str] = {},
) -> Sequence[str]:
    """Build a list of dependency specifiers from a dependency map.

    This can be used along with :py:data:`package_dependencies`,
    :py:data:`npm_dependencies`, or other dependency dictionaries to build a
    list of dependency specifiers for use on the command line or in the
    package build backend.

    Version Changed:
        7.1:
        * Added the ``local_packages`` argument.

    Args:
        deps (dict):
            A dictionary of dependencies.

        version_prefix (str, optional):
            A prefix to include before any package versions.

        local_packages (dict, optional):
            A mapping of dependency names to local paths where they could
            be found.

            Version Added:
                7.1

    Returns:
        list of str:
        A list of dependency specifiers.
    """
    new_deps: list[str] = []

    for dep_name, dep_details in deps.items():
        lower_dep_name = dep_name.lower()

        if lower_dep_name in local_packages:
            package_path = local_packages[lower_dep_name]
            new_deps.append(f'{dep_name} @ file://{package_path}')
        elif isinstance(dep_details, list):
            new_deps += [
                '%s%s%s; python_version%s'
                % (dep_name, version_prefix, entry['version'], entry['python'])
                for entry in dep_details
            ]
        else:
            new_deps.append('%s%s%s' % (dep_name, version_prefix, dep_details))

    return sorted(new_deps, key=lambda s: s.lower())


def _dependency_message(
    message: str,
    prefix: str = '',
) -> None:
    """Utility function to print and track a dependency-related message.

    This will track that a message was printed, allowing us to determine if
    any messages were shown to the user.

    Args:
        message (str):
            The dependency-related message to display. This will be wrapped,
            but long strings (like paths) will not contain line breaks.

        prefix (str, optional):
            The prefix for the message. All text will be aligned after this.
    """
    wrapped = textwrap.fill(
        message,
        initial_indent=prefix,
        subsequent_indent=' ' * len(prefix),
        break_long_words=False,
        break_on_hyphens=False)
    sys.stderr.write(f'\n{wrapped}\n')


def dependency_error(
    message: str,
) -> None:
    """Print a dependency error.

    This will track that a message was printed, allowing us to determine if
    any messages were shown to the user.

    Args:
        message (str):
            The dependency error to display. This will be wrapped, but long
            strings (like paths) will not contain line breaks.
    """
    global _dependency_error_count

    _dependency_message(message, prefix='ERROR: ')
    _dependency_error_count += 1


def dependency_warning(
    message: str,
) -> None:
    """Print a dependency warning.

    This will track that a message was printed, allowing us to determine if
    any messages were shown to the user.

    Args:
        message (str):
            The dependency warning to display. This will be wrapped, but long
            strings (like paths) will not contain line breaks.
    """
    global _dependency_warning_count

    _dependency_message(message, prefix='WARNING: ')
    _dependency_warning_count += 1


def fail_if_missing_dependencies() -> None:
    """Exit the process with an error if dependency messages were shown.

    If :py:func:`dependency_error` or :py:func:`dependency_warning` were
    called, this will print some help information with a link to the manual
    and then exit the process.
    """
    if _dependency_warning_count > 0 or _dependency_error_count > 0:
        from reviewboard import get_manual_url

        manual_url = get_manual_url()
        _dependency_message(
            f'Please see {manual_url} for help setting up Review Board.')

        if _dependency_error_count > 0:
            sys.exit(1)
