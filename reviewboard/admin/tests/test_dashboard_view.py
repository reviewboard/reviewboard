"""Unit tests for reviewboard.admin.views.dashboard."""

from __future__ import unicode_literals

from reviewboard.admin.widgets import (Widget,
                                       primary_widgets,
                                       register_admin_widget,
                                       secondary_widgets,
                                       unregister_admin_widget)
from reviewboard.testing.testcase import TestCase


class AdminDashboardViewTests(TestCase):
    """Unit tests for reviewboard.admin.views.dashboard."""

    fixtures = ['test_users']

    def test_renders_widgets(self):
        """Testing admin dashboard view renders widgets"""
        self.client.login(username='admin', password='admin')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        total_inital_widgets = (
            len(response.context['selected_secondary_widgets']) +
            len(response.context['selected_primary_widgets']))

        # Since admin/views.py widget_select() does not get run in testing,
        # we must do this instead to set up the data.
        profile = response.context['user'].get_profile()
        profile.extra_data.update({
            'primary_widget_selections': {
                widget.widget_id: '1'
                for widget in primary_widgets
            },
            'secondary_widget_selections': {
                widget.widget_id: '1'
                for widget in secondary_widgets
            },
            'primary_widget_positions': {
                widget.widget_id: i
                for i, widget in enumerate(primary_widgets)
            },
            'secondary_widget_positions': {
                widget.widget_id: i
                for i, widget in enumerate(secondary_widgets)
            },
        })
        profile.save(update_fields=('extra_data',))

        class TestPrimaryWidget(Widget):
            widget_id = 'test-primary-widget'

        class TestSecondaryWidget(Widget):
            widget_id = 'test-secondary-widget'

        # If either new widget doesn't render correctly, the page will break.
        try:
            register_admin_widget(TestPrimaryWidget, True)
            register_admin_widget(TestSecondaryWidget)

            # We must also add TestPrimaryWidget to primary_widget_selections
            # and TestSecondaryWidget to secondary_widget_selections, so that
            # they are selected to display on the page, but have no position.
            primary_selections = (
                profile.extra_data['primary_widget_selections'])
            secondary_selections = (
                profile.extra_data['secondary_widget_selections'])
            primary_selections[TestPrimaryWidget.widget_id] = '1'
            secondary_selections[TestSecondaryWidget.widget_id] = '1'
            profile.save(update_fields=('extra_data',))

            response = self.client.get('/admin/')
            self.assertEqual(response.status_code, 200)
            total_tested_widgets = (
                len(response.context['selected_secondary_widgets']) +
                len(response.context['selected_primary_widgets']))
            self.assertTrue(total_tested_widgets == total_inital_widgets + 2)
            self.assertIn(TestPrimaryWidget,
                          response.context['selected_primary_widgets'])
            self.assertIn(TestSecondaryWidget,
                          response.context['selected_secondary_widgets'])

        finally:
            # If an error was encountered above, the widgets will not be
            # registered. Ignore any errors in that case.
            try:
                unregister_admin_widget(TestPrimaryWidget)
            except KeyError:
                pass

            try:
                unregister_admin_widget(TestSecondaryWidget)
            except KeyError:
                pass
