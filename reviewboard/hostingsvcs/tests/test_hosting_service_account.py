"""Unit tests for reviewboard.hostingsvcs.models.HostingServiceAccount.

Version Added:
    5.0.1
"""

from reviewboard.hostingsvcs.errors import MissingHostingServiceError
from reviewboard.hostingsvcs.github import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.testing import TestCase


class HostingServiceAccountTests(TestCase):
    """Unit tests for HostingServiceAccount."""

    def test_service(self):
        """Testing HostingServiceAccount.service"""
        account = HostingServiceAccount.objects.create(
            service_name=GitHub.hosting_service_id,
            username='user1',
            visible=True)

        self.assertIsInstance(account.service, GitHub)

    def test_service_bad_service_name(self):
        """Testing HostingServiceAccount.service with a service name that does
        not match any service in the registry
        """

        account = HostingServiceAccount.objects.create(
            service_name='blah',
            username='user1',
            visible=True)
        message = ('The hosting service "blah" could not be loaded. An '
                   'administrator should ensure all necessary packages and '
                   'extensions are installed.')

        with self.assertRaisesMessage(MissingHostingServiceError, message):
            account.service
