"""Review UI framework.

Review UIs allow specialized review experiences for different file types.
"""

from __future__ import annotations

from djblets.registries.importer import lazy_import_registry


#: The registry for Review UIs.
#:
#: Version Added:
#:     7.0
review_ui_registry = lazy_import_registry(
    'reviewboard.reviews.ui.registry', 'ReviewUIRegistry')
