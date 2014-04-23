from __future__ import unicode_literals

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from paramiko.hostkeys import HostKeyEntry
import paramiko

from reviewboard.ssh.errors import UnsupportedSSHKeyError


class SSHHostKeys(paramiko.HostKeys):
    """Manages known lists of host keys.

    This is a specialization of paramiko.HostKeys that interfaces with
    a storage backend to get the list of host keys.
    """
    def __init__(self, storage):
        paramiko.HostKeys.__init__(self)

        self.storage = storage

    def load(self, filename):
        """Loads all known host keys from the storage backend."""
        self._entries = []

        lines = self.storage.read_host_keys()

        for line in lines:
            entry = HostKeyEntry.from_line(line)

            if entry is not None:
                self._entries.append(entry)

    def save(self, filename):
        pass


class SSHClient(paramiko.SSHClient):
    """A client for communicating with an SSH server.

    SSHClient allows for communicating with an SSH server and managing
    all known host and user keys.

    This is a specialization of paramiko.SSHClient, and supports all the
    same capabilities.

    Key access goes through an SSHStorage backend. The storage backend knows
    how to look up keys and write them.

    The default backend works with the site directory's data/.ssh directory,
    and supports namespaced directories for LocalSites.
    """
    DEFAULT_STORAGE = 'reviewboard.ssh.storage.FileSSHStorage'
    SUPPORTED_KEY_TYPES = (paramiko.RSAKey, paramiko.DSSKey)

    def __init__(self, namespace=None, storage=None):
        super(SSHClient, self).__init__()

        self.namespace = namespace
        self._load_storage()
        self._host_keys = SSHHostKeys(self.storage)

        self.load_host_keys('')

    def _load_storage(self):
        """Loads the storage backend.

        This will attempt to load the SSH storage backend. If there is an
        error in loading the backend, it will be logged, and an
        ImproperlyConfigured exception will be raised.
        """
        try:
            path = getattr(settings, 'RBSSH_STORAGE_BACKEND',
                           self.DEFAULT_STORAGE)
        except ImportError:
            # We may not be running in the Django environment.
            path = self.DEFAULT_STORAGE

        i = path.rfind('.')
        module, class_name = path[:i], path[i + 1:]

        try:
            mod = __import__(module, {}, {}, [class_name])
        except ImportError as e:
            msg = 'Error importing SSH storage backend %s: "%s"' % (module, e)
            logging.critical(msg)
            raise ImproperlyConfigured(msg)

        try:
            self.storage = getattr(mod, class_name)(namespace=self.namespace)
        except Exception as e:
            msg = 'Error instantiating SSH storage backend %s: "%s"' % \
                  (module, e)
            logging.critical(msg)
            raise

    def get_user_key(self):
        """Returns the keypair of the user running Review Board.

        This will be an instance of :py:mod:`paramiko.PKey`, representing
        a DSS or RSA key, as long as one exists. Otherwise, it may return None.
        """
        key = None
        fp = None

        try:
            key = self.storage.read_user_key()
        except paramiko.SSHException as e:
            logging.error('SSH: Unknown error accessing user key: %s' % e)
        except paramiko.PasswordRequiredException as e:
            logging.error('SSH: Unable to access password protected '
                          'key file: %s' % e)
        except IOError as e:
            logging.error('SSH: Error reading user key: %s' % e)

        if fp:
            fp.close()

        return key

    def delete_user_key(self):
        """Deletes the user key for this client.

        If no key exists, this will do nothing.
        """
        try:
            self.storage.delete_user_key()
        except Exception as e:
            logging.error('Unable to delete SSH key file: %s' % e)
            raise

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
        public_key = key.get_base64()

        try:
            lines = self.storage.read_authorized_keys()

            for line in lines:
                try:
                    authorized_key = line.split()[1]
                except (ValueError, IndexError):
                    continue

                if authorized_key == public_key:
                    return True
        except IOError:
            pass

        return False

    def generate_user_key(self, bits=2048):
        """Generates a new RSA keypair for the user running Review Board.

        This will store the new key in the backend storage and return the
        resulting key as an instance of :py:mod:`paramiko.RSAKey`.

        If a key already exists, it's returned instead.

        Callers are expected to handle any exceptions. This may raise
        IOError for any problems in writing the key file, or
        paramiko.SSHException for any other problems.
        """
        key = self.get_user_key()

        if not key:
            key = paramiko.RSAKey.generate(bits)
            self._write_user_key(key)

        return key

    def import_user_key(self, keyfile):
        """Imports an uploaded key file into Review Board.

        ``keyfile`` is expected to be an ``UploadedFile`` or a paramiko
        ``KeyFile``. If this is a valid key file, it will be saved in
        the storage backend and the resulting key as an instance of
        :py:mod:`paramiko.PKey` will be returned.

        If a key of this name already exists, it will be overwritten.

        Callers are expected to handle any exceptions. This may raise
        IOError for any problems in writing the key file, or
        paramiko.SSHException for any other problems.

        This will raise UnsupportedSSHKeyError if the uploaded key is not
        a supported type.
        """
        # Try to find out what key this is.
        for cls in self.SUPPORTED_KEY_TYPES:
            key = None

            try:
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
                self._write_user_key(key)
                return key

        raise UnsupportedSSHKeyError()

    def add_host_key(self, hostname, key):
        """Adds a host key to the known hosts file."""
        self.storage.add_host_key(hostname, key)

    def replace_host_key(self, hostname, old_key, new_key):
        """Replaces a host key in the known hosts file with another.

        This is used for replacing host keys that have changed.
        """
        self.storage.replace_host_key(hostname, old_key, new_key)

    def _write_user_key(self, key):
        """Convenience function to write a user key and check for errors.

        Any errors caused as a result of writing a user key will be logged.
        """
        try:
            self.storage.write_user_key(key)
        except UnsupportedSSHKeyError as e:
            logging.error('Failed to write unknown key type %s' % type(key))
            raise
        except IOError as e:
            logging.error('Failed to write SSH user key: %s' % e)
            raise
        except Exception as e:
            logging.error('Unknown error writing SSH user key: %s' % e,
                          exc_info=1)
            raise
