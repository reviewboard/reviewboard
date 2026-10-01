"""Hooks for webapi functionality.

Version Added:
    9.0:
    This replaces the old
    :py:mod:`reviewboard.extensions.hooks.api_extra_data_access` and
    :py:mod:`reviewboard.extensions.hooks.webapi_capabilities` modules.
"""

from __future__ import annotations

from djblets.extensions.hooks import (
    BaseRegistryMultiItemHook,
    ExtensionHook,
    ExtensionHookPoint,
)
from djblets.registries.errors import ItemLookupError

from reviewboard.webapi.server_info import (
    register_webapi_capabilities,
    unregister_webapi_capabilities,
)
from reviewboard.webapi.token_policies import (
    BaseWebAPITokenPolicy,
    webapi_token_policies,
)


class APIExtraDataAccessHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for setting access states on extra data fields.

    Extensions can use this hook to register ``extra_data`` fields with
    certain access states on subclasses of
    :py:data:`~reviewboard.webapi.base.WebAPIResource`.

    This accepts a list of ``field_set`` values specified by the Extension and
    registers them when the hook is created. Likewise, it unregisters the same
    list of ``field_set`` values when the Extension is disabled.

    Each element of ``field_set`` is a 2-:py:class:`tuple` where the first
    element of the tuple is the field's path (as a :py:class:`tuple`) and the
    second is the field's access state (as one of
    :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.
    ACCESS_STATE_PUBLIC`
    or :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.
    ACCESS_STATE_PRIVATE`).

    Example:
        .. code-block:: python

            obj.extra_data = {
                'foo': {
                    'bar' : 'private_data',
                    'baz' : 'public_data'
                }
            }

            ...

            APIExtraDataAccessHook(
                extension,
                resource,
                [
                    (('foo', 'bar'), ExtraDataAccessLevel.ACCESS_STATE_PRIVATE,
                ])
    """

    def initialize(self, resource, field_set):
        """Initialize the APIExtraDataAccessHook.

        Args:
            resource (reviewboard.webapi.base.WebAPIResource):
                The resource to modify access states for.

            field_set (list):
                Each element of ``field_set`` is a 2-:py:class:`tuple` where
                the first element of the tuple is the field's path (as a
                :py:class:`tuple`) and the second is the field's access state
                (as one of
                :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.
                ACCESS_STATE_PUBLIC`
                or :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.
                ACCESS_STATE_PRIVATE`).
        """
        self.resource = resource
        self.field_set = field_set

        resource.extra_data_access_callbacks.register(
            self.get_extra_data_state)

    def get_extra_data_state(self, key_path):
        """Return the state of an extra_data field.

        Args:
            key_path (tuple):
                A tuple of strings representing the path of an extra_data
                field.

        Returns:
            int:
            The access state of the provided field or ``None``.
        """
        for path, access_state in self.field_set:
            if path == key_path:
                return access_state

        return None

    def shutdown(self):
        """Shut down the hook.

        This will unregister the access levels from the resource.
        """
        try:
            self.resource.extra_data_access_callbacks.unregister(
                self.get_extra_data_state)
        except ItemLookupError:
            pass


class WebAPICapabilitiesHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """This hook allows adding capabilities to the web API server info.

    Note that this does not add the functionality, but adds to the server
    info listing.

    Extensions may only provide one instance of this hook. All capabilities
    must be registered at once.
    """

    def initialize(self, caps):
        """Initialize the hook.

        This will register each of the capabilities for the API.

        Args:
            caps (dict):
                The dictionary of capabilities to register. Each key must
                be a string, and each value should be a boolean or a
                dictionary of string keys to booleans.

        Raises:
            KeyError:
                Capabilities have already been registered by this extension.
        """
        register_webapi_capabilities(self.extension.id, caps)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the capabilities from the API.
        """
        unregister_webapi_capabilities(self.extension.id)


class WebAPITokenPoliciesHook(
    BaseRegistryMultiItemHook[type[BaseWebAPITokenPolicy]],
    metaclass=ExtensionHookPoint,
):
    """Hook for registering new API token policies.

    Version Added:
        9.0
    """

    registry = webapi_token_policies
