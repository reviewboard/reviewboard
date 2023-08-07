"""The base hosting service class and associated definitions.

This is pending deprecation. Consumers should update their imports to use
the classes in :py:mod:`reviewboard.hostingsvcs.base`.
"""

import logging

from django.dispatch import receiver
from djblets.registries.errors import ItemLookupError

from reviewboard.hostingsvcs.base import (
    BaseHostingService as HostingService,
    HostingServiceClient,
    HostingServiceHTTPRequest,
    HostingServiceHTTPResponse,
    hosting_service_registry)
from reviewboard.hostingsvcs.base.registry import HostingServiceRegistry
from reviewboard.signals import initializing


logger = logging.getLogger(__name__)


def get_hosting_services():
    """Return the list of hosting services.

    Returns:
        list:
        The :py:class:`~reviewboard.hostingsvcs.service.HostingService`
        subclasses.
    """
    return list(hosting_service_registry)


def get_hosting_service(name):
    """Return the hosting service with the given name.

    If the hosting service is not found, None will be returned.
    """
    try:
        return hosting_service_registry.get('hosting_service_id', name)
    except ItemLookupError:
        return None


def register_hosting_service(name, cls):
    """Register a custom hosting service class.

    A name can only be registered once. A KeyError will be thrown if attempting
    to register a second time.

    Args:
        name (unicode):
            The name of the hosting service. If the hosting service already
            has an ID assigned as
            :py:attr:`~HostingService.hosting_service_id`, that value should
            be passed. Note that this will also override any existing
            ID on the service.

        cls (type):
            The hosting service class. This should be a subclass of
            :py:class:`~HostingService`.
    """
    cls.hosting_service_id = name
    hosting_service_registry.register(cls)


def unregister_hosting_service(name):
    """Unregister a previously registered hosting service.

    Args:
        name (unicode):
            The name of the hosting service.
    """
    try:
        hosting_service_registry.unregister_by_attr('hosting_service_id',
                                                    name)
    except ItemLookupError as e:
        logger.error('Failed to unregister unknown hosting service "%s"',
                     name)
        raise e


@receiver(initializing, dispatch_uid='populate_hosting_services')
def _on_initializing(**kwargs):
    hosting_service_registry.populate()


#: Legacy name for HostingServiceHTTPRequest
#:
#: Deprecated:
#:     4.0:
#:     This has been replaced by :py:class:`HostingServiceHTTPRequest`.
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
