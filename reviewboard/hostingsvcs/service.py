"""The base hosting service class and associated definitions.

This is pending deprecation. Consumers should update their imports to use
the classes in :py:mod:`reviewboard.hostingsvcs.base`.

It includes compatibility imports for:

.. autosummary::
   :nosignatures:

   ~reviewboard.hostingsvcs.base.client.HostingServiceClient
   ~reviewboard.hostingsvcs.base.hosting_service.BaseHostingService
   ~reviewboard.hostingsvcs.base.http.HostingServiceHTTPRequest
   ~reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse
   ~reviewboard.hostingsvcs.base.repository.RemoteRepository
"""

from __future__ import annotations

import logging
from typing import List, Optional, Type

from reviewboard.hostingsvcs.base import (
    BaseHostingService as HostingService,
    HostingServiceClient,
    HostingServiceHTTPRequest,
    HostingServiceHTTPResponse,
    hosting_service_registry)
from reviewboard.hostingsvcs.base.registry import HostingServiceRegistry


logger = logging.getLogger(__name__)


def get_hosting_services() -> List[Type[HostingService]]:
    """Return the list of hosting services.

    Returns:
        list:
        The :py:class:`~reviewboard.hostingsvcs.base.BaseHostingService`
        subclasses.
    """
    return list(hosting_service_registry)


def get_hosting_service(
    name: str,
) -> Optional[Type[HostingService]]:
    """Return the hosting service with the given name.

    If the hosting service is not found, None will be returned.

    Args:
        name (str):
            The ID of the hosting service.

    Returns:
        type:
        The hosting service class, or ``None`` if not found.
    """
    return hosting_service_registry.get_hosting_service(name)


def register_hosting_service(
    name: str,
    cls: Type[HostingService],
) -> None:
    """Register a custom hosting service class.

    A name can only be registered once. A KeyError will be thrown if attempting
    to register a second time.

    Args:
        name (str):
            The name of the hosting service.

            If the hosting service already has an ID assigned as
            :py:attr:`BaseHostingService.hosting_service_id
            <reviewboard.hostingsvcs.base.BaseHostingService.
            hosting_service_id>`, that value should be passed. Note that this
            will also override any existing ID on the service.

        cls (type):
            The hosting service class.

            This must be a subclass of
            :py:class:`~reviewboard.hostingsvcs.base.BaseHostingService`.
    """
    cls.hosting_service_id = name
    hosting_service_registry.register(cls)


def unregister_hosting_service(
    name: str,
) -> None:
    """Unregister a previously registered hosting service.

    Args:
        name (str):
            The name of the hosting service.
    """
    hosting_service_registry.unregister_by_id(name)


#: Legacy name for HostingServiceHTTPRequest
#:
#: Deprecated:
#:     4.0:
#:     This has been replaced by :py:class:`~reviewboard.hostingsvcs.
#:     base.http.HostingServiceHTTPRequest`.
URLRequest = HostingServiceHTTPRequest


__all__ = [
    'HostingService',
    'HostingServiceClient',
    'HostingServiceHTTPRequest',
    'HostingServiceHTTPResponse',
    'HostingServiceRegistry',
    'URLRequest',
    'get_hosting_service',
    'get_hosting_services',
    'register_hosting_service',
    'unregister_hosting_service',
]

__autodoc_excludes__ = [
    'HostingService',
    'HostingServiceClient',
    'HostingServiceHTTPRequest',
    'HostingServiceHTTPResponse',
    'HostingServiceRegistry',
]
