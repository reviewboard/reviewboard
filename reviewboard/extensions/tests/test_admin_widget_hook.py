"""Unit tests for reviewboard.extensions.hooks.AdminWidgetHook."""

from __future__ import unicode_literals

from reviewboard.admin.widgets import (Widget,
                                       primary_widgets,
                                       secondary_widgets)
from reviewboard.extensions.hooks import AdminWidgetHook
from reviewboard.extensions.tests.testcases import (DummyExtension,
                                                    ExtensionManagerMixin)
from reviewboard.testing.testcase import TestCase


class TestWidget(Widget):
    widget_id = 'test'
    title = 'Testing Widget'


class AdminWidgetHookTests(ExtensionManagerMixin, TestCase):
    """Testing AdminWidgetHook."""

    def setUp(self):
        super(AdminWidgetHookTests, self).setUp()

        self.extension = DummyExtension(extension_manager=self.manager)

    def tearDown(self):
        super(AdminWidgetHookTests, self).tearDown()

        self.extension.shutdown()

    def test_register(self):
        """Testing AdminWidgetHook initializing"""
        AdminWidgetHook(extension=self.extension, widget_cls=TestWidget)

        self.assertIn(TestWidget, secondary_widgets)

    def test_register_with_primary(self):
        """Testing AdminWidgetHook initializing with primary set"""
        AdminWidgetHook(extension=self.extension, widget_cls=TestWidget,
                        primary=True)

        self.assertIn(TestWidget, primary_widgets)

    def test_unregister(self):
        """Testing AdminWidgetHook uninitializing"""
        hook = AdminWidgetHook(extension=self.extension, widget_cls=TestWidget)

        hook.disable_hook()

        self.assertNotIn(TestWidget, secondary_widgets)
