"""Hosting service support."""

from __future__ import annotations

from django.dispatch import receiver

from reviewboard.signals import initializing


@receiver(initializing, dispatch_uid='populate_hosting_services')
def _populate_registry(**kwargs) -> None:
    """Populate the hosting services registry.

    This will pre-populate the hosting services registry, ensuring
    that any URLs are automatically added and available for use.

    Version Added:
        6.0

    Args:
        **kwargs (dict, unused):
            Keyword arguments sent by the signal.
    """
    # We populate this here because we need to ensure any URLs are registered
    # once Review Board has initialized. We also need to ensure this is done
    # during unit test runs when the environment is re-initialized. It's not
    # sufficient to do this during AppConfig.ready.
    from reviewboard.hostingsvcs.base import hosting_service_registry

    hosting_service_registry.populate()
