"""Registry for SSO backends.

Version Added:
    5.0
"""

from __future__ import annotations

import re
from importlib import import_module
from typing import TYPE_CHECKING

from django.urls import include, path, re_path
from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (
    ALREADY_REGISTERED,
    LOAD_ENTRY_POINT,
    NOT_REGISTERED,
)

from reviewboard.accounts.sso.backends.base import BaseSSOBackend
from reviewboard.registries.registry import EntryPointRegistry

if TYPE_CHECKING:
    from collections.abc import Iterator

    from importlib_metadata import EntryPoint


class SSOBackendRegistry(EntryPointRegistry[BaseSSOBackend]):
    """A registry for managing SSO backends.

    Backends can be registered directly, or provided by packages through
    the ``reviewboard.sso_backends`` entry point. Each entry point must
    point to a :py:class:`~reviewboard.accounts.sso.backends.base.
    BaseSSOBackend` subclass, which will be instantiated when loaded.

    Version Changed:
        9.0:
        Backends are now loaded from the ``reviewboard.sso_backends`` entry
        point.

    Version Added:
        5.0
    """

    entry_point = 'reviewboard.sso_backends'
    lookup_attrs = ['backend_id']

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered SSO backend.'
        ),
        LOAD_ENTRY_POINT: _(
            'Error loading SSO backend %(entry_point)s: %(error)s'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered SSO backend.'
        ),
    }

    def __init__(self):
        """Initialize the registry."""
        super().__init__()
        self._url_patterns = {}

    def process_value_from_entry_point(
        self,
        entry_point: EntryPoint,
    ) -> BaseSSOBackend:
        """Load and instantiate the backend class from an entry point.

        Version Added:
            9.0

        Args:
            entry_point (importlib_metadata.EntryPoint):
                The entry point.

        Returns:
            reviewboard.accounts.sso.backends.base.BaseSSOBackend:
            The SSO backend instance.
        """
        return entry_point.load()()

    def get_defaults(self) -> Iterator[BaseSSOBackend]:
        """Yield the built-in and entry point SSO backends.

        This will make sure the standard SSO backends are always present in the
        registry.

        Version Changed:
            9.0:
            Backends from the ``reviewboard.sso_backends`` entry point are now
            included.

        Yields:
            reviewboard.accounts.sso.backends.base.BaseSSOBackend:
            The SSO backend instances.
        """
        builtin_backends = (
            ('saml.sso_backend', 'SAMLSSOBackend'),
        )

        for _module, _backend_cls_name in builtin_backends:
            mod = import_module('reviewboard.accounts.sso.backends.%s'
                                % _module)
            cls = getattr(mod, _backend_cls_name)
            yield cls()

        yield from super().get_defaults()

    def get_siteconfig_defaults(self):
        """Return defaults for the site configuration.

        Returns:
            dict:
            The defaults to register for the site configuration.
        """
        defaults = {}

        for backend in self:
            defaults.update(backend.siteconfig_defaults)

        return defaults

    def register(self, backend):
        """Register an SSO backend.

        This also adds the URL patterns defined by the backend. If the backend
        has a
        :py:attr:`~reviewboard.accounts.sso.backends.base.SSOBackend.urls`
        attribute that is non-``None``, they will be automatically added.

        Args:
            backend (reviewboard.accounts.sso.backends.base.BaseSSOBackend):
                The backend instance.
        """
        super().register(backend)

        from reviewboard.accounts.urls import sso_dynamic_urls

        if backend.urls:
            backend_id = backend.backend_id
            backend_urls = backend.urls

            if backend.login_view_cls:
                backend_urls.append(path(
                    'login/',
                    backend.login_view_cls.as_view(sso_backend=backend),
                    name='login'))

            dynamic_urls = [
                re_path(
                    r'^(?P<backend_id>%s)/' % re.escape(backend_id),
                    include((backend_urls, 'accounts'),
                            namespace=backend_id)),
            ]
            self._url_patterns[backend_id] = dynamic_urls
            sso_dynamic_urls.add_patterns(dynamic_urls)

    def unregister(self, backend):
        """Unregister an SSO backend.

        This will remove all registered URLs that the backend has defined.

        Args:
            backend (reviewboard.accounts.sso.backends.base.BaseSSOBackend):
                The backend instance.
        """
        super().unregister(backend)

        from reviewboard.accounts.urls import sso_dynamic_urls

        try:
            dynamic_urls = self._url_patterns.pop(backend.backend_id)
            sso_dynamic_urls.remove_patterns(dynamic_urls)
        except KeyError:
            pass
