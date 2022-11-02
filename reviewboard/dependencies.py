"""Version information for Review Board dependencies.

This contains constants that other parts of Review Board (primarily packaging)
can use to look up information on major dependencies of Review Board.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

import sys
import textwrap


#: The minimum supported version of Python.
PYTHON_MIN_VERSION = (3, 7)

#: A string representation of the minimum supported version of Python.
PYTHON_MIN_VERSION_STR = '%s.%s' % (PYTHON_MIN_VERSION)


# NOTE: This file may not import other (non-Python) modules! (Except for
#       the parent reviewboard module, which must be importable anyway). This
#       module is used for packaging and be needed before any dependencies
#       have been installed.


#: The major version of Django we're using for documentation.
django_doc_major_version = '3.2'

#: The major version of Djblets we're using for documentation.
djblets_doc_major_version = '3.x'

#: The version of Django required for the current version of Python.
django_version = '~=3.2.16'

#: The version range required for Djblets.
djblets_version = '~=3.1'

#: All dependencies required to install Review Board.
package_dependencies = {
    'bleach': '~=3.3',
    'cryptography': '>=1.8.1',
    'Django': django_version,
    'django-cors-headers': '~=3.11.0',
    'django_evolution': '~=2.2b1',
    'django-haystack': '~=3.2.1',
    'django-multiselectfield': '~=0.1.12',
    'django_oauth_toolkit': '~=1.6.3',
    'Djblets': djblets_version,
    'docutils': '',
    'markdown': '~=3.3.7',
    'mimeparse': '~=0.1.3',
    'paramiko': '>=1.12',
    'pydiffx': '~=1.1',
    'Pygments': '~=2.13',

    # TODO: We can migrate to the latest pymdown-extensions release now that
    # we're Python 3+ only.
    'pymdown-extensions': '~=6.3.0',
    'pymemcache': '',
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
}

#: Dependencies only specified during the packaging process.
#:
#: These dependencies are not used when simply developing Review Board.
#: The dependencies here are generally intended to be those that themselves
#: require Review Board.
package_only_dependencies = {
    'rbintegrations': '~=3.0.2',
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
