"""Top-level signals for initialization and settings changes."""

from __future__ import unicode_literals

import warnings

from django.dispatch import Signal
from django.utils.functional import SimpleLazyObject

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
    def warn_on_use():
        warnings.warn('The "%s" signal argument for "%s" has been deprecated '
                      'and will be removed in a future version; use "%s" '
                      'instead.'
                      % (old_name, signal_name, new_name),
                      DeprecationWarning)
        return value

    return SimpleLazyObject(warn_on_use)
