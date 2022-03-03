"""Unit tests for reviewboard.extensions.hooks.AdminWidgetHook."""

from reviewboard.admin.widgets import (BaseAdminWidget,
                                       admin_widgets_registry)
from reviewboard.extensions.hooks import AdminWidgetHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase


class MyAdminWidget(BaseAdminWidget):
    widget_id = 'test-widget'
    name = 'Testing Widget'


class AdminWidgetHookTests(BaseExtensionHookTestCase):
    """Testing AdminWidgetHook."""

    def test_initialize(self):
        """Testing AdminWidgetHook.initialize"""
        AdminWidgetHook(self.extension, MyAdminWidget)

        self.assertIn(MyAdminWidget, admin_widgets_registry)

    def test_shutdown(self):
        """Testing AdminWidgetHook.shutdown"""
        hook = AdminWidgetHook(self.extension, MyAdminWidget)
        hook.disable_hook()

        self.assertNotIn(MyAdminWidget, admin_widgets_registry)
