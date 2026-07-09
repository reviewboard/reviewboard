"""Base class for GitHub tests.

Version Added:
    9.0:
    Split out from reviewboard.hostingsvcs.tests.test_github
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.messages import Message
from django.contrib.messages.test import MessagesTestMixin

from reviewboard.hostingsvcs.github.accounts import InstallationStatus
from reviewboard.hostingsvcs.github.service import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.crypto_utils import encrypt_password
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import ClassVar, Literal

    from django.test.client import _MonkeyPatchedWSGIResponse


class GitHubTestCase(MessagesTestMixin, HostingServiceTestCase[GitHub]):
    """Base class for GitHub test suites."""

    service_name = 'github'

    default_account_data: Mapping[str, str] = {
        'personal_token': encrypt_password('abc123'),
    }

    default_repository_extra_data: Mapping[str, str] = {
        'repository_plan': 'public',
        'github_public_repo_name': 'myrepo',
    }

    #: The installation ID stored on the test account.
    #:
    #: Version Added:
    #:     9.0
    installation_id = 99

    #: The app ID stored on the test account.
    #:
    #: Version Added:
    #:     9.0
    app_id = 12345

    #: The webhook secret stored on the test app-record account.
    webhook_secret = 'topsecret'

    #: The private key to use for signing.
    #:
    #: Version Added:
    #:     9.0
    _private_key: ClassVar[rsa.RSAPrivateKey]

    #: The encoded private key.
    #:
    #: Version Added:
    #:     9.0
    _pem: ClassVar[bytes]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case class."""
        super().setUpClass()

        cls._private_key = rsa.generate_private_key(public_exponent=65537,
                                                    key_size=2048)
        cls._pem = cls._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption())

    def _assert_error_redirect(
        self,
        response: _MonkeyPatchedWSGIResponse,
        message: str,
    ) -> None:
        """Assert a response redirects to the list with an error message.

        Version Added:
            9.0

        Args:
            response (django.http.HttpResponse):
                The response returned by the view.

            message (str):
                The error message expected to be shown.
        """
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
                         local_site_reverse('connected-services-list'))

        self.assertMessages(response, [Message(40, message)])

    def _create_app_record_account(self) -> HostingServiceAccount:
        """Return a hidden app-record account holding the app credentials.

        Version Added:
            9.0

        Returns:
            reviewboard.hostingsvcs.models.HostingServiceAccount:
            The new app-record account.
        """
        # The PEM is Base64-encoded before encryption, matching how the
        # manifest callback stores it.
        private_key = encrypt_password(
            base64.b64encode(self._pem).decode('ascii'))

        client_secret = encrypt_password('client-secret')
        webhook_secret = encrypt_password(self.webhook_secret)

        return self.create_hosting_account(data={
            'github_app': {
                'app_id': self.app_id,
                'app_slug': 'rb-app',
                'client_id': 'client-id',
                'client_secret': client_secret,
                'private_key': private_key,
                'role': 'app',
                'webhook_secret': webhook_secret,
            },
        })

    def _create_app_installation_account(
        self,
        app_account: (HostingServiceAccount | None) = None,
        *,
        owner_id: int = 555,
        owner_login: str = 'myorg',
        owner_type: Literal['user', 'organization'] = 'organization',
        repository_selection: str = 'all',
        status: (str | None) = None,
    ) -> HostingServiceAccount:
        """Return an installation account referencing a new app record.

        Version Added:
            9.0

        Args:
            app_account (reviewboard.hostingsvcs.models.HostingServiceAccount,
                         optional):
                The app record account to link to.

            owner_id (int, optional):
                The stable owner ID to store.

            owner_login (str, optional):
                The owner login to set.

            owner_type (str, optional):
                The owner type to set.

            repository_selection (str, optional):
                The repository selection to set.

            status (str, optional):
                An installation status to store, if any.

        Returns:
            reviewboard.hostingsvcs.models.HostingServiceAccount:
            The new installation account.
        """
        if app_account is None:
            app_account = self._create_app_record_account()

        # This must match the shape the install wizard creates: it stores
        # hosting_url='' and the owner login as the username, and
        # find_installation_account() matches on that hosting_url.
        return HostingServiceAccount.objects.create(
            service_name='github',
            username=owner_login,
            hosting_url='',
            data={
                'github_app': {
                    'app_account_id': app_account.pk,
                    'installation_id': self.installation_id,
                    'owner_id': owner_id,
                    'owner_login': owner_login,
                    'owner_type': owner_type,
                    'repository_selection': repository_selection,
                    'role': 'installation',
                    'status': status or InstallationStatus.ACTIVE,
                },
            })
