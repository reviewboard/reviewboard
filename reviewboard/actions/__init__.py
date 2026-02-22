"""Actions framework for Review Board.

Version Added:
    6.0
"""

from djblets.registries.importer import lazy_import_registry

from reviewboard.actions.base import (AttachmentPoint,
                                      BaseAction,
                                      BaseMenuAction)


#: The actions registry.
actions_registry = lazy_import_registry(
    'reviewboard.actions.registry', 'ActionsRegistry')


__all__ = [
    'AttachmentPoint',
    'BaseAction',
    'BaseMenuAction',
    'actions_registry',
]

__autodoc_excludes__ = [
    'AttachmentPoint',
    'BaseAction',
    'BaseMenuAction',
]
