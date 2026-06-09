"""Unit tests for reviewboard.admin.views.EditServiceCredentialsView."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.urls import reverse

from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.testing import TestCase
from reviewboard.testing.hosting_services import TestService

if TYPE_CHECKING:
    from collections.abc import Sequence


class EditServiceCredentialsViewTests(TestCase):
    """Unit tests for EditServiceCredentialsView."""

    fixtures: Sequence[str] = ['test_users', 'test_scmtools']

    def setUp(self) -> None:
        """Set up state for the test."""
        super().setUp()

        hosting_service_registry.register(TestService)

        self.account = HostingServiceAccount.objects.create(
            service_name='test',
            username='myuser')

    def tearDown(self) -> None:
        """Tear down state for the test."""
        hosting_service_registry.unregister(TestService)

        super().tearDown()

    def test_get(self) -> None:
        """Testing EditServiceCredentialsView GET returns the pre-filled form
        """
        self.client.login(username='admin', password='admin')
        response = self.client.get(self._get_url('test', self.account.pk))

        self.assertEqual(response.status_code, 200)

        content = response.content
        self.assertIn(b'hosting_account_username', content)

        # The form is pre-populated from the account, and the dialog title is
        # set for the wizard.
        self.assertIn(b'value="myuser"', content)
        self.assertIn(b'data-wizard-title="Edit Credentials"', content)

    def test_get_with_unknown_account(self) -> None:
        """Testing EditServiceCredentialsView GET with an unknown account"""
        self.client.login(username='admin', password='admin')
        response = self.client.get(self._get_url('test', 999999))

        self.assertEqual(response.status_code, 404)

    def test_get_with_mismatched_service(self) -> None:
        """Testing EditServiceCredentialsView GET with a service that does not
        match the account
        """
        self.client.login(username='admin', password='admin')
        response = self.client.get(self._get_url('github', self.account.pk))

        self.assertEqual(response.status_code, 404)

    def test_get_with_unknown_service(self) -> None:
        """Testing EditServiceCredentialsView GET with an unknown service"""
        self.client.login(username='admin', password='admin')
        response = self.client.get(
            self._get_url('not-a-real-service', self.account.pk))

        self.assertEqual(response.status_code, 404)

    def test_get_requires_staff(self) -> None:
        """Testing EditServiceCredentialsView GET requires a staff member"""
        self.client.login(username='doc', password='doc')
        response = self.client.get(self._get_url('test', self.account.pk))

        self.assertEqual(response.status_code, 302)

    def test_get_requires_mutable_account(self) -> None:
        """Testing EditServiceCredentialsView GET requires a user who can
        modify the account
        """
        # A staff user without the change permission cannot modify the account.
        User.objects.create_user(username='staffuser',
                                 password='staffuser',
                                 email='staffuser@example.com',
                                 is_staff=True)

        self.client.login(username='staffuser', password='staffuser')
        response = self.client.get(self._get_url('test', self.account.pk))

        self.assertEqual(response.status_code, 404)

    def test_post_updates_and_authorizes(self) -> None:
        """Testing EditServiceCredentialsView POST updates and re-authorizes
        the account
        """
        self.client.login(username='admin', password='admin')
        response = self.client.post(
            self._get_url('test', self.account.pk),
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'newpass',
            })

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertTrue(rsp['success'])
        self.assertEqual(rsp['redirect'], reverse('connected-services-list'))

        account = HostingServiceAccount.objects.get(pk=self.account.pk)
        self.assertTrue(account.is_authorized)

    def test_post_with_authorization_error(self) -> None:
        """Testing EditServiceCredentialsView POST surfaces an
        AuthorizationError
        """
        self.client.login(username='admin', password='admin')
        response = self.client.post(
            self._get_url('test', self.account.pk),
            {
                'hosting_account_username': 'baduser',
                'hosting_account_password': 'mypass',
            })

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertFalse(rsp['success'])
        self.assertIn('Unable to link the account', rsp['html'])

    def test_post_with_invalid_form(self) -> None:
        """Testing EditServiceCredentialsView POST with a missing required
        field
        """
        self.client.login(username='admin', password='admin')
        response = self.client.post(
            self._get_url('test', self.account.pk),
            {
                'hosting_account_username': 'myuser',
            })

        self.assertEqual(response.status_code, 200)

        rsp = json.loads(response.content)
        self.assertFalse(rsp['success'])

    def test_post_requires_staff(self) -> None:
        """Testing EditServiceCredentialsView POST requires a staff member"""
        self.client.login(username='doc', password='doc')
        response = self.client.post(
            self._get_url('test', self.account.pk),
            {
                'hosting_account_username': 'myuser',
                'hosting_account_password': 'newpass',
            })

        self.assertEqual(response.status_code, 302)

    def _get_url(
        self,
        service_id: str,
        account_id: int,
    ) -> str:
        """Return the edit-credentials URL for an account.

        Args:
            service_id (str):
                The ID of the hosting service.

            account_id (int):
                The ID of the account.

        Returns:
            str:
            The edit-credentials URL.
        """
        return reverse('connected-services-account-edit-credentials',
                       kwargs={
                           'service_id': service_id,
                           'account_id': account_id,
                       })
