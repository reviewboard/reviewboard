"""Unit tests for reviewboard.admin.widgets."""

from __future__ import unicode_literals

from reviewboard.admin.widgets import (Widget,
                                       admin_widgets_registry,
                                       register_admin_widget,
                                       unregister_admin_widget)
from reviewboard.deprecation import RemovedInReviewBoard50Warning
from reviewboard.testing.testcase import TestCase


class MyLegacyWidget(Widget):
    widget_id = 'my-legacy-widget'
    title = 'My Legacy Widget'


class WidgetTests(TestCase):
    """Unit tests for the legacy reviewboard.admin.widgets.Widget."""

    def test_init(self):
        """Testing Widget.__init__"""
        message = (
            'Administration widgets should no longer inherit from '
            'reviewboard.admin.widgets.Widget. This class will be removed '
            'in Review Board 5.0. Please rewrite %r to inherit from '
            'reviewboard.admin.widgets.BaseAdminWidget instead.'
            % MyLegacyWidget
        )

        with self.assertWarns(RemovedInReviewBoard50Warning, message):
            widget = MyLegacyWidget()

        self.assertEqual(widget.dom_id, 'my-legacy-widget')
        self.assertEqual(widget.name, 'My Legacy Widget')


class LegacyWidgetRegistryTests(TestCase):
    """Unit tests for legacy Widget registration functions."""

    def tearDown(self):
        super(LegacyWidgetRegistryTests, self).tearDown()

        # Just in case a test fails to unregister as expected, remove the
        # legacy widget here.
        if MyLegacyWidget in admin_widgets_registry:
            admin_widgets_registry.unregister(MyLegacyWidget)

    def test_register_admin_widget(self):
        """Testing register_admin_widget"""
        message = (
            'reviewboard.admin.widgets.register_admin_widget() is '
            'deprecated and will be removed in Review Board 5.0. Use '
            'reviewboard.admin.widgets.admin_widgets_registry.register() '
            'to register %r instead.'
            % MyLegacyWidget
        )

        with self.assertWarns(RemovedInReviewBoard50Warning, message):
            register_admin_widget(MyLegacyWidget)

        self.assertIn(MyLegacyWidget, admin_widgets_registry)
        self.assertIs(admin_widgets_registry.get_widget('my-legacy-widget'),
                      MyLegacyWidget)

        admin_widgets_registry.unregister(MyLegacyWidget)

    def test_unregister_admin_widget(self):
        """Testing unregister_admin_widget"""
        admin_widgets_registry.register(MyLegacyWidget)

        message = (
            'reviewboard.admin.widgets.unregister_admin_widget() is '
            'deprecated and will be removed in Review Board 5.0. Use '
            'reviewboard.admin.widgets.admin_widgets_registry.unregister() '
            'to unregister %r instead.'
            % MyLegacyWidget
        )

        with self.assertWarns(RemovedInReviewBoard50Warning, message):
            unregister_admin_widget(MyLegacyWidget)

        self.assertNotIn(MyLegacyWidget, admin_widgets_registry)
