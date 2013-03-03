import os
import urlparse

import paramiko

from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import BadHostKeyError, SSHAuthenticationError, \
                                   SSHError
from reviewboard.ssh.policy import RaiseUnknownHostKeyPolicy


SSH_PORT = 22

# A list of known SSH URL schemes.
ssh_uri_schemes = ["ssh", "sftp"]

urlparse.uses_netloc.extend(ssh_uri_schemes)


def humanize_key(key):
    """Returns a human-readable key as a series of hex characters."""
    return ':'.join(["%02x" % ord(c) for c in key.get_fingerprint()])


def is_ssh_uri(url):
    """Returns whether or not a URL represents an SSH connection."""
    return urlparse.urlparse(url)[0] in ssh_uri_schemes


def check_host(netloc, username=None, password=None, namespace=None):
    """
    Checks if we can connect to a host with a known key.

    This will raise an exception if we cannot connect to the host. The
    exception will be one of BadHostKeyError, UnknownHostKeyError, or
    SCMError.
    """
    from django.conf import settings

    client = SSHClient(namespace=namespace)
    client.set_missing_host_key_policy(RaiseUnknownHostKeyPolicy())

    kwargs = {}

    if ':' in netloc:
        hostname, port = netloc.split(':')
        port = int(port)
    else:
        hostname = netloc
        port = SSH_PORT

    # We normally want to notify on unknown host keys, but not when running
    # unit tests.
    if getattr(settings, 'RUNNING_TEST', False):
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        kwargs['allow_agent'] = False

    try:
        client.connect(hostname, port, username=username, password=password,
                       pkey=client.get_user_key(), **kwargs)
    except paramiko.BadHostKeyException, e:
        raise BadHostKeyError(e.hostname, e.key, e.expected_key)
    except paramiko.AuthenticationException, e:
        # Some AuthenticationException instances have allowed_types set,
        # and some don't.
        allowed_types = getattr(e, 'allowed_types', [])

        if 'publickey' in allowed_types:
            key = client.get_user_key()
        else:
            key = None

        raise SSHAuthenticationError(allowed_types=allowed_types, user_key=key)
    except paramiko.SSHException, e:
        if str(e) == 'No authentication methods available':
            raise SSHAuthenticationError
        else:
            raise SSHError(unicode(e))


def register_rbssh(envvar):
    """Registers rbssh in an environment variable.

    This is a convenience method for making sure that rbssh is set properly
    in the environment for different tools. In some cases, we need to
    specifically place it in the system environment using ``os.putenv``,
    while in others (Mercurial, Bazaar), we need to place it in ``os.environ``.
    """
    os.putenv(envvar, 'rbssh')
    os.environ[envvar] = 'rbssh'
