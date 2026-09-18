"""A hook for registering a single sign-on backend.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint

from reviewboard.accounts.sso.backends import sso_backends

if TYPE_CHECKING:
    from reviewboard.accounts.sso.backends.base import BaseSSOBackend


class SSOBackendHook(BaseRegistryHook, metaclass=ExtensionHookPoint):
    """A hook for registering a single sign-on backend.

    SSO backends let users log in through an external identity provider.
    The backend's URLs are made available under
    ``/account/sso/<backend_id>/``, and a login button for the backend is
    shown on the login page while the backend is enabled.

    This hook takes an instance of a
    :py:class:`~reviewboard.accounts.sso.backends.base.BaseSSOBackend`
    subclass. The backend is unregistered when the extension is disabled.

    Version Added:
        9.0
    """

    registry = sso_backends

    def initialize(
        self,
        backend: BaseSSOBackend,
    ) -> None:
        """Initialize the hook.

        This will register the provided SSO backend.

        Args:
            backend (reviewboard.accounts.sso.backends.base.BaseSSOBackend):
                The SSO backend instance to register.
        """
        super().initialize(backend)
