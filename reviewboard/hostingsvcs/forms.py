"""The base hosting service class and associated definitions.

This is pending deprecation. Consumers should update their imports to use
the classes in :py:mod:`reviewboard.hostingsvcs.base.forms`.
"""

from reviewboard.hostingsvcs.base.forms import (HostingServiceAuthForm,
                                                HostingServiceForm)


__all__ = [
    'HostingServiceAuthForm',
    'HostingServiceForm',
]
