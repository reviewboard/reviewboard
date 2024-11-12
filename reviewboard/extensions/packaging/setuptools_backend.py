"""Setuptools backend for building Review Board extension packages.

Version Added:
    7.1:
    This moved from the top-level :py:mod:`reviewboard.packaging`.
"""

from __future__ import annotations

import os
import sys

from djblets.extensions.packaging.setuptools_backend import (
    BuildStaticFiles as DjbletsBuildStaticFiles,
    build_extension_cmdclass,
)
from setuptools import setup as setuptools_setup

from reviewboard.extensions.packaging.static_media import (
    RBStaticMediaBuilder,
    RBStaticMediaBuildContext,
)


class BuildStaticFiles(DjbletsBuildStaticFiles):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through LessCSS (if using :file:`.less` files), minified and versioned.

    Version Changed:
        7.1:
        This moved from :py:mod:`reviewboard.extensions.packaging`.
    """

    extension_entrypoint_group = 'reviewboard.extensions'
    django_settings_module = 'reviewboard.settings'
    static_media_builder_cls = RBStaticMediaBuilder
    static_media_build_context_cls = RBStaticMediaBuildContext


def setup(**setup_kwargs):
    """Build an extension package.

    Version Changed:
        7.1:
        This moved from :py:mod:`reviewboard.extensions.packaging`.

    Args:
        **setup_kwargs (dict):
            Keyword arguments to pass to the main setup method.
    """
    # Add the included conf directory so that there's a settings_local.py
    # file that can be used to package the static media.
    extensions_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, os.path.join(extensions_dir, 'conf'))

    os.environ[str('FORCE_BUILD_MEDIA')] = str('1')

    setup_kwargs.update({
        'zip_safe': False,
        'include_package_data': True,
        'cmdclass': dict(
            build_extension_cmdclass(build_static_files_cls=BuildStaticFiles),
            **setup_kwargs.get('cmdclass', {})),
    })

    setuptools_setup(**setup_kwargs)
