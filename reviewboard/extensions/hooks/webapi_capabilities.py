"""A hook for adding capabilities to the API server info payload."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint

from reviewboard.webapi.server_info import (register_webapi_capabilities,
                                            unregister_webapi_capabilities)


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
                The dictionary of capabilities to register. Each key msut
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
