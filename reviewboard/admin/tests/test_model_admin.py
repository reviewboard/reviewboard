"""Unit tests for reviewboard.admin.model_admin.ModelAdmin.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.urls import reverse
from djblets.conditions import ConditionSet

from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from typing import Any


class ModelAdminTests(TestCase):
    """Unit tests for ModelAdmin.

    These use the bug tracker add page, since it's a simple model with
    a stock admin add view.

    Version Added:
        9.0
    """

    fixtures = ['test_users']

    def test_add_page_with_next(self) -> None:
        """Testing ModelAdmin add page with ?next= renders a hidden next
        field
        """
        self.client.login(username='admin', password='admin')

        response = self.client.get(
            reverse('admin:hostingsvcs_configuredbugtracker_add'),
            {'next': '/admin/connected-services/'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<input type="hidden" name="next" '
            b'value="/admin/connected-services/">',
            response.content)

    def test_add_page_without_next(self) -> None:
        """Testing ModelAdmin add page without ?next= has no next field"""
        self.client.login(username='admin', password='admin')

        response = self.client.get(
            reverse('admin:hostingsvcs_configuredbugtracker_add'))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'name="next"', response.content)

    def test_response_add_with_next(self) -> None:
        """Testing ModelAdmin.response_add with a safe next URL redirects
        there
        """
        self.client.login(username='admin', password='admin')

        response = self.client.post(
            reverse('admin:hostingsvcs_configuredbugtracker_add'),
            self._make_post_data(next='/admin/connected-services/'))

        self.assertRedirects(response, '/admin/connected-services/',
                             fetch_redirect_response=False)
        self.assertTrue(ConfiguredBugTracker.objects.exists())

    def test_response_add_with_unsafe_next(self) -> None:
        """Testing ModelAdmin.response_add with an external next URL ignores
        it
        """
        self.client.login(username='admin', password='admin')

        response = self.client.post(
            reverse('admin:hostingsvcs_configuredbugtracker_add'),
            self._make_post_data(next='https://evil.example/'))

        self.assertRedirects(
            response,
            reverse('admin:hostingsvcs_configuredbugtracker_changelist'),
            fetch_redirect_response=False)

    def test_response_add_with_next_and_add_another(self) -> None:
        """Testing ModelAdmin.response_add with next and "Save and add
        another" keeps the default behavior
        """
        self.client.login(username='admin', password='admin')

        response = self.client.post(
            reverse('admin:hostingsvcs_configuredbugtracker_add'),
            self._make_post_data(next='/admin/connected-services/',
                                 _addanother='1'))

        self.assertRedirects(
            response,
            reverse('admin:hostingsvcs_configuredbugtracker_add'),
            fetch_redirect_response=False)

    def test_change_page_with_next(self) -> None:
        """Testing ModelAdmin change page with ?next= renders a hidden next
        field
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')

        self.client.login(username='admin', password='admin')

        response = self.client.get(
            reverse('admin:hostingsvcs_configuredbugtracker_change',
                    args=(bug_tracker.pk,)),
            {'next': '/admin/connected-services/'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<input type="hidden" name="next" '
            b'value="/admin/connected-services/">',
            response.content)

    def test_response_change_with_next(self) -> None:
        """Testing ModelAdmin.response_change with a safe next URL redirects
        there
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')

        self.client.login(username='admin', password='admin')

        response = self.client.post(
            reverse('admin:hostingsvcs_configuredbugtracker_change',
                    args=(bug_tracker.pk,)),
            self._make_post_data(name='New Name',
                                 next='/admin/connected-services/'))

        self.assertRedirects(response, '/admin/connected-services/',
                             fetch_redirect_response=False)

        bug_tracker.refresh_from_db()
        self.assertEqual(bug_tracker.name, 'New Name')

    def test_response_change_with_unsafe_next(self) -> None:
        """Testing ModelAdmin.response_change with an external next URL
        ignores it
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')

        self.client.login(username='admin', password='admin')

        response = self.client.post(
            reverse('admin:hostingsvcs_configuredbugtracker_change',
                    args=(bug_tracker.pk,)),
            self._make_post_data(next='https://evil.example/'))

        self.assertRedirects(
            response,
            reverse('admin:hostingsvcs_configuredbugtracker_changelist'),
            fetch_redirect_response=False)

    def test_response_change_with_next_and_continue(self) -> None:
        """Testing ModelAdmin.response_change with next and "Save and
        continue editing" keeps the default behavior
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')
        change_url = reverse('admin:hostingsvcs_configuredbugtracker_change',
                             args=(bug_tracker.pk,))

        self.client.login(username='admin', password='admin')

        response = self.client.post(
            change_url,
            self._make_post_data(next='/admin/connected-services/',
                                 _continue='1'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(change_url))

    def test_change_page_with_next_delete_link(self) -> None:
        """Testing ModelAdmin change page with ?next= passes next to the
        Delete link
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')

        self.client.login(username='admin', password='admin')

        response = self.client.get(
            reverse('admin:hostingsvcs_configuredbugtracker_change',
                    args=(bug_tracker.pk,)),
            {'next': '/admin/connected-services/'})

        delete_url = reverse('admin:hostingsvcs_configuredbugtracker_delete',
                             args=(bug_tracker.pk,))

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f'href="{delete_url}?next=%2Fadmin%2Fconnected-services%2F"'
            .encode('utf-8'),
            response.content)

    def test_delete_page_with_next(self) -> None:
        """Testing ModelAdmin delete page with ?next= renders a hidden next
        field
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')

        self.client.login(username='admin', password='admin')

        response = self.client.get(
            reverse('admin:hostingsvcs_configuredbugtracker_delete',
                    args=(bug_tracker.pk,)),
            {'next': '/admin/connected-services/'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<input type="hidden" name="next" '
            b'value="/admin/connected-services/">',
            response.content)

    def test_response_delete_with_next(self) -> None:
        """Testing ModelAdmin.response_delete with a safe next URL redirects
        there
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')

        self.client.login(username='admin', password='admin')

        response = self.client.post(
            reverse('admin:hostingsvcs_configuredbugtracker_delete',
                    args=(bug_tracker.pk,)),
            {
                'next': '/admin/connected-services/',
                'post': 'yes',
            })

        self.assertRedirects(response, '/admin/connected-services/',
                             fetch_redirect_response=False)
        self.assertFalse(ConfiguredBugTracker.objects.exists())

    def test_response_delete_with_unsafe_next(self) -> None:
        """Testing ModelAdmin.response_delete with an external next URL
        ignores it
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat')

        self.client.login(username='admin', password='admin')

        response = self.client.post(
            reverse('admin:hostingsvcs_configuredbugtracker_delete',
                    args=(bug_tracker.pk,)),
            {
                'next': 'https://evil.example/',
                'post': 'yes',
            })

        self.assertRedirects(
            response,
            reverse('admin:hostingsvcs_configuredbugtracker_changelist'),
            fetch_redirect_response=False)

    def _make_post_data(
        self,
        **kwargs,
    ) -> dict[str, Any]:
        """Return POST data for a valid bug tracker.

        Args:
            **kwargs (dict):
                Additional fields to include.

        Returns:
            dict:
            The POST data.
        """
        return {
            'accessible_to_everyone': True,
            'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
            'display_mode': ConfiguredBugTracker.DISPLAY_MODE_COMPACT,
            'enabled': True,
            'name': 'My Tracker',
            'service_name': 'splat',
            'splat_org_name': 'myorg',
            'user_conditions_last_id': '0',
            'user_conditions_mode': ConditionSet.MODE_ALL,
            **kwargs,
        }
