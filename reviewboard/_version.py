"""Review Board version information.

Version Added:
    8.0:
    Moved this code from :file:`reviewboard/__init__.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeAlias

    #: Type for version tuples.
    #:
    #: Version Added:
    #:     8.0
    _Version: TypeAlias = tuple[int, int, int, int, str, int, bool]


#: The version of Review Board.
#:
#: This is in the format of:
#:
#: (Major, Minor, Micro, Patch, alpha/beta/rc/final, Release Number, Released)
#:
VERSION: _Version = (9, 0, 0, 0, 'alpha', 0, False)


def get_version_string() -> str:
    """Return the Review Board version as a human-readable string.

    Returns:
        str:
        The Review Board version.
    """
    major, minor, micro, patch, tag, release_num, is_release = VERSION
    version = f'{major}.{minor}'

    if micro or patch:
        version += f'.{micro}'

    if patch:
        version += f'.{patch}'

    if tag != 'final':
        if tag == 'rc':
            version += f' RC{release_num}'
        else:
            version += f' {tag} {release_num}'

    if not is_release:
        version += ' (dev)'

    return version


def get_package_version() -> str:
    """Return the Review Board version as a Python package version string.

    Returns:
        str:
        The Review Board package version.
    """
    major, minor, micro, patch, tag, release_num = VERSION[:6]

    version = f'{major}.{minor}'

    if micro or patch:
        version += f'.{micro}'

    if patch:
        version += f'.{patch}'

    if tag != 'final':
        if tag == 'alpha':
            tag = 'a'
        elif tag == 'beta':
            tag = 'b'

        version += f'{tag}{release_num}'

    return version


def is_release() -> bool:
    """Return whether this is a released version of Review Board.

    Returns:
        bool:
        ``True`` if this is an official release.
    """
    return VERSION[6]


#: An alias for the the version information from :py:data:`VERSION`.
#:
#: This does not include the last entry in the tuple (the released state).
__version_info__ = VERSION[:-1]


#: An alias for the version used for the Python package.
__version__ = get_package_version()
