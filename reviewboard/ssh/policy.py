from __future__ import unicode_literals

import paramiko

from reviewboard.ssh.errors import UnknownHostKeyError


class RaiseUnknownHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """A Paramiko policy that raises UnknownHostKeyError for missing keys."""
    def missing_host_key(self, client, hostname, key):
        raise UnknownHostKeyError(hostname, key)
