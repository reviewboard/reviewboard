"""Forwarding imports and legacy utilities for authentication backends.

This module provides legacy functionality for registering authentication
backends, along with forwarding imports for:

.. autosummary::
   :nosignatures:

   ~reviewboard.accounts.backends.ad.ActiveDirectoryBackend
   ~reviewboard.accounts.backends.base.BaseAuthBackend
   ~reviewboard.accounts.backends.http_digest.HTTPDigestBackend
   ~reviewboard.accounts.backends.ldap.LDAPBackend
   ~reviewboard.accounts.backends.nis.NISBackend
   ~reviewboard.accounts.backends.registry.AuthBackendRegistry
   ~reviewboard.accounts.backends.registry.auth_backends
   ~reviewboard.accounts.backends.registry.get_enabled_auth_backends
   ~reviewboard.accounts.backends.standard.StandardAuthBackend
   ~reviewboard.accounts.backends.x509.X509Backend

Version Changed:
    3.0:
    The contents of this module were split into sub-modules.
"""

from __future__ import unicode_literals

from warnings import warn

from reviewboard.accounts.backends.ad import ActiveDirectoryBackend
from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.backends.http_digest import HTTPDigestBackend
from reviewboard.accounts.backends.ldap import LDAPBackend
from reviewboard.accounts.backends.nis import NISBackend
from reviewboard.accounts.backends.registry import (AuthBackendRegistry,
                                                    auth_backends,
                                                    get_enabled_auth_backends)
from reviewboard.accounts.backends.standard import StandardAuthBackend
from reviewboard.accounts.backends.x509 import X509Backend
from reviewboard.deprecation import RemovedInReviewBoard40Warning


# Legacy references.
AuthBackend = BaseAuthBackend
INVALID_USERNAME_CHAR_REGEX = AuthBackend.INVALID_USERNAME_CHAR_REGEX


def get_registered_auth_backends():
    """Yield all registered Review Board authentication backends.

    This will return all backends provided both by Review Board and by
    third parties that have properly registered with the
    ``reviewboard.auth_backends`` entry point.

    Deprecated:
        3.0:
        Iterate over
        :py:data:`~reviewboard.accounts.backends.registry.auth_backends`
        instead.

    Yields:
        type:
        The :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
        subclasses.
    """
    warn('reviewboard.accounts.backends.get_registered_auth_backends() is '
         'deprecated. Iterate over '
         'reviewboard.accounts.backends.auth_backends instead.',
         RemovedInReviewBoard40Warning)

    for backend in auth_backends:
        yield backend


def get_registered_auth_backend(backend_id):
    """Return the authentication backend with the specified ID.

    Deprecated:
        3.0:
        Use :py:meth:`auth_backends.get_auth_backend()
        <reviewboard.accounts.backends.registry.AuthBackendRegistry.
        get_auth_backend>` instead.

    Args:
        backend_id (unicode):
            The ID of the backend to retrieve.

    Returns:
        reviewboard.accounts.backends.base.BaseAuthBackend:
        The authentication backend, or ``None`` if it could not be found.
    """
    warn('reviewboard.accounts.backends.get_registered_auth_backend() is '
         'deprecated. Use '
         'reviewboard.accounts.backends.auth_backends.register() instead.',
         RemovedInReviewBoard40Warning)

    return auth_backends.get('backend_id', backend_id)


def register_auth_backend(backend_cls):
    """Register an authentication backend.

    This backend will appear in the list of available backends.
    The backend class must have a backend_id attribute set, and can only
    be registered once.

    Deprecated:
        3.0:
        Use :py:meth:`auth_backends.register()
        <reviewboard.accounts.backends.registry.AuthBackendRegistry.register>`
        instead.

    Args:
        backend_cls (type):
            The subclass of
            :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
            to register.

    Raises:
        KeyError:
            A backend already exists with this ID.
    """
    warn('reviewboard.accounts.backends.register_auth_backend() is '
         'deprecated. Use '
         'reviewboard.accounts.backends.auth_backends.register() instead.',
         RemovedInReviewBoard40Warning)

    auth_backends.register(backend_cls)


def unregister_auth_backend(backend_cls):
    """Unregister a previously registered authentication backend.

    Deprecated:
        3.0:
        Use :py:meth:`auth_backends.unregister()
        <reviewboard.accounts.backends.registry.AuthBackendRegistry.
        unregister>` instead.

    Args:
        backend_cls (type):
            The subclass of
            :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
            to unregister.
    """
    warn('reviewboard.accounts.backends.unregister_auth_backend() is '
         'deprecated. Use '
         'reviewboard.accounts.backends.auth_backends.unregister() instead.',
         RemovedInReviewBoard40Warning)

    auth_backends.unregister(backend_cls)


__all__ = (
    'ActiveDirectoryBackend',
    'AuthBackend',
    'AuthBackendRegistry',
    'HTTPDigestBackend',
    'INVALID_USERNAME_CHAR_REGEX',
    'LDAPBackend',
    'NISBackend',
    'StandardAuthBackend',
    'X509Backend',
    'auth_backends',
    'get_enabled_auth_backends',
    'get_registered_auth_backend',
    'get_registered_auth_backends',
    'register_auth_backend',
    'unregister_auth_backend',
)

__autodoc_excludes__ = (
    'ActiveDirectoryBackend',
    'AuthBackendRegistry',
    'HTTPDigestBackend',
    'LDAPBackend',
    'NISBackend',
    'StandardAuthBackend',
    'X509Backend',
    'auth_backends',
    'get_enabled_auth_backends',
)
