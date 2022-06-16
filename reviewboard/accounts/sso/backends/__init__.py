"""Backends for Single Sign-On.

Version Added:
    5.0
"""

from djblets.registries.importer import lazy_import_registry


#: The SSO backends registry
sso_backends = lazy_import_registry(
    'reviewboard.accounts.sso.backends.registry',
    'SSOBackendRegistry')
