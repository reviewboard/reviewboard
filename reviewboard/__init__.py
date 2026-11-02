"""Review Board version and package information.

These variables and functions can be used to identify the version of
Review Board. They're largely used for packaging purposes.
"""

from __future__ import annotations

from reviewboard._version import (
    VERSION,
    __version__,
    __version_info__,
    get_package_version,
    get_version_string,
    is_release,
)


def get_manual_url():
    """Return the URL to the Review Board manual for this version."""
    if VERSION[2] == 0 and VERSION[4] != 'final':
        manual_ver = 'dev'
    else:
        manual_ver = f'{VERSION[0]}.{VERSION[1]}'

    return f'https://www.reviewboard.org/docs/manual/{manual_ver}/'


def initialize(*args, **kwargs) -> None:
    """Begin initialization of Review Board.

    This sets up the logging, generates cache serial numbers, loads extensions,
    and sets up other aspects of Review Board. Once it has finished, it will
    fire the :py:data:`reviewboard.signals.initializing` signal.

    This must be called at some point before most features will work, but it
    will be called automatically in a standard install. If you are writing
    an extension or management command, you do not need to call this yourself.

    Version Changed:
        9.0:
        * All arguments should now be passed as keyword arguments. Support for
          positional arguments is deprecated and will be removed in
          Review Board 11.

        * This now wraps :py:func:`reviewboard.process.initialize`. This
          function is still the primary way to initialize Review Board.

    Args:
        load_extensions (bool, optional):
            Whether extensions should be automatically loaded upon
            initialization. If set, extensions will only load if the site
            has been upgraded to the latest version of Review Board.

        setup_logging (bool, optional):
            Whether to set up logging based on the configured settings.
            This can be disabled if the caller has their own logging
            configuration.

        setup_templates (bool, optional):
            Whether to set up state for template rendering. This can be
            disabled if the caller has no need for template rendering of
            any kind. This does not prevent template rendering from
            happening, but may change the output of some templates.

            Keep in mind that many pieces of functionality, such as avatars
            and some management commands, may be impacted by this setting.
    """
    # NOTE: Since this is the primary method for initialization, we continue
    #       to document the arguments independently above. We pass them as
    #       *args, **kwargs so that we can benefit from
    #       @deprecate_non_keyword_only_args in the wrapped function, while
    #       importing all this lazily.
    from reviewboard.process import initialize as _initialize

    _initialize(*args, **kwargs)


def finalize_setup(
    is_upgrade: bool = False,
) -> None:
    """Internal function to upgrade internal state after installs/upgrades.

    This should only be called by Review Board install or upgrade code.

    Version Changed:
        9.0:
        * This has been moved to :py:func:`reviewboard.upgrade.finalize_setup`
          and will be removed in Review Board 11.

    Version Changed:
        5.0:
        Removed the ``register_scmtools`` argument.

    Version Added:
        4.0:

    Args:
        is_upgrade (bool, optional):
            Whether this is finalizing an upgrade, rather than a new install.
    """
    from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
    from reviewboard.upgrade import finalize_setup as _finalize_setup

    # We're avoiding decorating the methods in this module to keep side
    # effects to a minimum, so we'll explicitly log a deprecation warning
    # here.
    RemovedInReviewBoard11_0Warning.warn(
        'reviewboard.finalize_setup has been moved to '
        'reviewboard.upgrade.finalize_setup. The old function will be '
        'removed in Review Board 11.'
    )

    _finalize_setup(is_upgrade=is_upgrade)


__all__ = [
    'VERSION',
    '__version__',
    '__version_info__',
    'finalize_setup',
    'get_manual_url',
    'get_package_version',
    'get_version_string',
    'initialize',
    'is_release',
]
