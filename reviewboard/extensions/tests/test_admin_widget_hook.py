"""Unit tests for reviewboard.extensions.hooks.AdminWidgetHook."""

from __future__ import unicode_literals

from reviewboard.admin.widgets import (BaseAdminWidget,
                                       Widget,
                                       admin_widgets_registry)
from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.extensions.hooks import AdminWidgetHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase


class MyLegacyAdminWidget(Widget):
    widget_id = 'legacy-test-widget'
    title = 'Legacy Testing Widget'


class MyAdminWidget(BaseAdminWidget):
    widget_id = 'test-widget'
    name = 'Testing Widget'


class AdminWidgetHookTests(BaseExtensionHookTestCase):
    """Testing AdminWidgetHook."""

    def test_initialize(self):
        """Testing AdminWidgetHook.initialize"""
        AdminWidgetHook(self.extension, MyAdminWidget)

        self.assertIn(MyAdminWidget, admin_widgets_registry)

    def test_initialize_with_legacy_widget(self):
        """Testing AdminWidgetHook.initialize with legacy Widget subclass"""
        message = (
            "AdminWidgetHook's support for legacy "
            "reviewboard.admin.widgets.Widget subclasses is deprecated "
            "and will be removed in Review Board 5.0. Rewrite %r "
            "to subclass the modern "
            "reviewboard.admin.widgets.baseAdminWidget instead. This "
            "will require a full rewrite of the widget's functionality."
            % MyLegacyAdminWidget
        )

        with self.assertWarns(RemovedInReviewBoard50Warning, message):
            AdminWidgetHook(self.extension, MyLegacyAdminWidget)

        self.assertIn(MyLegacyAdminWidget, admin_widgets_registry)

    def test_shutdown(self):
        """Testing AdminWidgetHook.shutdown"""
        hook = AdminWidgetHook(self.extension, MyAdminWidget)
        hook.disable_hook()

        self.assertNotIn(MyAdminWidget, admin_widgets_registry)
