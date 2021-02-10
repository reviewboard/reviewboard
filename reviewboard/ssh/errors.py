from __future__ import unicode_literals

import logging
import socket

from django.utils.translation import ugettext as _
from djblets.util.humanize import humanize_list


logger = logging.getLogger(__name__)


class SSHError(Exception):
    """An SSH-related error."""
    pass


class MakeSSHDirError(IOError, SSHError):
    def __init__(self, dirname):
        IOError.__init__(
            _("Unable to create directory %(dirname)s, which is needed for "
              "the SSH host keys. Create this directory, set the web "
              "server's user as the the owner, and make it writable only by "
              "that user.") % {'dirname': dirname})


class SSHAuthenticationError(SSHError):
    """An error representing a failed authentication over SSH.

    This takes a list of SSH authentication types that are allowed.
    Primarily, we respond to "password" and "publickey".

    This may also take the user's SSH key that was tried, if any.
    """
    def __init__(self, allowed_types=[], msg=None, user_key=None):
        if allowed_types:
            msg = _('Unable to authenticate against this repository using one '
                    'of the supported authentication types '
                    '(%(allowed_types)s).') % {
                'allowed_types': humanize_list(allowed_types),
            }
        elif not msg:
            msg = _('Unable to authenticate against this repository using one '
                    'of the supported authentication types.')

        SSHError.__init__(self, msg)
        self.allowed_types = allowed_types
        self.user_key = user_key


class UnsupportedSSHKeyError(SSHError):
    """An error representing an unsupported type of SSH key."""
    def __init__(self):
        SSHError.__init__(self,
                          _('This SSH key is not a valid RSA or DSS key.'))


class SSHKeyError(SSHError):
    """An error involving a host key on an SSH connection."""
    def __init__(self, hostname, key, message):
        from reviewboard.ssh.utils import humanize_key

        SSHError.__init__(self, message)
        self.hostname = hostname
        self.key = humanize_key(key)
        self.raw_key = key


class BadHostKeyError(SSHKeyError):
    """An error representing a bad or malicious key for an SSH connection."""
    def __init__(self, hostname, key, expected_key):
        from reviewboard.ssh.utils import humanize_key

        SSHKeyError.__init__(
            self, hostname, key,
            _("Warning! The host key for server %(hostname)s does not match "
              "the expected key.\n"
              "It's possible that someone is performing a man-in-the-middle "
              "attack. It's also possible that the RSA host key has just "
              "been changed. Please contact your system administrator if "
              "you're not sure. Do not accept this host key unless you're "
              "certain it's safe!")
            % {
                'hostname': hostname,
            })
        self.expected_key = humanize_key(expected_key)
        self.raw_expected_key = expected_key


class UnknownHostKeyError(SSHKeyError):
    """An error representing an unknown host key for an SSH connection."""
    def __init__(self, hostname, key):
        try:
            ipaddr = socket.gethostbyname(hostname)
            warning = _("The authenticity of the host '%(hostname)s' (%(ip)s) "
                        "could not be determined.") % {
                'hostname': hostname,
                'ip': ipaddr,
            }
        except Exception as e:
            logger.warning('Failed to find IP for "%s": %s',
                           hostname, e)
            warning = _("The authenticity of the host '%(hostname)s' could "
                        "not be determined.") % {'hostname': hostname}

        SSHKeyError.__init__(self, hostname, key, warning)


class SSHInvalidPortError(SSHError):
    """An error representing a port that is a non-integer value."""

    def __init__(self, port):
        super(SSHInvalidPortError, self).__init__(
            _('"%s" is not a valid port number. Please ensure the path has '
              'the correct port number specified.')
            % port)
