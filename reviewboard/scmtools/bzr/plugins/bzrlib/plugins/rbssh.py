# rbssh plugin for Bazaar.
# Copyright (C) 2017  Beanbag, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""rbssh plugin for Bazaar and Breezy.

This registers :command:`rbssh` as a SSH plugin for Bazaar. It's run entirely
outside of the Review Board process, and is invoked exclusively by
:command:`bzr` or :command:`brz`.
"""

# NOTE: This is a plugin compatible with both Breezy and Bazaar, which is
#       called as an external process. This plugin runs in Breezy/Bazaar's
#       process, which might even be outside of the same Python environment
#       as Review Board. As such, it needs to remain compatible with Python
#       2 and 3, and cannot import any modules from Review Board.
from __future__ import unicode_literals

try:
    from breezy.transport.ssh import (SubprocessVendor,
                                      register_default_ssh_vendor,
                                      register_ssh_vendor)
except ImportError:
    from bzrlib.transport.ssh import (SubprocessVendor,
                                      register_default_ssh_vendor,
                                      register_ssh_vendor)


class RBSSHVendor(SubprocessVendor):
    """SSH vendor class for using rbssh."""

    executable_path = 'rbssh'

    def _get_vendor_specific_argv(self, username, host, port=None,
                                  subsystem=None, command=None):
        """Return arguments to pass to rbssh.

        Args:
            username (unicode):
                The username to connect with.

            host (unicode):
                The hostname to connect to.

            port (int, optional):
                The custom port to connect to.

            subsystem (unicode, optional):
                The SSH subsystem to use.

            command (unicode, optional):
                The command to invoke through the SSH connection.

        Returns:
            list of unicode:
            The list of arguments to pass to :command:`rbssh`.
        """
        args = [self.executable_path]

        if port is not None:
            args.extend(['-p', '%s' % port])

        if username is not None:
            args.extend(['-l', username])

        if subsystem is not None:
            args.extend(['-s', host, subsystem])
        else:
            args.extend([host] + command)

        return args


vendor = RBSSHVendor()
register_ssh_vendor('rbssh', vendor)
register_default_ssh_vendor(vendor)
