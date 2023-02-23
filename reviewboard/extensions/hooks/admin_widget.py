"""A hook for adding a new widget to the administration dashboard."""

from __future__ import annotations

from djblets.extensions.hooks import BaseRegistryHook, ExtensionHookPoint

from reviewboard.admin.widgets import admin_widgets_registry


class AdminWidgetHook(BaseRegistryHook, metaclass=ExtensionHookPoint):
    """A hook for adding a new widget to the administration dashboard.

    Version Changed:
        4.0:
        Widget classes should now subclass
        :py:class:`~reviewboard.admin.widgets.AdminBaseWidget` instead of
        :py:class:`~reviewboard.admin.widgets.Widget`. Note that this will
        require a full rewrite of the widget.

        The ``primary`` argument is no longer supported when instantiating
        the hook, and will be ignored. Callers should remove it.

    Version Changed:
        5.0:
        Support for legacy widgets and arguments has been removed.
    """

    registry = admin_widgets_registry
