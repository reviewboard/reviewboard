"""Tests for reviewboard.hostingsvcs.bug_tracker_forms.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
from djblets.conditions import ConditionSet

from reviewboard.hostingsvcs.bug_tracker_forms import (
    BugTrackerForm,
    get_bug_tracker_service_choices
)
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    HostingServiceAccount,
)
from reviewboard.hostingsvcs.splat import Splat
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from typing import Any


class GetBugTrackerServiceChoicesTests(TestCase):
    """Unit tests for get_bug_tracker_service_choices.

    Version Added:
        9.0
    """

    def test_choices(self) -> None:
        """Testing get_bug_tracker_service_choices"""
        choices = dict(get_bug_tracker_service_choices())

        self.assertIn('splat', choices)
        self.assertIn('custom-bug-tracker', choices)
        self.assertIn('fogbugz', choices)

        # In-repo services are configured through the repository, not
        # through standalone configurations.
        self.assertNotIn('github', choices)
        self.assertNotIn('forgejo', choices)

        # Non-bug-tracker services never appear.
        self.assertNotIn('gerrit', choices)

        # Hidden services are not offered for new configurations.
        self.assertNotIn('versionone', choices)


class BugTrackerFormTests(kgb.SpyAgency, TestCase):
    """Unit tests for BugTrackerForm.

    Version Added:
        9.0
    """

    fixtures = ['test_scmtools']

    def _build_form_data(self, **overrides) -> dict:
        """Return form data for a valid bug tracker.

        Args:
            **overrides (dict):
                Values overriding the defaults.

        Returns:
            dict:
            The form data.
        """
        data = {
            'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
            'enabled': True,
            'name': 'My Tracker',
            'service_name': 'custom-bug-tracker',
            'url_template': 'https://bugs.example.com/%s',
            'user_conditions_mode': ConditionSet.MODE_ALL,
            'user_conditions_last_id': '0',
        }
        data.update(overrides)

        return data

    def _build_conditions_data(
        self,
        value: Any = True,
    ) -> dict[str, Any]:
        """Return form data for a single user condition.

        Args:
            value (object, optional):
                The value for the condition.

        Returns:
            dict:
            The condition's form data.
        """
        return {
            'user_conditions_choice[0]': 'user-is-superuser',
            'user_conditions_last_id': '0',
            'user_conditions_operator[0]': 'is',
            'user_conditions_value[0]': value,
        }

    def test_valid_form(self) -> None:
        """Testing BugTrackerForm with valid data"""
        form = BugTrackerForm(data=self._build_form_data())

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(bug_tracker.name, 'My Tracker')
        self.assertEqual(bug_tracker.service_name, 'custom-bug-tracker')
        self.assertEqual(bug_tracker.settings['url_template'],
                         'https://bugs.example.com/%s')

    def test_repositories_cleared_unless_selected(self) -> None:
        """Testing BugTrackerForm clears repositories unless
        apply_to=selected-repos
        """
        repository = self.create_repository()

        form = BugTrackerForm(data=self._build_form_data(
            repositories=[repository.pk]))

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(bug_tracker.repositories.count(), 0)

        form = BugTrackerForm(data=self._build_form_data(
            apply_to=ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS,
            repositories=[repository.pk]))

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(list(bug_tracker.repositories.all()),
                         [repository])

    def test_invalid_service(self) -> None:
        """Testing BugTrackerForm with an invalid service"""
        form = BugTrackerForm(data=self._build_form_data(
            service_name='xxx-invalid'))

        self.assertFalse(form.is_valid())
        self.assertIn('service_name', form.errors)

    def test_account_service_mismatch(self) -> None:
        """Testing BugTrackerForm with an account on another service"""
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='test-user')

        form = BugTrackerForm(data=self._build_form_data(
            service_name='splat',
            splat_org_name='my-org',
            hosting_account=account.pk))

        self.assertFalse(form.is_valid())
        self.assertIn('hosting_account', form.errors)

    def test_account_required(self) -> None:
        """Testing BugTrackerForm with a service that requires an account"""
        self.spy_on(Splat.is_bug_tracker_account_required,
                    owner=Splat,
                    op=kgb.SpyOpReturn(True))

        form = BugTrackerForm(data=self._build_form_data(
            service_name='splat',
            splat_org_name='my-org'))

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['hosting_account'],
                         ['This service requires a linked account.'])

        account = HostingServiceAccount.objects.create(
            service_name='splat',
            username='test-user')

        form = BugTrackerForm(data=self._build_form_data(
            service_name='splat',
            splat_org_name='my-org',
            hosting_account=account.pk))

        self.assertTrue(form.is_valid(), form.errors)

    def test_hosting_account_options_tag_service(self) -> None:
        """Testing BugTrackerForm renders each account's service"""
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='test-user')

        form = BugTrackerForm()
        html = str(form['hosting_account'])

        self.assertIn(f'value="{account.pk}" data-service="github"', html)

    def test_settings_validation(self) -> None:
        """Testing BugTrackerForm validates settings against the
        service's form
        """
        form = BugTrackerForm(data=self._build_form_data(
            service_name='splat',
            splat_org_name=''))

        self.assertFalse(form.is_valid())
        self.assertIn('splat_org_name', form.settings_form.errors)
        self.assertEqual(
            form.non_field_errors(),
            ['Please correct the errors in the Splat settings below.'])

        form = BugTrackerForm(data=self._build_form_data(
            service_name='splat',
            splat_org_name='my-org'))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['settings']['splat_org_name'],
                         'my-org')

    def test_accessible_to_everyone_clears_conditions(self) -> None:
        """Testing BugTrackerForm with accessible_to_everyone=True clears
        the user conditions
        """
        form = BugTrackerForm(data=self._build_form_data(
            accessible_to_everyone=True,
            **self._build_conditions_data()))

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = ConfiguredBugTracker.objects.get(pk=form.save().pk)
        self.assertEqual(bug_tracker.user_conditions, {
            'conditions': [],
            'mode': ConditionSet.MODE_ALL,
        })

    def test_accessible_to_everyone_ignores_condition_errors(self) -> None:
        """Testing BugTrackerForm with accessible_to_everyone=True ignores
        errors from the hidden user conditions
        """
        form = BugTrackerForm(data=self._build_form_data(
            accessible_to_everyone=True,
            **self._build_conditions_data(value='')))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn('user_conditions', form.errors)

    def test_not_accessible_to_everyone_keeps_conditions(self) -> None:
        """Testing BugTrackerForm with accessible_to_everyone=False stores
        the user conditions
        """
        form = BugTrackerForm(data=self._build_form_data(
            **self._build_conditions_data()))

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = ConfiguredBugTracker.objects.get(pk=form.save().pk)
        self.assertEqual(
            [
                condition['choice']
                for condition in bug_tracker.user_conditions['conditions']
            ],
            ['user-is-superuser'])

    def test_edit_with_user_conditions(self) -> None:
        """Testing BugTrackerForm unchecks accessible_to_everyone for an
        instance with user conditions
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'},
            user_conditions={
                'conditions': [{
                    'choice': 'user-is-superuser',
                    'op': 'is',
                    'value': True,
                }],
                'mode': ConditionSet.MODE_ALL,
            })

        form = BugTrackerForm(instance=bug_tracker)

        self.assertFalse(form.initial['accessible_to_everyone'])

    def test_edit_with_empty_user_conditions(self) -> None:
        """Testing BugTrackerForm renders an instance with empty user
        conditions
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat',
            settings={'splat_org_name': 'my-org'})

        form = BugTrackerForm(instance=bug_tracker)

        # Empty stored conditions ({}) are normalized so the conditions
        # widget can render them.
        self.assertEqual(form.initial['user_conditions'], {
            'conditions': [],
            'mode': ConditionSet.MODE_ALL,
        })

        # Rendering must not crash.
        form.as_p()

    def test_edit_preserves_unmanaged_settings(self) -> None:
        """Testing BugTrackerForm preserves settings keys the service's
        form does not manage
        """
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='splat',
            settings={
                'legacy_key': 'kept',
                'splat_org_name': 'my-org',
            })

        form = BugTrackerForm(
            data=self._build_form_data(service_name='splat',
                                       splat_org_name='new-org'),
            instance=bug_tracker)

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(bug_tracker.settings, {
            'display_mode': ConfiguredBugTracker.DISPLAY_MODE_COMPACT,
            'legacy_key': 'kept',
            'splat_org_name': 'new-org',
        })

    def test_display_mode(self) -> None:
        """Testing BugTrackerForm stores the display mode in the settings"""
        form = BugTrackerForm(data=self._build_form_data(
            display_mode=ConfiguredBugTracker.DISPLAY_MODE_DETAILED))

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(bug_tracker.display_mode,
                         ConfiguredBugTracker.DISPLAY_MODE_DETAILED)
        self.assertEqual(
            bug_tracker.settings[ConfiguredBugTracker.DISPLAY_MODE_KEY],
            ConfiguredBugTracker.DISPLAY_MODE_DETAILED)

    def test_display_mode_initial(self) -> None:
        """Testing BugTrackerForm shows the stored display mode"""
        bug_tracker = ConfiguredBugTracker.objects.create(
            name='My Tracker',
            service_name='custom-bug-tracker',
            settings={
                'display_mode': ConfiguredBugTracker.DISPLAY_MODE_DETAILED,
                'url_template': 'https://bugs.example.com/%s',
            })

        form = BugTrackerForm(instance=bug_tracker)

        self.assertEqual(form.initial['display_mode'],
                         ConfiguredBugTracker.DISPLAY_MODE_DETAILED)

    def test_display_mode_with_invalid_value(self) -> None:
        """Testing BugTrackerForm with an invalid display mode"""
        form = BugTrackerForm(data=self._build_form_data(
            display_mode='xxx-invalid'))

        self.assertFalse(form.is_valid())
        self.assertIn('display_mode', form.errors)
