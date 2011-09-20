import logging
import os
import urlparse

from django.utils.translation import ugettext_lazy as _
import paramiko

from reviewboard.scmtools.errors import AuthenticationError, \
                                        BadHostKeyError, SCMError, \
                                        UnknownHostKeyError, \
                                        UnsupportedSSHKeyError


# A list of known SSH URL schemes.
ssh_uri_schemes = ["ssh", "sftp"]

urlparse.uses_netloc.extend(ssh_uri_schemes)

_ssh_dir = None


class RaiseUnknownHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """A Paramiko policy that raises UnknownHostKeyError for missing keys."""
    def missing_host_key(self, client, hostname, key):
        raise UnknownHostKeyError(hostname, key)


class MakeSSHDirError(IOError):
    def __init__(self, dirname):
        IOError.__init__(_("Unable to create directory %(dirname)s, which is "
                           "needed for the SSH host keys. Create this "
                           "directory, set the web server's user as the "
                           "the owner, and make it writable only by that "
                           "user.") % {
            'dirname': dirname,
        })


def humanize_key(key):
    """Returns a human-readable key as a series of hex characters."""
    return ':'.join(["%02x" % ord(c) for c in key.get_fingerprint()])


def set_ssh_dir(path):
    """Sets the SSH directory to use.

    This is mostly intended for unit tests.
    """
    global _ssh_dir
    _ssh_dir = path


def get_ssh_dir(local_site_name=None, ssh_dir_name=None):
    """Returns the path to the SSH directory on the system.

    By default, this will attempt to find either a .ssh or ssh directory.
    If ``ssh_dir_name`` is specified, the search will be skipped, and we'll
    use that name instead.
    """
    global _ssh_dir
    path = _ssh_dir

    if not _ssh_dir or ssh_dir_name:
        path = os.path.expanduser('~')

        if not ssh_dir_name:
            ssh_dir_name = '.ssh'

            for name in ('.ssh', 'ssh'):
                if os.path.exists(os.path.join(path, name)):
                    ssh_dir_name = name
                    break

        path = os.path.join(path, ssh_dir_name)

        if not ssh_dir_name:
            _ssh_dir = path

    if local_site_name:
        return os.path.join(path, local_site_name)
    else:
        return path


def get_host_keys_filename(local_site_name=None):
    """Returns the path to the known host keys file."""
    return os.path.join(get_ssh_dir(local_site_name), 'known_hosts')


def get_user_key(local_site_name=None):
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
            path = os.path.join(get_ssh_dir(local_site_name, sshdir),
                                filename)

            if os.path.isfile(path):
                keyfiles.append((cls, path))

    for cls, keyfile in keyfiles:
        try:
            return cls.from_private_key_file(keyfile)
        except paramiko.SSHException, e:
            logging.error('SSH: Unknown error accessing local key file %s: %s'
                          % (keyfile, e))
        except paramiko.PasswordRequiredException, e:
            logging.error('SSH: Unable to access password protected key file '
                          '%s: %s' % (keyfile, e))
        except IOError, e:
            logging.error('SSH: Error reading local key file %s: %s'
                          % (keyfile, e))

    return None


def get_public_key(key):
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


def is_key_authorized(key):
    """Returns whether or not a public key is currently authorized."""
    authorized = False
    public_key = key.get_base64()

    try:
        filename = os.path.join(get_ssh_dir(), 'authorized_keys')
        fp = open(filename, 'r')

        for line in fp.xreadlines():
            try:
                authorized_key = line.split()[1]
            except ValueError:
                continue
            except IndexError:
                continue

            if authorized_key == public_key:
                authorized = True
                break

        fp.close()
    except IOError:
        pass

    return authorized


def ensure_ssh_dir(local_site_name=None):
    """Ensures the existance of the .ssh directory.

    If the directory doesn't exist, it will be created.
    The full path to the directory will be returned.

    Callers are expected to handle any exceptions. This may raise
    IOError for any problems in creating the directory.
    """
    sshdir = get_ssh_dir(local_site_name)

    if local_site_name:
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


def generate_user_key(local_site_name=None):
    """Generates a new RSA keypair for the user running Review Board.

    This will store the new key in :file:`$HOME/.ssh/id_rsa` and return the
    resulting key as an instance of :py:mod:`paramiko.RSAKey`.

    If a key already exists in the id_rsa file, it's returned instead.

    Callers are expected to handle any exceptions. This may raise
    IOError for any problems in writing the key file, or
    paramiko.SSHException for any other problems.
    """
    sshdir = ensure_ssh_dir(local_site_name)
    filename = os.path.join(sshdir, 'id_rsa')

    if os.path.isfile(filename):
        return get_user_key(local_site_name)

    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(filename)
    return key


def import_user_key(keyfile, local_site_name=None):
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
    sshdir = ensure_ssh_dir(local_site_name)

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


def is_ssh_uri(url):
    """Returns whether or not a URL represents an SSH connection."""
    return urlparse.urlparse(url)[0] in ssh_uri_schemes


def get_ssh_client(local_site_name=None):
    """Returns a new paramiko.SSHClient with all known host keys added."""
    client = paramiko.SSHClient()
    filename = get_host_keys_filename(local_site_name)

    if os.path.exists(filename):
        client.load_host_keys(filename)

    return client


def add_host_key(hostname, key, local_site_name=None):
    """Adds a host key to the known hosts file."""
    ensure_ssh_dir(local_site_name)
    filename = get_host_keys_filename(local_site_name)

    try:
        fp = open(filename, 'a')
        fp.write('%s %s %s\n' % (hostname, key.get_name(), key.get_base64()))
        fp.close()
    except IOError, e:
        raise IOError(
            _('Unable to write host keys file %(filename)s: %(error)s') % {
                'filename': filename,
                'error': e,
            })


def replace_host_key(hostname, old_key, new_key, local_site_name=None):
    """Replaces a host key in the known hosts file with another.

    This is used for replacing host keys that have changed.
    """
    filename = get_host_keys_filename(local_site_name)

    if not os.path.exists(filename):
        add_host_key(hostname, new_key, local_site_name)
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


def check_host(hostname, username=None, password=None, local_site_name=None):
    """
    Checks if we can connect to a host with a known key.

    This will raise an exception if we cannot connect to the host. The
    exception will be one of BadHostKeyError, UnknownHostKeyError, or
    SCMError.
    """
    from django.conf import settings

    client = get_ssh_client(local_site_name)
    client.set_missing_host_key_policy(RaiseUnknownHostKeyPolicy())

    kwargs = {}

    # We normally want to notify on unknown host keys, but not when running
    # unit tests.
    if getattr(settings, 'RUNNING_TEST', False):
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        kwargs['allow_agent'] = False

    try:
        client.connect(hostname, username=username, password=password,
                       pkey=get_user_key(local_site_name), **kwargs)
    except paramiko.BadHostKeyException, e:
        raise BadHostKeyError(e.hostname, e.key, e.expected_key)
    except paramiko.AuthenticationException, e:
        # Some AuthenticationException instances have allowed_types set,
        # and some don't.
        allowed_types = getattr(e, 'allowed_types', [])

        if 'publickey' in allowed_types:
            key = get_user_key(local_site_name)
        else:
            key = None

        raise AuthenticationError(allowed_types=allowed_types, user_key=key)
    except paramiko.SSHException, e:
        if str(e) == 'No authentication methods available':
            raise AuthenticationError
        else:
            raise SCMError(unicode(e))


def register_rbssh(envvar):
    """Registers rbssh in an environment variable.

    This is a convenience method for making sure that rbssh is set properly
    in the environment for different tools. In some cases, we need to
    specifically place it in the system environment using ``os.putenv``,
    while in others (Mercurial, Bazaar), we need to place it in ``os.environ``.
    """
    os.putenv(envvar, 'rbssh')
    os.environ[envvar] = 'rbssh'
