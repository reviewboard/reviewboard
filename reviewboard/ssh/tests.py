from __future__ import unicode_literals

import os
import shutil
import tempfile

import paramiko

from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import UnsupportedSSHKeyError
from reviewboard.ssh.storage import FileSSHStorage
from reviewboard.testing.testcase import TestCase


class SSHTestCase(TestCase):
    def setUp(self):
        super(SSHTestCase, self).setUp()

        self.old_home = os.getenv('HOME')
        self.tempdir = None
        os.environ['RBSSH_ALLOW_AGENT'] = '0'
        FileSSHStorage._ssh_dir = None

        if not hasattr(SSHTestCase, 'key1'):
            SSHTestCase.key1 = paramiko.RSAKey.generate(1024)
            SSHTestCase.key2 = paramiko.DSSKey.generate(1024)
            SSHTestCase.key1_b64 = SSHTestCase.key1.get_base64()
            SSHTestCase.key2_b64 = SSHTestCase.key2.get_base64()

    def tearDown(self):
        super(SSHTestCase, self).tearDown()

        self._set_home(self.old_home)

        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def _set_home(self, homedir):
        os.environ['HOME'] = homedir


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

        line1 = 'host1 ssh-rsa %s' % self.key1_b64
        line2 = 'host2 ssh-dss %s' % self.key2_b64

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
        storage.add_host_key('host1', self.key1)

        filename = storage.get_host_keys_filename()
        with open(filename, 'r') as fp:
            lines = fp.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], 'host1 ssh-rsa %s\n' % self.key1_b64)

    def test_replace_host_key(self):
        """Testing FileSSHStorage.replace_host_key"""
        storage = FileSSHStorage()
        storage.add_host_key('host1', self.key1)
        storage.replace_host_key('host1', self.key1, self.key2)

        filename = storage.get_host_keys_filename()
        with open(filename, 'r') as fp:
            lines = fp.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], 'host1 ssh-dss %s\n' % self.key2_b64)

    def test_replace_host_key_no_known_hosts(self):
        """Testing FileSSHStorage.replace_host_key with no known hosts file"""
        storage = FileSSHStorage()
        storage.replace_host_key('host1', self.key1, self.key2)

        filename = storage.get_host_keys_filename()
        with open(filename, 'r') as fp:
            lines = fp.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], 'host1 ssh-dss %s\n' % self.key2_b64)


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
        client.import_user_key(self.key1)

        key_file = os.path.join(client.storage.get_ssh_dir(), 'id_rsa')
        self.assertTrue(os.path.exists(key_file))
        self.assertEqual(client.get_user_key(), self.key1)

        client.delete_user_key()
        self.assertFalse(os.path.exists(key_file))

    def test_delete_user_key_with_localsite(self):
        """Testing SSHClient.delete_user_key with localsite"""
        self.test_delete_user_key('site-1')

    def test_add_host_key(self, namespace=None):
        """Testing SSHClient.add_host_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        client.add_host_key('example.com', self.key1)

        known_hosts_file = client.storage.get_host_keys_filename()
        self.assertTrue(os.path.exists(known_hosts_file))

        with open(known_hosts_file, 'r') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', self.key1.get_name(), self.key1_b64])

    def test_add_host_key_with_localsite(self):
        """Testing SSHClient.add_host_key with localsite"""
        self.test_add_host_key('site-1')

    def test_replace_host_key(self, namespace=None):
        """Testing SSHClient.replace_host_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        client.add_host_key('example.com', self.key1)
        client.replace_host_key('example.com', self.key1, self.key2)

        known_hosts_file = client.storage.get_host_keys_filename()
        self.assertTrue(os.path.exists(known_hosts_file))

        with open(known_hosts_file, 'r') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', self.key2.get_name(),
                          self.key2_b64])

    def test_replace_host_key_with_localsite(self):
        """Testing SSHClient.replace_host_key with localsite"""
        self.test_replace_host_key('site-1')

    def test_import_user_key(self, namespace=None):
        """Testing SSHClient.import_user_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        client.import_user_key(self.key1)
        self.assertEqual(client.get_user_key(), self.key1)

    def test_import_user_key_with_localsite(self):
        """Testing SSHClient.import_user_key with localsite"""
        self.test_import_user_key('site-1')
