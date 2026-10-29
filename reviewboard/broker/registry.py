"""Registry for message broker backends.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (
    ALREADY_REGISTERED,
    LOAD_ENTRY_POINT,
    NOT_REGISTERED,
    UNREGISTER,
)

from reviewboard.broker.base.backends import BaseBrokerBackend
from reviewboard.registries.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Iterator


class BrokerBackendRegistry(Registry[type[BaseBrokerBackend]]):
    """A registry for managing message broker backends.

    Version Added:
        9.0
    """

    lookup_attrs = ('broker_id',)

    errors = {
        ALREADY_REGISTERED: _(
            '%(item)r is already a registered broker backend.'
        ),
        LOAD_ENTRY_POINT: _(
            'Error loading broker backend %(entry_point)s: %(error)s'
        ),
        NOT_REGISTERED: _(
            'No broker backend registered with %(attr_name)s = '
            '%(attr_value)s.'
        ),
        UNREGISTER: _(
            '%(item)r is not a registered broker backend.'
        ),
    }

    def get_broker(
        self,
        broker_id: str,
    ) -> type[BaseBrokerBackend] | None:
        """Return the broker class with the given ID.

        If the broker isn't found, ``None`` will be returned.

        Args:
            broker_id (str):
                The ID of the broker to return.

        Returns:
            type:
            The matching broker class, or ``None`` if not found.
        """
        return self.get_or_none('broker_id', broker_id)

    def get_defaults(self) -> Iterator[type[BaseBrokerBackend]]:
        """Yield the built-in broker backends.

        Yields:
            type:
            Each :py:class:`~reviewboard.broker.base.backends.
            BaseBrokerBackend` subclass.
        """
        from reviewboard.broker.backends.local import LocalBrokerBackend
        from reviewboard.broker.backends.memory import MemoryBrokerBackend

        yield LocalBrokerBackend

        if settings.RUNNING_TEST:
            yield MemoryBrokerBackend


#: The global Registry for available broker backends.
#:
#: Version Added:
#:     9.0
broker_registry = BrokerBackendRegistry()
