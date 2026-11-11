"""Signal handlers for hosting services.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models.signals import post_delete, post_save

from reviewboard.hostingsvcs.github.accounts import \
    clear_installation_repositories_cache
from reviewboard.scmtools.models import Repository

if TYPE_CHECKING:
    from typing import Any


def _on_repository_changed(
    *,
    instance: Repository,
    **kwargs: Any,
) -> None:
    """Handler for when a repository was saved or deleted.

    Version Added:
        9.0

    Args:
        instance (reviewboard.scmtools.models.Repository):
            The repository that was saved or deleted.

        **kwargs (dict, unused):
            Additional keyword arguments sent by the signal.
    """
    if instance.hosting_account_id is not None:
        # Clear the cached map that we use for GitHub App-connected
        # repository lookups.
        clear_installation_repositories_cache(
            instance.hosting_account_id)


def connect_signal_handlers() -> None:
    """Connect hosting service-related signal handlers.

    Version Added:
        9.0
    """
    post_save.connect(_on_repository_changed, sender=Repository)
    post_delete.connect(_on_repository_changed, sender=Repository)
