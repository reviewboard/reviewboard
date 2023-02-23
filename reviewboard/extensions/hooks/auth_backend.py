"""A hook for registering an authentication backend."""

from __future__ import annotations

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint

from reviewboard.accounts.backends import auth_backends


class AuthBackendHook(BaseRegistryHook, metaclass=ExtensionHookPoint):
    """A hook for registering an authentication backend.

    Authentication backends control user authentication, registration, user
    lookup, and user data manipulation.

    This hook takes the class of an authentication backend that should
    be made available to the server.
    """

    registry = auth_backends

    def initialize(self, backend_cls):
        """Initialize the hook.

        This will register the provided authentication backend.

        Args:
            backend_cls (type):
                The authentication backend to register. This should be a
                subclass of
                :py:class:`~reviewboard.accounts.backends.AuthBackend`.
        """
        super(AuthBackendHook, self).initialize(backend_cls)
