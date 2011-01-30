#!/usr/bin/env python
#
# rbssh.py -- A custom SSH client for use in Review Board.
#
# This is used as an ssh replacement that can be used across platforms with
# a cusotm .ssh directory. OpenSSH doesn't respect $HOME, instead reading
# /etc/passwd directly, which causes problems for us. Using rbssh, we can
# work around this.
#
#
# Copyright (c) 2010-2011  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
import os
import select
import socket
import sys
import tempfile
import time
from optparse import OptionParser

import paramiko

from reviewboard import get_version_string
from reviewboard.scmtools import sshutils
from reviewboard.scmtools.core import SCMTool


DEBUG = False


options = None
debug_fp = None


def debug(s):
    if debug_fp:
        debug_fp.write(s)
        debug_fp.flush()


def parse_options(args):
    global options

    # There are two sets of arguments we may find. We want to handle
    # anything before the hostname, but nothing after it. So, split
    # up the argument list.

    rbssh_args = []
    command_args = []

    found_hostname = False

    for arg in args:
        if arg.startswith('-'):
            if found_hostname:
                command_args.append(arg)
            else:
                rbssh_args.append(arg)
        else:
            found_hostname = True
            rbssh_args.append(arg)

    parser = OptionParser(usage='%prog [options] [user@]hostname command',
                          version='%prog ' + get_version_string())
    parser.add_option('-l',
                      dest='username', metavar='USERNAME', default=None,
                      help='the user to log in as on the remote machine')
    parser.add_option('-p', '--port',
                      dest='port', metavar='PORT', default=None,
                      help='the port to connect to')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='suppress any unnecessary output')

    (options, args) = parser.parse_args(rbssh_args)

    if len(rbssh_args) < 2:
        parser.print_help()
        sys.exit(1)

    return args[0], args[1:] + command_args


def process_channel(channel):
    if channel.recv_ready():
        data = channel.recv(4096)
        debug('<< %s\n' % data)

        if not data:
            debug('!! stdout empty\n')
            return False

        sys.stdout.write(data)
        sys.stdout.flush()

    if channel.recv_stderr_ready():
        data = channel.recv_stderr(4096)

        if not data:
            debug('!! stderr empty\n')
            return False

        debug('E>> %s\n' % data)
        sys.stderr.write(data)
        sys.stderr.flush()

    if channel.exit_status_ready():
        debug('exit_status_ready\n')
        return False

    return True


def process_stdin(channel):
    buf = os.read(sys.stdin.fileno(), 4096)

    if not buf:
        debug('!! stdin empty\n')
        return False

    debug('>> %s\n' % buf)
    result = channel.send(buf)

    return True


def begin_posix(channel):
    import fcntl

    fd = sys.stdin.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    debug('!! begin_posix\n')

    while True:
        rl, wl, el = select.select([channel, sys.stdin], [], [])

        if channel in rl:
            if not process_channel(channel):
                break

        if sys.stdin in rl:
            if not process_stdin(channel):
                channel.shutdown_write()
                break

    debug('!! done\n')


def begin_windows(channel):
    debug('!! begin_windows\n')
    import threading

    def read_stdin(channel):
        while process_stdin(channel):
            time.sleep(0.1)

    writer = threading.Thread(target=read_stdin, args=(channel,))
    writer.setDaemon(True)
    writer.start()

    try:
        while process_channel(channel):
            time.sleep(0.1)
    except EOFError:
        pass


def main():
    if DEBUG:
        global debug_fp
        fd, name = tempfile.mkstemp(prefix='rbssh', suffix='.log')
        debug_fp = os.fdopen(fd, "w+b")

        debug_fp.write('%s\n' % sys.argv)
        debug_fp.write('PID %s\n' % os.getpid())

    path, command = parse_options(sys.argv[1:])

    if '://' not in path:
        path = 'ssh://' + path

    username, hostname = SCMTool.get_auth_from_uri(path, options.username)

    debug('%s, %s, %s\n' % (hostname, username, command))

    client = sshutils.get_ssh_client()
    client.connect(hostname, username=username)

    transport = client.get_transport()
    channel = transport.open_session()
    channel.exec_command(' '.join(command))

    if os.name == 'posix':
        begin_posix(channel)
    else:
        begin_windows(channel)

    status = channel.recv_exit_status()
    client.close()

    if debug_fp:
        fp.close()

    return status


if __name__ == '__main__':
    main()
