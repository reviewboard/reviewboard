"""Integrations support for Review Board.

This module provides the Review Board functionality needed to create
integrations for third-party services. It builds upon Djblets's integrations
foundation, offering some additional utilities for more easily creating
manageable integrations.

The functions and classes used in this module are deprecated. Consumers should
use the versions in :py:mod:`reviewboard.integrations.base` instead.
"""

from __future__ import unicode_literals

from django.utils import six

from reviewboard.deprecation import RemovedInReviewBoard50Warning


def get_integration_manager():
    """Return the integrations manager.

    Deprecated:
        4.0:
        This has been deprecated in favor of
        :py:func:`reviewboard.integrations.base.get_integration_manager`.

    Returns:
        djblets.integrations.manager.IntegrationManager:
        The Review Board integrations manager.
    """
    from reviewboard.integrations.base import (get_integration_manager as
                                               _get_integration_manager)

    RemovedInReviewBoard50Warning.warn(
        'reviewboard.integrations.get_integration_manager() is deprecated. '
        'Use reviewboard.integrations.base.get_integration_manager() instead.')

    return _get_integration_manager()


class _ProxyIntegrationMetaClass(type):
    """Metaclass for a deprecated forwarding Integration class.

    This is used along with :py:class:`Integration` to allow older code
    that subclasses :py:class:`reviewboard.integrations.Integration` to
    instead automatically subclass
    :py:class:`reviewboard.integrations.base.Integration`, emitting a warning
    in the process to notify authors to update their code.
    """

    def __new__(cls, name, bases, d):
        """Create the subclass of an integration.

        Args:
            name (str):
                The name of the integration subclass.

            bases (tuple):
                The parent classes.

            d (dict):
                The class dictionary.

        Returns:
            type:
            The new class.
        """
        if bases != (object,):
            # This is a subclass of Integration.
            from reviewboard.integrations.base import (Integration as
                                                       BaseIntegration)

            RemovedInReviewBoard50Warning.warn(
                'reviewboard.integrations.Integration is deprecated. %s '
                'should inherit from reviewboard.integrations.base.'
                'Integration instead.'
                % name)

            new_bases = []

            for base in bases:
                if base is Integration:
                    new_bases.append(BaseIntegration)
                else:
                    new_bases.append(base)

            bases = tuple(new_bases)

        return type.__new__(cls, name, bases, d)


@six.add_metaclass(_ProxyIntegrationMetaClass)
class Integration(object):
    """Base class for an integration.

    Deprecated:
        4.0:
        Subclasses should inherit from
        :py:class:`reviewboard.integrations.base.Integration` instead.
    """
