"""Base support for creating and using integrations.

This module provides a method for getting the integration manager used by
Review Board (:py:func:`get_integration_manager`) and a base class for defining
integrations (:py:class:`Integration`).
"""

from __future__ import unicode_literals

from djblets.integrations.integration import Integration as DjbletsIntegration
from djblets.integrations.manager import IntegrationManager


_integration_manager = None


class Integration(DjbletsIntegration):
    """Base class for an integration.

    Integrations are pluggable components that interface the application with
    a third-party service, notifying the service or triggering actions on
    certain events, or fetching data from the service. They can be registered
    by the consuming application or through extensions.

    Unlike an extension, an integration can contain multiple configurations
    active at one time. This is useful, for instance, when you want multiple,
    distinct configurations for posting messages to different channels on a
    chat service.

    There's one :py:class:`Integration` instance for each class, and it
    typically operates by responding to events and communicating with another
    service, making use of the state stored in one or more
    :py:class:`~reviewboard.integrations.models.IntegrationConfig` instances,
    which it can query. This allows hook registration and other logic to be
    shared across all configurations of an instance.

    Integrations can make use of :ref:`extension-hooks`, binding the lifecycle
    of that hook's registration to the lifecycle of that particular
    integration, making it very easy to tie an integration into any part of
    the application.
    """

    def get_configs(self, local_site):
        """Return configurations matching the given filters.

        This will return all enabled configurations for this integration
        matching the provided ``local_site``.

        The configurations can be filtered down further by the caller, based
        on the settings.

        Args:
            local_site (reviewboard.site.models.LocalSite):
                The Local Site matching any configurations. This should
                correspond to the value used for any repositories, review
                requests, reviews, etc. being used to trigger an operation,
                and should be set based on those objects.

        Returns:
            list of reviewboard.integrations.models.IntegrationConfig:
            A list of enabled integration configurations matching the query.
        """
        return super(Integration, self).get_configs(local_site=local_site)


class GetIntegrationManagerMixin(object):
    """Mixin for supplying an IntegrationManager for classes.

    This is used in any class that needs a :py:meth:`get_integration_manager`
    function.
    """

    @classmethod
    def get_integration_manager(self):
        """Return the IntegrationManager for the class.

        Returns:
            djblets.integrations.manager.IntegrationManager:
            The integration manager used in Review Board.
        """
        return get_integration_manager()


def get_integration_manager():
    """Return the integration manager for Review Board.

    Returns:
        djblets.integrations.manager.IntegrationManager:
        The integration manager used for Review Board.
    """
    global _integration_manager

    if not _integration_manager:
        from reviewboard.integrations.models import IntegrationConfig

        _integration_manager = IntegrationManager(IntegrationConfig)

    return _integration_manager
