"""Build backend for Review Board extension packages.

Version Added:
    7.1
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Iterator, Optional

from setuptools import build_meta


@contextmanager
def _prepare_package_files() -> Iterator[None]:
    """Prepare files for the package.

    This will create a :file:`setup.py` if one doesn't already exist and
    ensure the extension's module can be found in the search path.

    Context:
        The package files and environment will be ready for building.
    """
    setup_py_created: bool = False

    if not os.path.exists('setup.py'):
        # There's no setup.py here, so we'll want to create one that calls
        # our version.
        #
        # This is the same approach that setuptools (at least as of v74)
        # uses. The build backend is still a wrapper around calling setup().
        setup_py_created = True

        with open('setup.py', 'w') as fp:
            fp.write(
                'from reviewboard.extensions.packaging.setuptools_backend'
                ' import setup\n'
                '\n'
                'setup()\n'
            )

    # Make sure the extension's module can be found in this directory.
    sys.path.insert(0, os.getcwd())

    try:
        yield
    finally:
        if setup_py_created:
            os.unlink('setup.py')

        sys.path.pop(0)


def build_sdist(
    sdist_directory: str,
    config_settings: Optional[dict] = None,
) -> str:
    """Build a source distribution.

    This will prepare a setup.py to run our extension-building logic, and
    then build the distribution.

    Args:
        sdist_directory (str):
            The directory where the source distribution will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated source distribution file.
    """
    with _prepare_package_files():
        return build_meta.build_sdist(sdist_directory,
                                      config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[dict] = None,
    metadata_directory: Optional[str] = None,
) -> str:
    """Build a wheel.

    This will prepare a setup.py to run our extension-building logic, and
    then build the distribution.

    Args:
        wheel_directory (str):
            The directory where the wheel will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated wheel file.
    """
    with _prepare_package_files():
        return build_meta.build_wheel(wheel_directory,
                                      config_settings,
                                      metadata_directory)


get_requires_for_build_editable = build_meta.get_requires_for_build_editable
get_requires_for_build_sdist = build_meta.get_requires_for_build_sdist
get_requires_for_build_wheel = build_meta.get_requires_for_build_wheel
build_editable = build_meta.build_editable
prepare_metadata_for_build_editable = \
    build_meta.prepare_metadata_for_build_editable
prepare_metadata_for_build_wheel = build_meta.prepare_metadata_for_build_wheel
