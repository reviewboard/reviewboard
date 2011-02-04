#!/usr/bin/env python
#
# rbssh.py -- A custom SSH client for use in Review Board.
#
# This is used as an ssh replacement that can be used across platforms with
# a custom .ssh directory. OpenSSH doesn't respect $HOME, instead reading
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
import getpass
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


DEBUG = os.getenv('DEBUG_RBSSH')


options = None
debug_fp = None


class PlatformHandler(object):
    def __init__(self, channel):
        self.channel = channel

    def shell(self):
        raise NotImplemented

    def transfer(self):
        raise NotImplemented

    def process_channel(self):
        if self.channel.recv_ready():
            data = self.channel.recv(4096)
            #debug('<< %s\n' % data)

            if not data:
                print '\r\n*** EOF\r\n'
                debug('!! stdout empty\n')
                return False

            sys.stdout.write(data)
            sys.stdout.flush()

        if self.channel.recv_stderr_ready():
            data = self.channel.recv_stderr(4096)

            if not data:
                debug('!! stderr empty\n')
                return False

            #debug('E>> %s\n' % data)
            sys.stderr.write(data)
            sys.stderr.flush()

        if self.channel.exit_status_ready():
            debug('!!! exit_status_ready\n')
            return False

        return True


    def process_stdin(self):
        buf = os.read(sys.stdin.fileno(), 1)

        if not buf:
            debug('!! stdin empty\n')
            return False

        #debug('>> %s\n' % buf)
        result = self.channel.send(buf)

        return True


class PosixHandler(PlatformHandler):
    def shell(self):
        import termios
        import tty

        oldtty = termios.tcgetattr(sys.stdin)

        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())

            self.handle_communications()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    def transfer(self):
        import fcntl

        fd = sys.stdin.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.handle_communications()

    def handle_communications(self):
        while True:
            rl, wl, el = select.select([self.channel, sys.stdin], [], [])

            if self.channel in rl:
                if not self.process_channel():
                    break

            if sys.stdin in rl:
                if not self.process_stdin():
                    self.channel.shutdown_write()
                    break


class WindowsHandler(PlatformHandler):
    def shell(self):
        self.handle_communications()

    def transfer(self):
        self.handle_communications()

    def handle_communications(self):
        import threading

        debug('!! begin_windows_transfer\n')

        def read_stdin(channel):
            while process_stdin(channel):
                time.sleep(0.1)

        writer = threading.Thread(target=read_stdin, args=(self.channel,))
        writer.setDaemon(True)
        writer.start()

        try:
            while self.process_channel():
                time.sleep(0.1)
        except EOFError:
            pass


def debug(s):
    if debug_fp:
        debug_fp.write(s)
        debug_fp.flush()


def print_version(option, opt, value, parser):
    parser.print_version()
    sys.exit(0)


def parse_options(args):
    global options

    hostname = None

    parser = OptionParser(usage='%prog [options] [user@]hostname [command]',
                          version='%prog ' + get_version_string())
    parser.disable_interspersed_args()
    parser.add_option('-l',
                      dest='username', metavar='USERNAME', default=None,
                      help='the user to log in as on the remote machine')
    parser.add_option('-p', '--port',
                      type='int', dest='port', metavar='PORT', default=None,
                      help='the port to connect to')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='suppress any unnecessary output')
    parser.add_option('-s',
                      dest='subsystem', metavar='SUBSYSTEM', default=None,
                      nargs=2,
                      help='the subsystem to use (ssh or sftp)')
    parser.add_option('-V',
                      action='callback', callback=print_version,
                      help='display the version information and exit')

    (options, args) = parser.parse_args(args)

    if options.subsystem:
        if len(options.subsystem) != 2:
            parser.error('-s requires a hostname and a valid subsystem')
        elif options.subsystem[1] not in ('sftp', 'ssh'):
            parser.error('Invalid subsystem %s' % options.subsystem[1])

        hostname, options.subsystem = options.subsystem

    if len(args) == 0 and not hostname:
        parser.error('A hostname must be specified')

    if not hostname:
        hostname = args[0]
        args = args[1:]

    return hostname, args


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
    attempts = 0
    password = None
    success = False

    while True:
        try:
            client.connect(hostname, username=username, password=password)
            break
        except paramiko.AuthenticationException, e:
            if attempts == 3 or not sys.stdin.isatty():
                sys.stderr.write('Too many authentication failures for %s\n' %
                                 username)
                sys.exit(1)

            attempts += 1
            password = getpass.getpass("%s@%s's password: " %
                                       (username, hostname))
        except Exception, e:
            debug('Unknown exception during connect: %s (%s)' % (e, type(e)))
            sys.exit(1)

    transport = client.get_transport()

    channel = transport.open_session()

    if os.name == 'posix':
        handler = PosixHandler(channel)
    else:
        handler = WindowsHandler(channel)

    if options.subsystem == 'sftp':
        debug('!!! Invoking sftp subsystem')
        channel.invoke_subsystem('sftp')
        handler.transfer()
    elif command:
        debug('!!! Sending command %s' % command)
        channel.exec_command(' '.join(command))
        handler.transfer()
    else:
        debug('!!! Opening shell')
        channel.get_pty()
        channel.invoke_shell()
        handler.shell()

    debug('!!! Done')
    status = channel.recv_exit_status()
    client.close()

    if debug_fp:
        debug_fp.close()

    return status


if __name__ == '__main__':
    main()
