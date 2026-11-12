"""Unit tests for JIRA forms.

Version Added:
    9.0:
    Split up ``reviewboard.hostingsvcs.test_jira``.
"""

from __future__ import annotations

from djblets.conditions import ConditionSet

from reviewboard.hostingsvcs.bug_tracker_forms import BugTrackerForm
from reviewboard.hostingsvcs.jira.forms import (
    JIRAAuthForm,
    JIRABugTrackerConfigForm,
)
from reviewboard.hostingsvcs.jira.service import JIRA
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.hostingsvcs.tests.jira.base import JIRATestCase


class JIRAAuthFormTests(JIRATestCase):
    """Unit tests for JIRAAuthForm.

    Version Added:
        9.0
    """

    def test_get_hosting_url(self) -> None:
        """Testing JIRAAuthForm.get_hosting_url returns the server URL"""
        form = JIRAAuthForm(
            data={
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mytoken',
                'jira_server_url': 'https://jira.example.com/',
            },
            hosting_service_cls=JIRA)

        self.assertTrue(form.is_valid(), form.errors)

        # Trailing slashes are stripped.
        self.assertEqual(form.get_hosting_url(), 'https://jira.example.com')

    def test_save_with_same_username_on_two_servers(self) -> None:
        """Testing JIRAAuthForm.save with the same username on two servers
        creates two accounts
        """
        accounts = []

        for server_url in ('https://one.example.com',
                           'https://two.example.com'):
            form = JIRAAuthForm(
                data={
                    'hosting_account_username': 'myuser',
                    'hosting_account_password': 'mytoken',
                    'jira_server_url': server_url,
                },
                hosting_service_cls=JIRA)

            self.assertTrue(form.is_valid(), form.errors)
            accounts.append(form.save())

        self.assertNotEqual(accounts[0].pk, accounts[1].pk)

        for account in accounts:
            account.refresh_from_db()

        self.assertEqual(accounts[0].hosting_url, 'https://one.example.com')
        self.assertEqual(accounts[1].hosting_url, 'https://two.example.com')


class JIRAAuthFormDeploymentTests(JIRATestCase):
    """Unit tests for JIRAAuthForm deployment handling.

    Version Added:
        9.0
    """

    def test_cloud_composes_server_url(self) -> None:
        """Testing JIRAAuthForm with JIRA Cloud composes the server URL
        from the site name
        """
        form = JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
                'jira_cloud_site': 'myteam',
                'hosting_account_username': 'me@example.com',
                'hosting_account_password': 'mytoken',
            },
            hosting_service_cls=JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_hosting_url(),
                         'https://myteam.atlassian.net')

    def test_cloud_normalizes_pasted_urls(self) -> None:
        """Testing JIRAAuthForm with JIRA Cloud normalizes pasted URLs
        down to the site name
        """
        form = JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
                'jira_cloud_site': 'https://MyTeam.atlassian.net/jira',
                'hosting_account_username': 'me@example.com',
                'hosting_account_password': 'mytoken',
            },
            hosting_service_cls=JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['jira_server_url'],
                         'https://myteam.atlassian.net')

    def test_cloud_requires_site(self) -> None:
        """Testing JIRAAuthForm with JIRA Cloud requires the site name"""
        form = JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
                'hosting_account_username': 'me@example.com',
                'hosting_account_password': 'mytoken',
            },
            hosting_service_cls=JIRA)

        self.assertFalse(form.is_valid())
        self.assertIn('jira_cloud_site', form.errors)

    def test_data_center_requires_server_url(self) -> None:
        """Testing JIRAAuthForm defaults to Data Center and requires the
        server URL
        """
        form = JIRAAuthForm(
            data={
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=JIRA)

        self.assertFalse(form.is_valid())
        self.assertIn('jira_server_url', form.errors)

    def test_data_center_with_invalid_server_url(self) -> None:
        """Testing JIRAAuthForm with Data Center rejects server URLs that
        are not full HTTP or HTTPS URLs
        """
        for server_url in ('jira.example.com',
                           'ftp://jira.example.com',
                           'https://'):
            with self.subTest(server_url=server_url):
                form = JIRAAuthForm(
                    data={
                        'jira_deployment': 'dc',
                        'jira_server_url': server_url,
                        'hosting_account_username': 'myuser',
                        'hosting_account_password': 'mypass',
                    },
                    hosting_service_cls=JIRA)

                self.assertFalse(form.is_valid())
                self.assertIn('jira_server_url', form.errors)

    def test_data_center_with_intranet_server_url(self) -> None:
        """Testing JIRAAuthForm with Data Center accepts single-label
        intranet hostnames with ports
        """
        form = JIRAAuthForm(
            data={
                'jira_deployment': 'dc',
                'jira_server_url': 'http://jira:8080/',
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'mypass',
            },
            hosting_service_cls=JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_hosting_url(), 'http://jira:8080')

    def test_required_flags_per_deployment(self) -> None:
        """Testing JIRAAuthForm marks the chosen deployment's URL field
        required
        """
        form = JIRAAuthForm(
            data={
                'jira_deployment': 'cloud',
            },
            hosting_service_cls=JIRA)
        self.assertTrue(form.fields['jira_cloud_site'].required)
        self.assertFalse(form.fields['jira_server_url'].required)

        form = JIRAAuthForm(
            data={
                'jira_deployment': 'dc',
            },
            hosting_service_cls=JIRA)
        self.assertTrue(form.fields['jira_server_url'].required)
        self.assertFalse(form.fields['jira_cloud_site'].required)


class JIRARequiresAccountTests(JIRATestCase):
    """Unit tests for JIRA's account requirement on configurations.

    Version Added:
        9.0
    """

    def test_config_requires_account(self) -> None:
        """Testing JIRA bug tracker configurations require an account"""
        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'name': 'My Tracker',
                'service_name': 'jira',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            })

        self.assertFalse(form.is_valid())
        self.assertIn('hosting_account', form.errors)

    def test_legacy_config_grandfathered(self) -> None:
        """Testing migrated legacy JIRA configurations stay editable
        without an account
        """
        bug_tracker = self.create_bug_tracker(
            name='Legacy JIRA',
            service_name='jira',
            settings={
                'jira_url': 'https://jira.example.com',
            })

        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'name': 'Legacy JIRA',
                'service_name': 'jira',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            },
            instance=bug_tracker)

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertIsNone(bug_tracker.hosting_account)

        # The legacy server URL is preserved.
        self.assertEqual(bug_tracker.settings['jira_url'],
                         'https://jira.example.com')

    def test_config_with_account(self) -> None:
        """Testing JIRA bug tracker configurations save with an account"""
        account = self.create_hosting_account(use_url=True)

        form = BugTrackerForm(
            data={
                'apply_to': ConfiguredBugTracker.APPLY_TO_ALL,
                'enabled': True,
                'hosting_account': account.pk,
                'name': 'My Tracker',
                'service_name': 'jira',
                'user_conditions_last_id': '0',
                'user_conditions_mode': ConditionSet.MODE_ALL,
            })

        self.assertTrue(form.is_valid(), form.errors)

        bug_tracker = form.save()
        self.assertEqual(bug_tracker.hosting_account, account)


class JIRABugTrackerConfigFormTests(JIRATestCase):
    """Unit tests for JIRABugTrackerConfigForm.

    Version Added:
        9.0
    """

    def test_project_normalized(self) -> None:
        """Testing JIRABugTrackerConfigForm normalizes the project key"""
        form = JIRABugTrackerConfigForm(
            data={
                'jira_project': ' eng ',
            },
            hosting_service_cls=JIRA)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['jira_project'], 'ENG')

    def test_invalid_project(self) -> None:
        """Testing JIRABugTrackerConfigForm with an invalid project key"""
        form = JIRABugTrackerConfigForm(
            data={
                'jira_project': 'not a key',
            },
            hosting_service_cls=JIRA)

        self.assertFalse(form.is_valid())
        self.assertIn('jira_project', form.errors)

    def test_is_bug_tracker_config_form(self) -> None:
        """Testing JIRA uses JIRABugTrackerConfigForm for configs"""
        self.assertIs(JIRA.bug_tracker_config_form,
                      JIRABugTrackerConfigForm)
