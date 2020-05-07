from __future__ import unicode_literals

import io
import os
import shutil
import tempfile

import paramiko
from django.utils import six
from django.utils.encoding import force_str
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import cached_property

from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import UnsupportedSSHKeyError
from reviewboard.ssh.storage import (FileSSHStorage,
                                     get_ssh_storage_backend_path,
                                     set_ssh_storage_backend_path)
from reviewboard.ssh.utils import humanize_key
from reviewboard.testing.testcase import TestCase


rsa_key_blob = """-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQCsElbDaXtsLctXBQVu8N55ptQ3s1IDBP1nqL/0J3+L70DMjRXa
tVB9uPeZOPDJrWgu7Gn2k48oRkGdl+9+WtnaNvgb6jC9TU4gNXKtBeq/Q/NQgtLs
jBnhczMC90PnM+Bvq6TyDaufXqYP7w8Xk1TsW7nz58HMsIPOEA8Ajx+3PwIDAQAB
AoGAXgjbn4j6qSDRmemlkX5Spnq0SQhXTk0gytBermgTfP6wE9kaU1548Wvu665B
cIWyhMowEk+LkX/rhdstR4kQuhkgGtkO78YLjqmHPHuMYRn4Ea/1xdSYA1qOnLWR
GNbnnvYY9/YR5KhsmFbuG5wfA2V0Bw3ULm02jgGuCV7Y5okCQQDgN4md1qXmkO9S
XgfftE1r4ByqFwWzzFRTAFEFN2jULUwmM3B+L+1MUGjuKBk/tjfdv7QBPRJoO6xz
peG00nHNAkEAxHaIyIaaK9ajrke+tiSDZYs9HCnYHiVH2+3hg1vTHIrgO8VkjA93
A40Qaol+7dKzsC5TPll3k2uGnY+lo/RxOwJAI+RgEDc7KXSMCvhodEQNnLYsgIHc
9NJBsWO8lIQxML3rkbXsTRbo+q1ojq82k39c5A97BjO7jZn32i90uRhzBQJBALcQ
KHaJjeDpeM1thtRcA5+79a5ngzzbyjCxYSAwkO+YrEalsQIdau2BJVnQUtiyK8Mv
91syrIxOdjoc3uB+Zn8CQQCpvbEXIU/76MH/yDmgOk4+R8qo/yU6cgn7PTCWzGL7
SK+fSBGKFq+n2FxQIt9OWswQ+wbvq9jmJmLCGxuUSMPu
-----END RSA PRIVATE KEY-----
"""

dsa_key_blob = """-----BEGIN DSA PRIVATE KEY-----
MIIBugIBAAKBgQDddn3Hr3guZXLlmRLlneT0HSUa3gx3dYVCMr/b7UXu7gMxG919
C6Tzjk300tgxDpTnmq1OVwoQA44tIFYlxvw9KnxttnPe+Ny7nocGDApBXMLfaZLN
QbAlsBxTEVPB6CxtF9srVs3SXNbQddGI/PidEK00Fe1jwNnv0aC43LCFFwIVAM/d
qNnjATC1+ub/4dwnbO4sL2zlAoGAVM/g9ePoFxdldGKh40SaNHjkSw9GMo72HioD
KkSBNJ2Es/8ppX6Wkgi3WWZNsMruTTnVyWPqPIPpt58yqyMYtqSVVmoK7ihyxbxW
dUtG9rrNwo9/OqfvUxGFYE0suBnNR29lKKlWT+Sk5Cjd+5BpGZ6ptaxgvkYDFkyX
JrWBXzUCgYA0u51vP+h9InIxYxAr64Y72rungv/2Y409vvEbnBDK42na8SJ4fNZF
CUa4Y8KQ8bUaKyBbiXz/r+zbzA7D5kxsdBMeUmHjQhMIGiMxvGfPLw/9jWR2pcFH
DPCGtVEaccnAOCgOEfgRGq5MG/i0YCFj7AIdLQchGiUDVPJNFK8KNwIUUDs/Ac/t
NnIFhSieTpeXxmozkks=
-----END DSA PRIVATE KEY-----
"""


class TestKeys(object):
    """Keys used for unit tests.

    This is used to access keys across any and all unit tests that need them,
    in a way that reduces overhead by constructing each key only once and
    only on first access, caching it for future lookups.
    """

    @cached_property
    def rsa_key(self):
        """A stable RSA key for testing."""
        return paramiko.RSAKey.from_private_key(io.StringIO(rsa_key_blob))

    @cached_property
    def dsa_key(self):
        """A stable DSA key for testing."""
        return paramiko.DSSKey.from_private_key(io.StringIO(dsa_key_blob))

    @cached_property
    def rsa_key_b64(self):
        """Base64 encoding for the RSA key."""
        return test_keys.rsa_key.get_base64()

    @cached_property
    def dsa_key_b64(self):
        """Base64 encoding for the DSA key."""
        return test_keys.dsa_key.get_base64()


test_keys = TestKeys()


class SSHTestCase(TestCase):
    def setUp(self):
        super(SSHTestCase, self).setUp()

        self.old_home = os.getenv('HOME')
        self.tempdir = None
        os.environ[str('RBSSH_ALLOW_AGENT')] = str('0')
        FileSSHStorage._ssh_dir = None

    def tearDown(self):
        super(SSHTestCase, self).tearDown()

        self._set_home(self.old_home)

        if self.tempdir:
            shutil.rmtree(self.tempdir)

    @property
    def key1(self):
        """Legacy alias for TestKeys.rsa_key."""
        return test_keys.rsa_key

    @property
    def key2(self):
        """Legacy alias for TestKeys.dsa_key."""
        return test_keys.dsa_key

    @property
    def key1_b64(self):
        """Legacy alias for TestKeys.rsa_key_b64."""
        return test_keys.rsa_key_b64

    @property
    def key2_b64(self):
        """Legacy alias for TestKeys.dsa_key_b64."""
        return test_keys.dsa_key_b64

    def _set_home(self, homedir):
        os.environ[str('HOME')] = force_str(homedir)


class FileSSHStorageTests(SSHTestCase):
    """Unit tests for FileSSHStorage."""
    def setUp(self):
        super(FileSSHStorageTests, self).setUp()

        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')
        self._set_home(self.tempdir)

    def test_get_ssh_dir_with_dot_ssh(self):
        """Testing FileSSHStorage.get_ssh_dir with ~/.ssh"""
        sshdir = os.path.join(self.tempdir, '.ssh')

        storage = FileSSHStorage()
        self.assertEqual(storage.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_ssh(self):
        """Testing FileSSHStorage.get_ssh_dir with ~/ssh"""
        sshdir = os.path.join(self.tempdir, 'ssh')
        os.mkdir(sshdir, 0o700)

        storage = FileSSHStorage()
        self.assertEqual(storage.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_dot_ssh_and_localsite(self):
        """Testing FileSSHStorage.get_ssh_dir with ~/.ssh and localsite"""
        sshdir = os.path.join(self.tempdir, '.ssh', 'site-1')

        storage = FileSSHStorage(namespace='site-1')
        self.assertEqual(storage.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_ssh_and_localsite(self):
        """Testing FileSSHStorage.get_ssh_dir with ~/ssh and localsite"""
        sshdir = os.path.join(self.tempdir, 'ssh')
        os.mkdir(sshdir, 0o700)
        sshdir = os.path.join(sshdir, 'site-1')

        storage = FileSSHStorage(namespace='site-1')
        self.assertEqual(storage.get_ssh_dir(), sshdir)

    def test_write_user_key_unsupported(self):
        """Testing FileSSHStorage.write_user_key with unsupported key type"""
        class FakeKey(object):
            pass

        storage = FileSSHStorage()
        self.assertRaises(UnsupportedSSHKeyError,
                          lambda: storage.write_user_key(FakeKey()))

    def test_read_host_keys(self):
        """Testing FileSSHStorage.read_host_keys"""
        storage = FileSSHStorage()
        storage.ensure_ssh_dir()

        line1 = 'host1 ssh-rsa %s' % test_keys.rsa_key_b64
        line2 = 'host2 ssh-dss %s' % test_keys.dsa_key_b64

        filename = storage.get_host_keys_filename()

        with open(filename, 'w') as fp:
            fp.write('%s\n' % line1)
            fp.write('\n')
            fp.write('# foo\n')
            fp.write('%s  \n' % line2)

        lines = storage.read_host_keys()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], line1)
        self.assertEqual(lines[1], line2)

    def test_add_host_key(self):
        """Testing FileSSHStorage.add_host_key"""
        storage = FileSSHStorage()
        storage.add_host_key('host1', test_keys.rsa_key)

        filename = storage.get_host_keys_filename()

        with open(filename, 'r') as fp:
            lines = fp.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0],
                         'host1 ssh-rsa %s\n' % test_keys.rsa_key_b64)

    def test_replace_host_key(self):
        """Testing FileSSHStorage.replace_host_key"""
        storage = FileSSHStorage()
        storage.add_host_key('host1', test_keys.rsa_key)
        storage.replace_host_key('host1', test_keys.rsa_key,
                                 test_keys.dsa_key)

        filename = storage.get_host_keys_filename()

        with open(filename, 'r') as fp:
            lines = fp.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0],
                         'host1 ssh-dss %s\n' % test_keys.dsa_key_b64)

    def test_replace_host_key_no_known_hosts(self):
        """Testing FileSSHStorage.replace_host_key with no known hosts file"""
        storage = FileSSHStorage()
        storage.replace_host_key('host1', test_keys.rsa_key, test_keys.dsa_key)

        filename = storage.get_host_keys_filename()

        with open(filename, 'r') as fp:
            lines = fp.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0],
                         'host1 ssh-dss %s\n' % test_keys.dsa_key_b64)


class SSHClientTests(SSHTestCase):
    """Unit tests for SSHClient."""
    def setUp(self):
        super(SSHClientTests, self).setUp()

        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')

    def test_generate_user_key(self, namespace=None):
        """Testing SSHClient.generate_user_key"""
        self._set_home(self.tempdir)

        client = SSHClient(namespace=namespace)
        key = client.generate_user_key(bits=1024)
        key_file = os.path.join(client.storage.get_ssh_dir(), 'id_rsa')
        self.assertTrue(os.path.exists(key_file))
        self.assertEqual(client.get_user_key(), key)

    def test_generate_user_key_with_localsite(self):
        """Testing SSHClient.generate_user_key with localsite"""
        self.test_generate_user_key('site-1')

    def test_delete_user_key(self, namespace=None):
        """Testing SSHClient.delete_user_key"""
        self._set_home(self.tempdir)

        client = SSHClient(namespace=namespace)
        client.import_user_key(test_keys.rsa_key)

        key_file = os.path.join(client.storage.get_ssh_dir(), 'id_rsa')
        self.assertTrue(os.path.exists(key_file))
        self.assertEqual(client.get_user_key(), test_keys.rsa_key)

        client.delete_user_key()
        self.assertFalse(os.path.exists(key_file))

    def test_delete_user_key_with_localsite(self):
        """Testing SSHClient.delete_user_key with localsite"""
        self.test_delete_user_key('site-1')

    def test_add_host_key(self, namespace=None):
        """Testing SSHClient.add_host_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        client.add_host_key('example.com', test_keys.rsa_key)

        known_hosts_file = client.storage.get_host_keys_filename()
        self.assertTrue(os.path.exists(known_hosts_file))

        with open(known_hosts_file, 'r') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', test_keys.rsa_key.get_name(),
                          test_keys.rsa_key_b64])

    def test_add_host_key_with_localsite(self):
        """Testing SSHClient.add_host_key with localsite"""
        self.test_add_host_key('site-1')

    def test_replace_host_key(self, namespace=None):
        """Testing SSHClient.replace_host_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        client.add_host_key('example.com', test_keys.rsa_key)
        client.replace_host_key('example.com', test_keys.rsa_key,
                                test_keys.dsa_key)

        known_hosts_file = client.storage.get_host_keys_filename()
        self.assertTrue(os.path.exists(known_hosts_file))

        with open(known_hosts_file, 'r') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', test_keys.dsa_key.get_name(),
                          test_keys.dsa_key_b64])

    def test_replace_host_key_with_localsite(self):
        """Testing SSHClient.replace_host_key with localsite"""
        self.test_replace_host_key('site-1')

    def test_import_user_key(self, namespace=None):
        """Testing SSHClient.import_user_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        client.import_user_key(test_keys.rsa_key)
        self.assertEqual(client.get_user_key(), test_keys.rsa_key)

    def test_import_user_key_with_localsite(self):
        """Testing SSHClient.import_user_key with localsite"""
        self.test_import_user_key('site-1')


class SettingsTests(TestCase):
    """Unit tests for the SSH storage backend settings functions."""

    def setUp(self):
        super(SettingsTests, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()

    def test_set_ssh_storage_backend_path(self):
        """Testing set_ssh_storage_backend_path"""
        set_ssh_storage_backend_path('foo.bar.FooStorage')

        self.assertEqual(self.siteconfig.get('ssh_storage_backend'),
                         'foo.bar.FooStorage')

    def test_get_ssh_storage_backend_path(self):
        """Testing set_ssh_storage_backend_path"""
        self.siteconfig.set('ssh_storage_backend', 'foo.bar.BarStorage')

        self.assertEqual(get_ssh_storage_backend_path(),
                         'foo.bar.BarStorage')


class UtilsTests(SSHTestCase):
    """Unit tests for reviewboard.ssh.utils."""

    def test_humanize_key_with_rsa_key(self):
        """Testing humanize_key with RSA key"""
        humanized = humanize_key(test_keys.rsa_key)
        self.assertIsInstance(humanized, six.text_type)
        self.assertEqual(humanized,
                         '76:ec:40:bd:69:9e:b1:e4:47:a9:e3:74:82:ec:0c:0f')

    def test_humanize_key_with_dsa_key(self):
        """Testing humanize_key with DSA key"""
        humanized = humanize_key(test_keys.dsa_key)
        self.assertIsInstance(humanized, six.text_type)
        self.assertEqual(humanized,
                         '62:4b:7f:b0:94:57:e2:bb:e7:d8:a4:88:88:c6:10:38')
