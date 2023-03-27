"""A hook for setting access states on extra data fields."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.registries.errors import ItemLookupError


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
    :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PUBLIC`
    or :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PRIVATE`).

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
                :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PUBLIC`
                or :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PRIVATE`).
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
