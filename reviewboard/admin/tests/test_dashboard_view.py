"""Unit tests for reviewboard.admin.views.dashboard."""

from __future__ import unicode_literals

from django.utils import six
from kgb import SpyAgency

from reviewboard.admin.views import logger
from reviewboard.admin.widgets import BaseAdminWidget, admin_widgets_registry
from reviewboard.testing.testcase import TestCase


class MyWidget(BaseAdminWidget):
    widget_id = 'my-widget'
    name = 'My Widget'
    css_classes = 'test-c-my-widget -is-large'

    def get_js_model_attrs(self, request):
        return {
            'test_attr': 'test-value',
        }

    def get_js_model_options(self, request):
        return {
            'test_option': 'test-value',
        }

    def get_js_view_options(self, request):
        return {
            'test_option': 'test-value',
        }


class HiddenWidget(BaseAdminWidget):
    widget_id = 'hidden-widget'
    name = 'Hidden Widget'

    def can_render(self, request):
        return False


class AdminDashboardViewTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.admin.views.admin_dashboard_view."""

    fixtures = ['test_users']

    def test_get(self):
        """Testing admin_dashboard_view"""
        admin_widgets_registry.register(MyWidget)

        try:
            self.client.login(username='admin', password='admin')
            response = self.client.get('/admin/')
            self.assertEqual(response.status_code, 200)

            self.assertIn('page_model_attrs', response.context)
            widgets = response.context['page_model_attrs']['widgetsData']

            self.assertEqual(len(widgets), len(admin_widgets_registry))

            self.assertEqual(
                widgets[-1],
                {
                    'id': 'my-widget',
                    'domID': 'admin-widget-my-widget',
                    'viewClass': 'RB.Admin.WidgetView',
                    'modelClass': 'RB.Admin.Widget',
                    'viewOptions': {
                        'test_option': 'test-value',
                    },
                    'modelAttrs': {
                        'test_attr': 'test-value',
                    },
                    'modelOptions': {
                        'test_option': 'test-value',
                    },
                })

            self.assertIn(
                b'<div class="rb-c-admin-widget test-c-my-widget -is-large"'
                b' id="admin-widget-my-widget">',
                response.content)
        finally:
            admin_widgets_registry.unregister(MyWidget)

    def test_get_with_widget_can_render_false(self):
        """Testing admin_dashboard_view with widget.can_render() == False"""
        admin_widgets_registry.register(HiddenWidget)

        try:
            self.client.login(username='admin', password='admin')
            response = self.client.get('/admin/')
            self.assertEqual(response.status_code, 200)

            self.assertIn('page_model_attrs', response.context)
            widgets = response.context['page_model_attrs']['widgetsData']

            self.assertEqual(len(widgets), len(admin_widgets_registry) - 1)

            self.assertNotEqual(widgets[-1]['id'], 'hidden-widget')
        finally:
            admin_widgets_registry.unregister(HiddenWidget)

    def test_get_with_broken_widget_init(self):
        """Testing admin_dashboard_view with broken widget.__init__"""
        error_msg = '__init__ broke'

        class BrokenWidget(BaseAdminWidget):
            widget_id = 'broken-widget'

            def __init__(self):
                raise Exception(error_msg)

        self._test_broken_widget(BrokenWidget, error_msg)

    def test_get_with_broken_widget_can_render(self):
        """Testing admin_dashboard_view with broken widget.can_render"""
        error_msg = 'can_render broke'

        class BrokenWidget(BaseAdminWidget):
            widget_id = 'broken-widget'

            def can_render(self, request):
                raise Exception(error_msg)

        self._test_broken_widget(BrokenWidget, error_msg)

    def test_get_with_broken_widget_get_js_view_options(self):
        """Testing admin_dashboard_view with broken widget.get_js_view_options
        """
        error_msg = 'get_js_view_options broke'

        class BrokenWidget(BaseAdminWidget):
            widget_id = 'broken-widget'

            def get_js_view_options(self, request):
                raise Exception(error_msg)

        self._test_broken_widget(BrokenWidget, error_msg)

    def test_get_with_broken_widget_get_js_model_attrs(self):
        """Testing admin_dashboard_view with broken widget.get_js_model_attrs
        """
        error_msg = 'get_js_model_attrs broke'

        class BrokenWidget(BaseAdminWidget):
            widget_id = 'broken-widget'

            def get_js_model_attrs(self, request):
                raise Exception(error_msg)

        self._test_broken_widget(BrokenWidget, error_msg)

    def test_get_with_broken_widget_get_js_model_options(self):
        """Testing admin_dashboard_view with broken widget.get_js_model_options
        """
        error_msg = 'get_js_model_options broke'

        class BrokenWidget(BaseAdminWidget):
            widget_id = 'broken-widget'

            def get_js_model_options(self, request):
                raise Exception(error_msg)

        self._test_broken_widget(BrokenWidget, error_msg)

    def test_get_with_broken_widget_render(self):
        """Testing admin_dashboard_view with broken widget.render"""
        error_msg = 'render broke'

        class BrokenWidget(BaseAdminWidget):
            widget_id = 'broken-widget'

            def render(self, request):
                raise Exception(error_msg)

        self._test_broken_widget(BrokenWidget, error_msg)

    def _test_broken_widget(self, widget_cls, expected_msg):
        """Test that a broken widget doesn't break the dashboard view.

        Args:
            widget_cls (type):
                The broken widget to register and test against.

            expected_msg (unicode, optional):
                The expected error message raised by the broken method.
        """
        admin_widgets_registry.register(widget_cls)
        self.spy_on(logger.exception)

        try:
            self.client.login(username='admin', password='admin')
            response = self.client.get('/admin/')
            self.assertEqual(response.status_code, 200)

            self.assertIn('page_model_attrs', response.context)
            widgets = response.context['page_model_attrs']['widgetsData']

            self.assertEqual(len(widgets), len(admin_widgets_registry) - 1)
            self.assertNotEqual(widgets[-1]['id'], widget_cls.widget_id)
            self.assertNotIn(
                b'id="admin-widget-%s"' % widget_cls.widget_id.encode('utf-8'),
                response.content)

            spy_call = logger.exception.last_call
            self.assertEqual(spy_call.args[0],
                             'Error setting up administration widget %r: %s')
            self.assertEqual(spy_call.args[1], widget_cls)
            self.assertIsInstance(spy_call.args[2], Exception)
            self.assertEqual(six.text_type(spy_call.args[2]), expected_msg)
        finally:
            admin_widgets_registry.unregister(widget_cls)
