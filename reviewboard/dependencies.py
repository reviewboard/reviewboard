"""Version information for Review Board dependencies.

This contains constants that other parts of Review Board (primarily packaging)
can use to look up information on major dependencies of Review Board.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

from __future__ import unicode_literals

import sys
import textwrap


#: The minimum supported version of Python 2.x.
PYTHON_2_MIN_VERSION = (2, 7)

#: The minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION = (3, 6)

#: A string representation of the minimum supported version of Python 2.x.
PYTHON_2_MIN_VERSION_STR = '%s.%s' % (PYTHON_2_MIN_VERSION)

#: A string representation of the minimum supported version of Python 3.x.
PYTHON_3_MIN_VERSION_STR = '%s.%s' % (PYTHON_3_MIN_VERSION)

#: A dependency version range for Python 2.x.
PYTHON_2_RANGE = "=='%s.*'" % PYTHON_2_MIN_VERSION_STR

#: A dependency version range for Python 3.x.
PYTHON_3_RANGE = ">='%s'" % PYTHON_3_MIN_VERSION_STR


# NOTE: This file may not import other (non-Python) modules! (Except for
#       the parent reviewboard module, which must be importable anyway). This
#       module is used for packaging and be needed before any dependencies
#       have been installed.


#: The major version of Django we're using for documentation.
django_doc_major_version = '1.11'

#: The major version of Djblets we're using for documentation.
djblets_doc_major_version = '2.x'

#: The version of Django required for the current version of Python.
django_version = '>=1.11.29,<1.11.999'

#: The version range required for Djblets.
djblets_version = '>=2.2,<=2.999'

#: All dependencies required to install Review Board.
package_dependencies = {
    'bleach': '>=3.3',
    'cryptography': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=1.8.1,<3.3.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=1.8.1',
        },
    ],
    'Django': django_version,
    'django-cors-headers': '>=1.1.0,<1.1.999',
    'django_evolution': '>=2.1,<2.999',
    'django-haystack': '>=2.8.1,<2.999',
    'django-multiselectfield': '',
    'django-oauth-toolkit': '>=0.9.0,<0.9.999',
    'Djblets': djblets_version,
    'docutils': '',
    'elasticsearch': '>=2.4.1,<2.999',

    # Markdown 3.2 dropped support for Python 2.
    'markdown': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=3.1.1,<3.1.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=3.3.3',
        },
    ],

    'mimeparse': '>=0.1.3',
    'paramiko': '>=1.12',
    'Pygments': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=2.1,<=2.5.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=2.1',
        },
    ],

    # To keep behavior consistent between Python 2 and 3 installs, we're
    # sticking with the pymdown-extensions 6.x range. At the time of this
    # writing (November 14, 2020), the latest version is 8.0.1, and 6.3+
    # all require Python-Markdown 3.2+, which requires Python 3.
    #
    # Once we drop Python 2 support, we can migrate to the latest
    # pymdown-extensions release.
    'pymdown-extensions': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=6.2,<6.2.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=6.3,<6.3.999',
        },
    ],
    'python-memcached': '',
    'pytz': '>=2015.2',
    'Whoosh': '>=2.6',

    # The following are pinned versions/ranges needed to satisfy dependency
    # conflicts between multiple projects. We are not using these directly.
    # These should be removed in future versions of Review Board as
    # dependencies change.

    # asana dependencies:
    'requests-oauthlib': '>=0.8,<=1.0',

    # django-oauth-toolkit dependencies:
    'django-braces': '==1.13.0',
    'oauthlib': '==1.0.1',

    # cryptography and paramiko dependencies:
    'bcrypt': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=3.1.7,<3.1.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=3.1.7',
        },
    ],

    # setuptools and other modules need pyparsing, but 3.0+ won't support
    # Python 2.7.
    'pyparsing': [
        {
            'python': PYTHON_2_RANGE,
            'version': '>=2.4,<2.4.999',
        },
        {
            'python': PYTHON_3_RANGE,
            'version': '>=2.4',
        }
    ],
}

#: Dependencies only specified during the packaging process.
#:
#: These dependencies are not used when simply developing Review Board.
#: The dependencies here are generally intended to be those that themselves
#: require Review Board.
package_only_dependencies = {
    'rbintegrations': '>=2.0,<2.0.999',
}


_dependency_error_count = 0
_dependency_warning_count = 0


def build_dependency_list(deps, version_prefix=''):
    """Build a list of dependency specifiers from a dependency map.

    This can be used along with :py:data:`package_dependencies`,
    :py:data:`npm_dependencies`, or other dependency dictionaries to build a
    list of dependency specifiers for use on the command line or in
    :file:`setup.py`.

    Args:
        deps (dict):
            A dictionary of dependencies.

    Returns:
        list of unicode:
        A list of dependency specifiers.
    """
    new_deps = []

    for dep_name, dep_details in deps.items():
        if isinstance(dep_details, list):
            new_deps += [
                '%s%s%s; python_version%s'
                % (dep_name, version_prefix, entry['version'], entry['python'])
                for entry in dep_details
            ]
        else:
            new_deps.append('%s%s%s' % (dep_name, version_prefix, dep_details))

    return sorted(new_deps, key=lambda s: s.lower())


def _dependency_message(message, prefix=''):
    """Utility function to print and track a dependency-related message.

    This will track that a message was printed, allowing us to determine if
    any messages were shown to the user.

    Args:
        message (unicode):
            The dependency-related message to display. This will be wrapped,
            but long strings (like paths) will not contain line breaks.

        prefix (unicode, optional):
            The prefix for the message. All text will be aligned after this.
    """
    sys.stderr.write('\n%s\n'
                     % textwrap.fill(message,
                                     initial_indent=prefix,
                                     subsequent_indent=' ' * len(prefix),
                                     break_long_words=False,
                                     break_on_hyphens=False))


def dependency_error(message):
    """Print a dependency error.

    This will track that a message was printed, allowing us to determine if
    any messages were shown to the user.

    Args:
        message (unicode):
            The dependency error to display. This will be wrapped, but long
            strings (like paths) will not contain line breaks.
    """
    global _dependency_error_count

    _dependency_message(message, prefix='ERROR: ')
    _dependency_error_count += 1


def dependency_warning(message):
    """Print a dependency warning.

    This will track that a message was printed, allowing us to determine if
    any messages were shown to the user.

    Args:
        message (unicode):
            The dependency warning to display. This will be wrapped, but long
            strings (like paths) will not contain line breaks.
    """
    global _dependency_warning_count

    _dependency_message(message, prefix='WARNING: ')
    _dependency_warning_count += 1


def fail_if_missing_dependencies():
    """Exit the process with an error if dependency messages were shown.

    If :py:func:`dependency_error` or :py:func:`dependency_warning` were
    called, this will print some help information with a link to the manual
    and then exit the process.
    """
    if _dependency_warning_count > 0 or _dependency_error_count > 0:
        from reviewboard import get_manual_url

        _dependency_message('Please see %s for help setting up Review Board.'
                            % get_manual_url())

        if _dependency_error_count > 0:
            sys.exit(1)
