"""Unit tests for reviewboard.admin.forms.SSHSettingsForm."""

from __future__ import unicode_literals

import os
import shutil
import tempfile

from django.utils.encoding import force_str

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.ssh.client import SSHClient
from reviewboard.testing.testcase import TestCase


class SSHSettingsFormTestCase(TestCase):
    """Unit tests for reviewboard.admin.forms.SSHSettingsForm."""

    fixtures = ['test_users']

    def setUp(self):
        """Set up this test case."""
        super(SSHSettingsFormTestCase, self).setUp()

        # Setup temp directory to prevent the original ssh related
        # configurations been overwritten.
        self.old_home = os.getenv('HOME')
        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')
        os.environ[str('RBSSH_ALLOW_AGENT')] = str('0')
        self._set_home(self.tempdir)

        self.ssh_client = SSHClient()

    def tearDown(self):
        """Tear down this test case."""
        super(SSHSettingsFormTestCase, self).tearDown()

        self._set_home(self.old_home)

        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def _set_home(self, homedir):
        """Set the $HOME environment variable."""
        os.environ[str('HOME')] = force_str(homedir)

    def test_generate_key(self):
        """Testing SSHSettingsForm POST with generate_key=1"""
        # Should have no ssh key at this point.
        self.assertIsNone(self.ssh_client.get_user_key())

        # Send post request with 'generate_key' = 1.
        self.client.login(username='admin', password='admin')
        response = self.client.post(local_site_reverse('settings-ssh'), {
            'generate_key': 1,
        })

        # On success, the form returns HTTP 302 (redirect).
        self.assertEqual(response.status_code, 302)

        # Check whether the key has been created.
        self.assertIsNotNone(self.ssh_client.get_user_key())

    def test_delete_key(self):
        """Testing SSHSettingsForm POST with delete_key=1"""
        # Should have no ssh key at this point, generate one.
        self.assertIsNone(self.ssh_client.get_user_key())
        self.ssh_client.generate_user_key()
        self.assertIsNotNone(self.ssh_client.get_user_key())

        # Send post request with 'delete_key' = 1.
        self.client.login(username='admin', password='admin')
        response = self.client.post(local_site_reverse('settings-ssh'), {
            'delete_key': 1,
        })

        # On success, the form returns HTTP 302 (redirect).
        self.assertEqual(response.status_code, 302)

        # Check whether the key has been deleted.
        self.assertIsNone(self.ssh_client.get_user_key())
