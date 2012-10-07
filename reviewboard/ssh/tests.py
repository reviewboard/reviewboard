import os
import shutil
import tempfile

from django.test import TestCase as DjangoTestCase
import paramiko

from reviewboard.ssh.client import SSHClient


class SSHTestCase(DjangoTestCase):
    def setUp(self):
        self.old_home = os.getenv('HOME')
        self.tempdir = None
        os.environ['RBSSH_ALLOW_AGENT'] = '0'

    def tearDown(self):
        self._set_home(self.old_home)

        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def _set_home(self, homedir):
        os.environ['HOME'] = homedir


class SSHClientTests(SSHTestCase):
    """Unit tests for SSHClient."""
    def setUp(self):
        super(SSHClientTests, self).setUp()

        self.tempdir = tempfile.mkdtemp(prefix='rb-tests-home-')

    def test_get_ssh_dir_with_dot_ssh(self):
        """Testing SSHClient.get_ssh_dir with ~/.ssh"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, '.ssh')

        client = SSHClient()
        self.assertEqual(client.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_ssh(self):
        """Testing SSHClient.get_ssh_dir with ~/ssh"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, 'ssh')
        os.mkdir(sshdir, 0700)

        client = SSHClient()
        self.assertEqual(client.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_dot_ssh_and_localsite(self):
        """Testing SSHClient.get_ssh_dir with ~/.ssh and localsite"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, '.ssh', 'site-1')

        client = SSHClient(namespace='site-1')
        self.assertEqual(client.get_ssh_dir(), sshdir)

    def test_get_ssh_dir_with_ssh_and_localsite(self):
        """Testing SSHClient.get_ssh_dir with ~/ssh and localsite"""
        self._set_home(self.tempdir)
        sshdir = os.path.join(self.tempdir, 'ssh')
        os.mkdir(sshdir, 0700)
        sshdir = os.path.join(sshdir, 'site-1')

        client = SSHClient(namespace='site-1')
        self.assertEqual(client.get_ssh_dir(), sshdir)

    def test_generate_user_key(self, namespace=None):
        """Testing SSHClient.generate_user_key"""
        self._set_home(self.tempdir)

        client = SSHClient(namespace=namespace)
        key = client.generate_user_key()
        key_file = os.path.join(client.get_ssh_dir(), 'id_rsa')
        self.assertTrue(os.path.exists(key_file))
        self.assertEqual(client.get_user_key(), key)

    def test_generate_user_key_with_localsite(self):
        """Testing SSHClient.generate_user_key with localsite"""
        self.test_generate_user_key('site-1')

    def test_add_host_key(self, namespace=None):
        """Testing SSHClient.add_host_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        key = paramiko.RSAKey.generate(2048)
        client.add_host_key('example.com', key)

        known_hosts_file = client.get_host_keys_filename()
        self.assertTrue(os.path.exists(known_hosts_file))

        f = open(known_hosts_file, 'r')
        lines = f.readlines()
        f.close()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', key.get_name(), key.get_base64()])

    def test_add_host_key_with_localsite(self):
        """Testing SSHClient.add_host_key with localsite"""
        self.test_add_host_key('site-1')

    def test_replace_host_key(self, namespace=None):
        """Testing SSHClient.replace_host_key"""
        self._set_home(self.tempdir)
        client = SSHClient(namespace=namespace)

        key = paramiko.RSAKey.generate(2048)
        client.add_host_key('example.com', key)

        new_key = paramiko.RSAKey.generate(2048)
        client.replace_host_key('example.com', key, new_key)

        known_hosts_file = client.get_host_keys_filename()
        self.assertTrue(os.path.exists(known_hosts_file))

        f = open(known_hosts_file, 'r')
        lines = f.readlines()
        f.close()

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].split(),
                         ['example.com', new_key.get_name(),
                          new_key.get_base64()])

    def test_replace_host_key_with_localsite(self):
        """Testing SSHClient.replace_host_key with localsite"""
        self.test_replace_host_key('site-1')
