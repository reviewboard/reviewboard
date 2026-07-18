"""Unit tests for reviewboard.hostingsvcs.admin.ConfiguredBugTrackerAdmin.

Version Added:
    9.0
"""

from __future__ import annotations

from django.urls import reverse
from djblets.conditions import ConditionSet

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.testing.testcase import TestCase


class ConfiguredBugTrackerAdminTests(TestCase):
    """Unit tests for ConfiguredBugTrackerAdmin.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    def test_change_page_fieldsets(self) -> None:
        """Testing ConfiguredBugTrackerAdmin change page renders with the
        internal state fieldset
        """
        self.client.login(username='admin', password='admin')

        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'},
            user_conditions=ConditionSet(
                ConditionSet.MODE_ALL, []).serialize())

        url = reverse('admin:hostingsvcs_configuredbugtracker_change',
                      args=(bug_tracker.pk,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Internal State', response.content)

        # The advanced fields render in the collapsed section.
        content = response.content
        internal_state_pos = content.index(b'Internal State')
        self.assertGreater(content.index(b'name="local_site"'),
                           internal_state_pos)
        self.assertGreater(content.index(b'name="extra_data"'),
                           internal_state_pos)
        self.assertLess(content.index(b'name="name"'), internal_state_pos)

        # The display mode is chosen before the scoping it applies to.
        self.assertLess(content.index(b'name="display_mode"'),
                        content.index(b'name="apply_to"'))

    def test_change_page_settings_forms(self) -> None:
        """Testing ConfiguredBugTrackerAdmin change page renders each service's
        settings form
        """
        self.client.login(username='admin', password='admin')

        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'})

        url = reverse('admin:hostingsvcs_configuredbugtracker_change',
                      args=(bug_tracker.pk,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        content = response.content

        # The settings are edited as fields, not as raw JSON.
        self.assertNotIn(b'name="settings"', content)
        self.assertIn(b'data-service-id="splat"', content)
        self.assertIn(b'name="splat_org_name"', content)
        self.assertIn(b'value="my-org"', content)

        # Other services' forms are rendered too, for switching between.
        self.assertIn(b'data-service-id="custom-bug-tracker"', content)
        self.assertIn(b'name="url_template"', content)

    def test_change_page_settings_fieldsets(self) -> None:
        """Testing ConfiguredBugTrackerAdmin change page renders each service's
        settings form in a fieldset of its own
        """
        self.client.login(username='admin', password='admin')

        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='trac',
            settings={'trac_url': 'https://trac.example.com'})

        url = reverse('admin:hostingsvcs_configuredbugtracker_change',
                      args=(bug_tracker.pk,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        content = response.content

        # The service's settings are named after the service, and follow
        # the main fields rather than the access control fields.
        self.assertIn(b'Trac Settings', content)

        trac_settings_pos = content.index(b'Trac Settings')
        self.assertLess(content.index(b'name="service_name"'),
                        trac_settings_pos)
        self.assertLess(trac_settings_pos, content.index(b'Access control'))

        # The fields render within the fieldset.
        self.assertGreater(content.index(b'name="trac_url"'),
                           trac_settings_pos)

    def test_change_page_access_control_fieldset(self) -> None:
        """Testing ConfiguredBugTrackerAdmin change page renders the access
        control fieldset
        """
        self.client.login(username='admin', password='admin')

        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'},
            user_conditions=ConditionSet(
                ConditionSet.MODE_ALL, []).serialize())

        url = reverse('admin:hostingsvcs_configuredbugtracker_change',
                      args=(bug_tracker.pk,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'Access control', content)

        # Both access fields render in the section, in order.
        access_control_pos = content.index(b'Access control')
        self.assertGreater(content.index(b'name="accessible_to_everyone"'),
                           access_control_pos)
        self.assertGreater(content.index(b'name="user_conditions_mode"'),
                           content.index(b'name="accessible_to_everyone"'))

    def test_add_page_with_invalid_settings(self) -> None:
        """Testing ConfiguredBugTrackerAdmin add page with invalid service
        settings shows the errors
        """
        self.client.login(username='admin', password='admin')

        url = reverse('admin:hostingsvcs_configuredbugtracker_add')

        response = self.client.post(url, {
            'accessible_to_everyone': True,
            'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
            'display_mode': ConfiguredBugTracker.DISPLAY_MODE_COMPACT,
            'enabled': True,
            'name': 'My Tracker',
            'service_name': 'splat',
            'splat_org_name': '',
            'user_conditions_last_id': '0',
            'user_conditions_mode': ConditionSet.MODE_ALL,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ConfiguredBugTracker.objects.exists())

        content = response.content

        # The admin shows its error banner and the form's general error.
        self.assertIn(b'Please correct the error below.', content)
        self.assertIn(b'Please correct the errors in the Splat settings '
                      b'below.',
                      content)

        # The service stays selected, so its settings are shown again with
        # the field's error.
        self.assertIn(b'<option value="splat" selected>', content)
        self.assertIn(b'id="id_splat_org_name_error"', content)
