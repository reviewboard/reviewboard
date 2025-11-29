"""Actions framework for Review Board.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from djblets.registries.importer import lazy_import_registry

from reviewboard.actions.base import (ActionAttachmentPoint,
                                      ActionPlacement,
                                      AttachmentPoint,
                                      BaseAction,
                                      BaseGroupAction,
                                      BaseMenuAction,
                                      QuickAccessActionMixin)

if TYPE_CHECKING:
    from reviewboard.actions.registry import (
        ActionAttachmentPointsRegistry,
        ActionsRegistry,
    )


#: The actions registry.
actions_registry: ActionsRegistry = lazy_import_registry(
    'reviewboard.actions.registry',
    'ActionsRegistry')  # type: ignore


#: The action attachment points registry.
#:
#: Version Added:
#:     7.1
action_attachment_points_registry: ActionAttachmentPointsRegistry = \
    lazy_import_registry('reviewboard.actions.registry',
                         'ActionAttachmentPointsRegistry')  # type: ignore


__all__ = [
    'ActionAttachmentPoint',
    'ActionPlacement',
    'AttachmentPoint',
    'BaseAction',
    'BaseGroupAction',
    'BaseMenuAction',
    'QuickAccessActionMixin',
    'action_attachment_points_registry',
    'actions_registry',
]

__autodoc_excludes__ = [
    'ActionAttachmentPoint',
    'ActionPlacement',
    'AttachmentPoint',
    'BaseAction',
    'BaseGroupAction',
    'BaseMenuAction',
    'QuickAccessActionMixin',
]
