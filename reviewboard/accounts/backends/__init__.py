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


# Legacy references.
AuthBackend = BaseAuthBackend
INVALID_USERNAME_CHAR_REGEX = AuthBackend.INVALID_USERNAME_CHAR_REGEX


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
