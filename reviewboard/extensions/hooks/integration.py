"""A hook for registering new integration classes."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHookPoint
from djblets.integrations.hooks import BaseIntegrationHook

from reviewboard.integrations.base import GetIntegrationManagerMixin


class IntegrationHook(GetIntegrationManagerMixin, BaseIntegrationHook,
                      metaclass=ExtensionHookPoint):
    """A hook for registering new integration classes.

    Integrations enable Review Board to connect with third-party services in
    specialized ways. This class makes it easy to register new integrations on
    an extension, binding their lifecycles to that of the extension.
    """
