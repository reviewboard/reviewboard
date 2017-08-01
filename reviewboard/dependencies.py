"""Version information for Review Board dependencies.

This contains constants that other parts of Review Board (primarily packaging)
can use to look up information on major dependencies of Review Board.

The contents in this file might change substantially between releases. If
you're going to make use of data from this file, code defensively.
"""

from __future__ import unicode_literals

# NOTE: This file may not import other files! It's used for packaging and
#       may be needed before any dependencies have been installed.


#: The major version of Django we're using for documentation.
django_doc_major_version = '1.6'

#: The major version of Djblets we're using for documentation.
djblets_doc_major_version = '0.9'

#: The version range required for Django.
django_version = '>=1.6.11,<1.6.999'

#: The version range required for Djblets.
djblets_version = '>=0.9.9,<=0.9.999'

#: All dependencies required to install Review Board.
package_dependencies = {
    'cryptography': '>=1.8.1',
    'Django': django_version,
    'django_evolution': '>=0.7.7,<=0.7.999',
    'django-haystack': '>=2.3.1,<=2.4.999',
    'django-multiselectfield': '',
    'Djblets': djblets_version,
    'docutils': '',
    'markdown': '>=2.4.0,<2.4.999',
    'mimeparse': '>=0.1.3',
    'paramiko': '>=1.12',
    'Pygments': '>=2.1',
    'python-dateutil': '>=1.5',
    'python-memcached': '',
    'pytz': '>=2015.2',
    'recaptcha-client': '',
    'Whoosh': '>=2.6',
}


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
    return sorted(
        [
            '%s%s%s' % (dep_name, version_prefix, dep_version)
            for dep_name, dep_version in deps.items()
        ],
        key=lambda s: s.lower())
