"""A hook for registering a hosting service."""

from __future__ import annotations

from django.utils.translation import gettext as _
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

from reviewboard.hostingsvcs.base import hosting_service_registry


class HostingServiceHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for registering a hosting service."""

    def initialize(self, service_cls):
        """Initialize the hook.

        This will register the hosting service.

        Args:
            service_cls (type):
                The hosting service class to register. This must be a
                subclass of :py:class:`~reviewboard.hostingsvcs.base.
                hosting_service.BaseHostingService`.

        Raises:
            ValueError:
                The service's :py:attr:`~reviewboard.hostingsvcs.base.
                .hosting_service.BaseHostingService.hosting_service_id`
                attribute was not set.
        """
        hosting_service_id = service_cls.hosting_service_id

        if hosting_service_id is None:
            raise ValueError(_('%s.hosting_service_id must be set.')
                             % (service_cls.__name__))

        self.hosting_service_id = hosting_service_id
        hosting_service_registry.register(service_cls)

    def shutdown(self):
        """Shut down the hook.

        This will unregister the hosting service.
        """
        hosting_service_registry.unregister_by_id(self.hosting_service_id)
