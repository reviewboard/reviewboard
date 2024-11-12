"""Packaging support for Review Board extensions.

Version Changed:
    7.1:
    This has been split into sub-modules: Consumers should update any older
    imports for this module to instead import from
    :py:mod:`reviewboard.extensions.packaging.setuptools_backend` or
    :py:mod:`reviewboard.extensions.packaging.static_media`.
"""

# NOTE: It's important not to import anything directly in this module that
#       depends on a configured Django environment.

from __future__ import annotations

from housekeeping import ClassMovedMixin, func_moved

from reviewboard.deprecation import RemovedInReviewBoard90Warning
import reviewboard.extensions.packaging.setuptools_backend as \
    setuptools_backend
import reviewboard.extensions.packaging.static_media as static_media


class RBStaticMediaBuildContext(ClassMovedMixin,
                                static_media.RBStaticMediaBuildContext,
                                warning_cls=RemovedInReviewBoard90Warning):
    """Context for performing a static media build for an extension.

    This will set up some default NPM workspace paths needed for building
    Review Board extensions.

    Deprecated:
        7.1:
        This has been moved to :py:class:`reviewboard.extensions.packaging.
        setuptools_backend.RBStaticMediaBuildContext`. The legacy import will
        be removed in Review Board 9.

    Version Added:
        7.0
    """


class RBStaticMediaBuilder(ClassMovedMixin,
                           static_media.RBStaticMediaBuilder,
                           warning_cls=RemovedInReviewBoard90Warning):
    """Static media builder for Review Board extensions.

    This will take care of building static media files. As part of this, it
    will set up Babel, Rollup, and TypeScript configuration files needed to
    compile against Review Board JavaScript/TypeScript modules.

    Deprecated:
        7.1:
        This has been moved to :py:class:`reviewboard.extensions.packaging.
        setuptools_backend.RBStaticMediaBuilder`. The legacy import will be
        removed in Review Board 9.

    Version Added:
        7.0
    """


class BuildStaticFiles(ClassMovedMixin,
                       setuptools_backend.BuildStaticFiles,
                       warning_cls=RemovedInReviewBoard90Warning):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through LessCSS (if using :file:`.less` files), minified and versioned.

    Deprecated:
        7.1:
        This has been moved to :py:class:`reviewboard.extensions.packaging.
        setuptools_backend.RBStaticMediaBuilder`. The legacy import will be
        removed in Review Board 9.

    Version Added:
        7.0
    """


@func_moved(RemovedInReviewBoard90Warning,
            new_func=setuptools_backend.setup)
def setup(**setup_kwargs):
    """Build an extension package.

    Deprecated:
        7.1:
        This has been moved to :py:class:`reviewboard.extensions.packaging.
        setuptools_backend.setup`. The legacy import will be removed in
        Review Board 9.

    Args:
        **setup_kwargs (dict):
            Keyword arguments to pass to the main setup method.
    """
    return setuptools_backend.setup(**setup_kwargs)
