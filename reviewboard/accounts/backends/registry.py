"""Authentication backend registry."""

from __future__ import unicode_literals

import logging
from warnings import warn

from django.conf import settings
from django.contrib.auth import get_backends
from django.utils.translation import ugettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED, LOAD_ENTRY_POINT,
                                         NOT_REGISTERED, UNREGISTER)

from reviewboard.accounts.backends.base import BaseAuthBackend
from reviewboard.accounts.backends.standard import StandardAuthBackend
from reviewboard.registries.registry import EntryPointRegistry


_enabled_auth_backends = []
_auth_backend_setting = None


class AuthBackendRegistry(EntryPointRegistry):
    """A registry for managing authentication backends."""

    entry_point = 'reviewboard.auth_backends'
    lookup_attrs = ('backend_id',)

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)r" is already a registered authentication backend.'
        ),
        LOAD_ENTRY_POINT: _(
            'Error loading authentication backend %(entry_point)s: %(error)s'
        ),
        NOT_REGISTERED: _(
            'No authentication backend registered with %(attr_name)s = '
            '%(attr_value)s.'
        ),
        UNREGISTER: _(
            '"%(item)r is not a registered authentication backend.'
        ),
    }

    def process_value_from_entry_point(self, entry_point):
        """Load the class from the entry point.

        If the class lacks a value for
        :py:attr:`~reviewboard.accounts.backends.base.BaseAuthBackend
        .backend_id`, it will be set as the entry point's name.

        Args:
           entry_point (pkg_resources.EntryPoint):
                The entry point.

        Returns:
            type:
            The :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
            subclass.
        """

        cls = entry_point.load()

        if not cls.backend_id:
            logging.warning('The authentication backend %r did not provide '
                            'a backend_id attribute. Setting it to the '
                            'entry point name ("%s")',
                            cls, entry_point.name)

            cls.backend_id = entry_point.name

        return cls

    def get_defaults(self):
        """Yield the authentication backends.

        This will make sure the standard authentication backend is always
        registered and returned first.

        Yields:
            type:
            The :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
            subclasses.
        """
        yield StandardAuthBackend

        for value in super(AuthBackendRegistry, self).get_defaults():
            yield value

    def unregister(self, backend_class):
        """Unregister the requested authentication backend.

        Args:
            backend_class (type):
                The class of the backend to unregister. This must be a subclass
                of :py:class:`~reviewboard.accounts.backends.base
                .BaseAuthBackend`.

        Raises:
            djblets.registries.errors.ItemLookupError:
                Raised when the class cannot be found.
        """
        self.populate()

        try:
            super(AuthBackendRegistry, self).unregister(backend_class)
        except self.lookup_error_class as e:
            logging.error('Failed to unregister unknown authentication '
                          'backend "%s".',
                          backend_class.backend_id)
            raise e

    def get_auth_backend(self, auth_backend_id):
        """Return the requested authentication backend, if it exists.

        Args:
            auth_backend_id (unicode):
                The unique ID of the
                :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
                class.

        Returns:
            type:
            The :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
            subclass, or ``None`` if it is not registered.
        """
        return self.get('backend_id', auth_backend_id)


def get_enabled_auth_backends():
    """Return all authentication backends being used by Review Board.

    The returned list contains every authentication backend that Review Board
    will try, in order.

    Returns:
        list of type:
        The list of registered
        :py:class:`~reviewboard.accounts.backends.base.BaseAuthBackend`
        subclasses.
    """
    global _enabled_auth_backends
    global _auth_backend_setting

    if (not _enabled_auth_backends or
        _auth_backend_setting != settings.AUTHENTICATION_BACKENDS):
        _enabled_auth_backends = list(get_backends())
        _auth_backend_setting = settings.AUTHENTICATION_BACKENDS

    return _enabled_auth_backends


#: Registry instance for working with available authentication backends.
auth_backends = AuthBackendRegistry()
