import logging
import os

from django.utils.translation import ugettext_lazy as _
import paramiko

from reviewboard.ssh.errors import MakeSSHDirError, UnsupportedSSHKeyError


class SSHClient(paramiko.SSHClient):
    _ssh_dir = None

    def __init__(self, namespace=None):
        super(SSHClient, self).__init__()

        self.namespace = namespace

        filename = self.get_host_keys_filename()

        if os.path.exists(filename):
            self.load_host_keys(filename)

    def get_host_keys_filename(self):
        """Returns the path to the known host keys file."""
        return os.path.join(self.get_ssh_dir(), 'known_hosts')

    def get_ssh_dir(self, ssh_dir_name=None):
        """Returns the path to the SSH directory on the system.

        By default, this will attempt to find either a .ssh or ssh directory.
        If ``ssh_dir_name`` is specified, the search will be skipped, and we'll
        use that name instead.
        """
        path = SSHClient._ssh_dir

        if not SSHClient._ssh_dir or ssh_dir_name:
            path = os.path.expanduser('~')

            if not ssh_dir_name:
                ssh_dir_name = '.ssh'

                for name in ('.ssh', 'ssh'):
                    if os.path.exists(os.path.join(path, name)):
                        ssh_dir_name = name
                        break

            path = os.path.join(path, ssh_dir_name)

            if not ssh_dir_name:
                SSHClient._ssh_dir = path

        if self.namespace:
            return os.path.join(path, self.namespace)
        else:
            return path

    def get_user_key(self):
        """Returns the keypair of the user running Review Board.

        This will be an instance of :py:mod:`paramiko.PKey`, representing
        a DSS or RSA key, as long as one exists. Otherwise, it may return None.
        """
        keyfiles = []

        for cls, filename in ((paramiko.RSAKey, 'id_rsa'),
                              (paramiko.DSSKey, 'id_dsa')):
            # Paramiko looks in ~/.ssh and ~/ssh, depending on the platform,
            # so check both.
            for sshdir in ('.ssh', 'ssh'):
                path = os.path.join(self.get_ssh_dir(sshdir), filename)

                if os.path.isfile(path):
                    keyfiles.append((cls, path))

        for cls, keyfile in keyfiles:
            try:
                return cls.from_private_key_file(keyfile)
            except paramiko.SSHException, e:
                logging.error('SSH: Unknown error accessing local key file '
                              '%s: %s'
                              % (keyfile, e))
            except paramiko.PasswordRequiredException, e:
                logging.error('SSH: Unable to access password protected '
                              'key file %s: %s' % (keyfile, e))
            except IOError, e:
                logging.error('SSH: Error reading local key file %s: %s'
                              % (keyfile, e))

        return None

    def get_public_key(self, key):
        """Returns the public key portion of an SSH key.

        This will be formatted for display.
        """
        public_key = ''

        if key:
            base64 = key.get_base64()

            # TODO: Move this wrapping logic into a common templatetag.
            for i in range(0, len(base64), 64):
                public_key += base64[i:i + 64] + '\n'

        return public_key

    def is_key_authorized(self, key):
        """Returns whether or not a public key is currently authorized."""
        authorized = False
        public_key = key.get_base64()

        try:
            filename = os.path.join(self.get_ssh_dir(), 'authorized_keys')
            fp = open(filename, 'r')

            for line in fp.xreadlines():
                try:
                    authorized_key = line.split()[1]
                except (ValueError, IndexError):
                    continue

                if authorized_key == public_key:
                    authorized = True
                    break

            fp.close()
        except IOError:
            pass

        return authorized

    def ensure_ssh_dir(self):
        """Ensures the existance of the .ssh directory.

        If the directory doesn't exist, it will be created.
        The full path to the directory will be returned.

        Callers are expected to handle any exceptions. This may raise
        IOError for any problems in creating the directory.
        """
        sshdir = self.get_ssh_dir()

        if self.namespace:
            # The parent will be the .ssh dir.
            parent = os.path.dirname(sshdir)

            if not os.path.exists(parent):
                try:
                    os.mkdir(parent, 0700)
                except OSError:
                    raise MakeSSHDirError(parent)

        if not os.path.exists(sshdir):
            try:
                os.mkdir(sshdir, 0700)
            except OSError:
                raise MakeSSHDirError(sshdir)

        return sshdir

    def generate_user_key(self):
        """Generates a new RSA keypair for the user running Review Board.

        This will store the new key in :file:`$HOME/.ssh/id_rsa` and return the
        resulting key as an instance of :py:mod:`paramiko.RSAKey`.

        If a key already exists in the id_rsa file, it's returned instead.

        Callers are expected to handle any exceptions. This may raise
        IOError for any problems in writing the key file, or
        paramiko.SSHException for any other problems.
        """
        sshdir = self.ensure_ssh_dir()
        filename = os.path.join(sshdir, 'id_rsa')

        if os.path.isfile(filename):
            return self.get_user_key()

        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(filename)
        return key

    def import_user_key(self, keyfile):
        """Imports an uploaded key file into Review Board.

        ``keyfile`` is expected to be an ``UploadedFile`` or a paramiko
        ``KeyFile``. If this is a valid key file, it will be saved in
        :file:`$HOME/.ssh/`` and the resulting key as an instance of
        :py:mod:`paramiko.RSAKey` will be returned.

        If a key of this name already exists, it will be overwritten.

        Callers are expected to handle any exceptions. This may raise
        IOError for any problems in writing the key file, or
        paramiko.SSHException for any other problems.

        This will raise UnsupportedSSHKeyError if the uploaded key is not
        a supported type.
        """
        sshdir = self.ensure_ssh_dir()

        # Try to find out what key this is.
        for cls, filename in ((paramiko.RSAKey, 'id_rsa'),
                              (paramiko.DSSKey, 'id_dsa')):
            try:
                key = None

                if not isinstance(keyfile, paramiko.PKey):
                    keyfile.seek(0)
                    key = cls.from_private_key(keyfile)
                elif isinstance(keyfile, cls):
                    key = keyfile
            except paramiko.SSHException:
                # We don't have more detailed info than this, but most
                # likely, it's not a valid key. Skip to the next.
                continue

            if key:
                key.write_private_key_file(os.path.join(sshdir, filename))
                return key

        raise UnsupportedSSHKeyError()

    def add_host_key(self, hostname, key):
        """Adds a host key to the known hosts file."""
        self.ensure_ssh_dir()
        filename = self.get_host_keys_filename()

        try:
            fp = open(filename, 'a')
            fp.write('%s %s %s\n' % (hostname, key.get_name(),
                                     key.get_base64()))
            fp.close()
        except IOError, e:
            raise IOError(
                _('Unable to write host keys file %(filename)s: %(error)s') % {
                    'filename': filename,
                    'error': e,
                })

    def replace_host_key(self, hostname, old_key, new_key):
        """Replaces a host key in the known hosts file with another.

        This is used for replacing host keys that have changed.
        """
        filename = self.get_host_keys_filename()

        if not os.path.exists(filename):
            self.add_host_key(hostname, new_key)
            return

        try:
            fp = open(filename, 'r')
            lines = fp.readlines()
            fp.close()

            old_key_base64 = old_key.get_base64()
        except IOError, e:
            raise IOError(
                _('Unable to read host keys file %(filename)s: %(error)s') % {
                    'filename': filename,
                    'error': e,
                })

        try:
            fp = open(filename, 'w')

            for line in lines:
                parts = line.strip().split(" ")

                if parts[-1] == old_key_base64:
                    parts[-1] = new_key.get_base64()

                fp.write(' '.join(parts) + '\n')

            fp.close()
        except IOError, e:
            raise IOError(
                _('Unable to write host keys file %(filename)s: %(error)s') % {
                    'filename': filename,
                    'error': e,
                })
