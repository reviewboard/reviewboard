"""Top-level signals for initialization and settings changes."""

from __future__ import unicode_literals

import warnings

from django.dispatch import Signal
from djblets.deprecation import deprecated_arg_value

from reviewboard.deprecation import RemovedInReviewBoard40Warning


#: Emitted when the initialization of Review Board is complete.
#:
#: This will emit any time a process or thread has finished initializing,
#: and is ready to serve requests.
initializing = Signal()

#: Emitted when site settings have been loaded.
#:
#: Any time there are new settings saved or loaded, this will emit. Consumers
#: can listen and update their own state based on the new settings.
site_settings_loaded = Signal()


def deprecated_signal_argument(signal_name, old_name, new_name, value):
    """Wrap a signal argument in a lazy object to warn when treated as unicode.

    Args:
        signal_name (unicode):
            The name of the signal.

        old_name (unicode):
            The name of the signal argument that was deprecated.

        new_name (unicode):
            The name of the signal argument to use in the deprecated argument's
            place.

        value (object):
            The corresponding value.

    Returns:
        django.utils.functional.SimpleLazyObject:
        The value wrapped in a lazy object. The first time it is casted as
        :py:class:`unicode` a warning will be emitted.
    """
    warnings.warn('deprecated_signal_argument has been deprecated and will '
                  'be removed in Review Board 4.0. Use '
                  'djblets.deprecation.deprecated_arg_value instead.',
                  RemovedInReviewBoard40Warning)

    return deprecated_arg_value(owner_name=signal_name,
                                old_arg_name=old_name,
                                new_arg_name=new_name,
                                value=value,
                                warning_cls=RemovedInReviewBoard40Warning)
