"""Local memory message broker backend.

This isn't available for production. It's only used for unit tests.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from reviewboard.broker.base.backends import BaseCeleryBrokerBackend

if TYPE_CHECKING:
    from typelets.json import JSONDictImmutable

    from reviewboard.broker.base.backends import BackendCeleryConfig


class MemoryBrokerBackend(BaseCeleryBrokerBackend):
    """A message broker backend using in-process memory.

    This is only available for use in unit tests, ensuring that code
    triggering tasks can be properly tested.

    Version Added:
        9.0
    """

    broker_id = 'memory'
    name = _('Memory (testing only)')

    def get_celery_config(
        self,
        broker_settings: JSONDictImmutable,
    ) -> BackendCeleryConfig:
        """Return configuration for the Celery app.

        This will return the basic settings needed to use the memory backend.

        Args:
            broker_settings (dict):
                The stored settings for the broker.

        Returns:
            reviewboard.broker.base.backends.BackendCeleryConfig:
            The configuration settings for Celery.
        """
        return {
            'app_config': {
                'broker_url': 'memory://',
            },
        }
