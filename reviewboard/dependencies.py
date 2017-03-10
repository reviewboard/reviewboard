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

#: The version range required for Django.
django_version = '>=1.6.11,<1.6.999'

#: The version range required for Djblets.
djblets_version = '>=0.8.29,<=0.8.999'

#: All dependencies required to install Review Board.
package_dependencies = {
    'Django': django_version,
    'django_evolution': '>=0.7.6,<=0.7.999',
    'django-haystack': '>=2.3.1,<=2.4.999',
    'Djblets': djblets_version,
    'docutils': '',
    'markdown': '>=2.4.0,<2.4.999',
    'mimeparse': '>=0.1.3',
    'paramiko': '>=1.12',
    'pycrypto': '>=2.6',
    'Pygments': '>=2.1',
    'python-dateutil': '==1.5',
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
