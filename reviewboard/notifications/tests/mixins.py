"""Mixins for notifications tests.

Version Added:
    6.0
"""

from typing import List, TYPE_CHECKING

from django.contrib.auth.models import User
from django.core import mail
from djblets.mail.utils import build_email_address_for_user
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.siteconfig import load_site_config, settings_map
from reviewboard.notifications.email.utils import get_email_addresses_for_group
from reviewboard.reviews.models import Group
from reviewboard.testing import TestCase


if TYPE_CHECKING:
    class HelperBase(TestCase):
        pass
else:
    class HelperBase:
        pass


class EmailTestHelper(HelperBase):
    """A mixin for test cases which need to verify e-mail sending."""

    email_siteconfig_settings = {}

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        mail.outbox = []
        self.sender = 'noreply@example.com'
        self._old_email_settings = {}

        if self.email_siteconfig_settings:
            siteconfig = SiteConfiguration.objects.get_current()
            needs_reload = False

            for key, value in self.email_siteconfig_settings.items():
                old_value = siteconfig.get(key)

                if old_value != value:
                    self._old_email_settings[key] = old_value
                    siteconfig.set(key, value)

                    if key in settings_map:
                        needs_reload = True

            if self._old_email_settings:
                siteconfig.save()

                if needs_reload:
                    load_site_config()

    def tearDown(self) -> None:
        """Tear down the test case."""
        super().tearDown()

        if self._old_email_settings:
            siteconfig = SiteConfiguration.objects.get_current()
            needs_reload = False

            for key, value in self._old_email_settings.items():
                self._old_email_settings[key] = siteconfig.get(key)
                siteconfig.set(key, value)

                if key in settings_map:
                    needs_reload = True

            siteconfig.save()

            if needs_reload:
                load_site_config()

    def assertValidRecipients(
        self,
        user_list: List[str],
        group_list: List[str] = [],
    ) -> None:
        """Assert that the e-mail recipient list is as expected.

        Args:
            user_list (list of str):
                The list of usernames for users who should be included on the
                email.

            group_list (list of str, optional):
                The list of group names for groups who should be included on
                the email.
        """
        recipient_list = mail.outbox[0].to + mail.outbox[0].cc
        self.assertEqual(len(recipient_list), len(user_list) + len(group_list))

        for user in user_list:
            self.assertTrue(build_email_address_for_user(
                User.objects.get(username=user)) in recipient_list,
                'user %s was not found in the recipient list' % user)

        groups = Group.objects.filter(name__in=group_list, local_site=None)

        for group in groups:
            for address in get_email_addresses_for_group(group):
                self.assertTrue(
                    address in recipient_list,
                    'group %s was not found in the recipient list' % address)
