"""Python build backend for Review Board.

This is a specialization of the setuptools build backend, making the following
custom changes:

1. Including all of Review Board's dependencies as build-time dependencies.

   We execute code within Review Board as part of the build process, meaning
   that we need most (if not all) of the dependencies at build time. To play
   it safe, we simply include them all.

2. Introspecting reviewboard/dependencies.py for package metadata.

   Setuptools allows for dynamic dependencies, but only when including it
   via a requirements.txt-formatted file. We temporarily generate one of those
   for Setuptools when building the metadata.

   (Note that we have no other place to inject this, as pyproject.toml's
   dependencies, even if empty/not specified, override anything we could set
   anywhere else.)

3. Building media and i18n files.

   When building wheels or source distributions, we run our media-building
   scripts, ensuring they get included in the resulting files.

Version Added:
    7.1


Editable Installs
-----------------

By default, this build backend will pull down the latest versions of Djblets
and any other build related dependencies in order to build the package. This
is the case whether you're building a package or setting up an editable
install (:command:`pip install -e .`).

If you need to set up an editable install against in-development builds of
Djblets, Django-Pipeline, or other packages, you will need to set up symlinks
to your local packages in :file:`.local-packages/`. For example:

.. code-block:: console

   $ cd .local-packages
   $ ln -s ~/src/djblets djblets

This must match the package name as listed in the dependencies (but is
case-insensitive).


Static Media
------------

As part of packaging, this build backend will regenerate static media files. As
part of this process, it will set up symlinks to the applicable source trees in
:file:`.npm-workspaces/`.

If you are building a package out of your tree, any existing symlinks in
this directory may be overridden, pointing to packages in the temporary build
environment. Editable installs should exhibit this issue.

When you're building packages, always do so from a clean clone of the tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from setuptools import build_meta as _build_meta

from reviewboard.dependencies import (build_dependency_list,
                                      package_dependencies,
                                      package_only_dependencies)

if TYPE_CHECKING:
    from setuptools.build_meta import _ConfigSettings


LOCAL_PACKAGES_DIR = '.local-packages'


def get_requires_for_build_editable(
    config_settings: (_ConfigSettings | None) = None,
) -> list[str]:
    """Return build-time requirements for editable builds.

    This will return the standard Review Board dependencies, along with any
    pyproject-specified build-time dependencies.

    If any local dependencies are found in the :file:`.local-packages`
    directory at the root of the tree, they will be used instead of
    downloading from PyPI.

    Args:
        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        list of str:
        The list of build-time dependencies.
    """
    _write_dependencies()

    local_paths: dict[str, str] = {}

    if os.path.exists(LOCAL_PACKAGES_DIR):
        for name in os.listdir(LOCAL_PACKAGES_DIR):
            local_paths[name.lower()] = os.path.abspath(
                os.readlink(os.path.join(LOCAL_PACKAGES_DIR, name)))

    dependencies = build_dependency_list(
        package_dependencies,
        local_packages=local_paths)

    return [
        *dependencies,
        *_build_meta.get_requires_for_build_wheel(config_settings)
    ]


def get_requires_for_build_sdist(
    config_settings: (_ConfigSettings | None) = None,
) -> list[str]:
    """Return build-time requirements for source distributions.

    This will return the standard Review Board dependencies, along with any
    pyproject-specified build-time dependencies.

    Args:
        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        list of str:
        The list of build-time dependencies.
    """
    _write_dependencies()

    return [
        *build_dependency_list(package_dependencies),
        *_build_meta.get_requires_for_build_wheel(config_settings)
    ]


def get_requires_for_build_wheel(
    config_settings: (_ConfigSettings | None) = None,
) -> list[str]:
    """Return build-time requirements for wheel distributions.

    This will return the standard Review Board dependencies, along with any
    pyproject-specified build-time dependencies.

    Args:
        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        list of str:
        The list of build-time dependencies.
    """
    _write_dependencies()

    return [
        *build_dependency_list(package_dependencies),
        *_build_meta.get_requires_for_build_wheel(config_settings)
    ]


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: (_ConfigSettings | None) = None,
) -> str:
    """Prepare metadata for an editable build.

    This will write out Review Board's dependencies to a temporary file so
    that pyproject.toml can locate it.

    Args:
        metadata_directory (str):
            The target directory for metadata.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated ``.dist-info`` directory.
    """
    _write_dependencies()

    return _build_meta.prepare_metadata_for_build_editable(
        metadata_directory,
        config_settings)


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: (_ConfigSettings | None) = None,
) -> str:
    """Prepare metadata for a wheel distribution.

    This will write out Review Board's dependencies to a temporary file so
    that pyproject.toml can locate it.

    Args:
        metadata_directory (str):
            The target directory for metadata.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated ``.dist-info`` directory.
    """
    _rebuild_npm_workspaces()
    _install_npm_packages()
    _write_dependencies()

    return _build_meta.prepare_metadata_for_build_wheel(
        metadata_directory,
        config_settings)


def build_editable(
    wheel_directory: str,
    config_settings: (_ConfigSettings | None) = None,
    metadata_directory: (str | None) = None,
) -> str:
    """Build an editable environment.

    This will build the static media and i18n files needed by Djblets, and
    then let Setuptools build the editable environment.

    Args:
        wheel_directory (str):
            The directory where the editable wheel will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

        metadata_directory (str, optional):
            The directory where metadata would be stored.

    Returns:
        str:
        The basename for the generated source distribution file.
    """
    _rebuild_npm_workspaces()
    _install_npm_packages()

    return _build_meta.build_editable(
        wheel_directory,
        {
            'editable_mode': 'compat',
            **(config_settings or {})
        },
        metadata_directory)


def build_sdist(
    sdist_directory: str,
    config_settings: (_ConfigSettings | None) = None,
) -> str:
    """Build a source distribution.

    This will build the static media and i18n files needed by Review Board,
    and then let Setuptools build the distribution.

    Args:
        sdist_directory (str):
            The directory where the source distribution will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated source distribution file.
    """
    _rebuild_npm_workspaces()
    _install_npm_packages()
    _build_data_files()

    return _build_meta.build_sdist(sdist_directory,
                                   config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: (_ConfigSettings | None) = None,
    metadata_directory: (str | None) = None,
) -> str:
    """Build a wheel.

    This will build the static media and i18n files needed by Review Board,
    and then let Setuptools build the distribution.

    Args:
        wheel_directory (str):
            The directory where the wheel will be placed.

        config_settings (dict, optional):
            Configuration settings to pass to Setuptools.

    Returns:
        str:
        The basename for the generated wheel file.
    """
    _rebuild_npm_workspaces()
    _install_npm_packages()
    _build_data_files()

    return _build_meta.build_wheel(wheel_directory,
                                   config_settings,
                                   metadata_directory)


def _rebuild_npm_workspaces() -> None:
    """Rebuild the links under .npm-workspaces for static media building.

    This will look up the module paths for Djblets and Review Board and
    link them so that JavaScript and CSS build infrastructure can import
    files correctly.
    """
    root_dir = os.path.abspath(os.path.join(__file__, '..'))
    npm_workspaces_dir = os.path.join(root_dir, '.npm-workspaces')

    if not os.path.exists(npm_workspaces_dir):
        os.mkdir(npm_workspaces_dir, 0o755)

    from importlib import import_module

    for mod_name in ['djblets']:
        try:
            mod = import_module(mod_name)
        except ImportError:
            raise RuntimeError(
                f'Missing the dependency for {mod_name}, which is needed to '
                f'compile static media.'
            )

        mod_path = mod.__file__
        assert mod_path

        symlink_path = os.path.join(npm_workspaces_dir, mod_name)

        # Unlink this unconditionally, so we don't have to worry about things
        # like an existing dangling symlink that shows as non-existent.
        try:
            os.unlink(symlink_path)
        except FileNotFoundError:
            pass

        os.symlink(os.path.dirname(mod_path), symlink_path)


def _install_npm_packages() -> None:
    """Install NPM packages.

    Raises:
        RuntimeError:
            There was an error installing npm packages.
    """
    try:
        subprocess.run(['npm', 'install'],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT,
                       check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'Failed to install npm packages: {e.output}')


def _write_dependencies() -> None:
    """Write all dependencies to a file.

    This will write to :file:`package-requirements.txt`, so that
    :file:`pyproject.toml` can reference it.
    """
    dependencies = build_dependency_list({
        **package_dependencies,
        **package_only_dependencies,
    })

    with open('package-requirements.txt', 'w', encoding='utf-8') as fp:
        for dependency in dependencies:
            fp.write(f'{dependency}\n')


def _build_data_files() -> None:
    """Build static media and i18n data files.

    Raises:
        RuntimeError:
            There was an error building the media or i18n files.
    """
    # Build the static media.
    try:
        subprocess.check_call(
            [
                sys.executable,
                os.path.join('contrib', 'internal', 'build-media.py'),
            ])
    except subprocess.CalledProcessError:
        raise RuntimeError('Failed to build media files')

    # Build the i18n files.
    try:
        subprocess.check_call([
            sys.executable,
            os.path.join('contrib', 'internal', 'build-i18n.py'),
        ])
    except subprocess.CalledProcessError:
        raise RuntimeError('Failed to build i18n files')
