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

from __future__ import unicode_literals

import getpass
import logging
import os
import select
import sys
from optparse import OptionParser

if 'RBSITE_PYTHONPATH' in os.environ:
    for path in reversed(os.environ['RBSITE_PYTHONPATH'].split(':')):
        sys.path.insert(1, path)

import paramiko

from reviewboard import initialize, get_version_string
from reviewboard.scmtools.core import SCMTool
from reviewboard.ssh.client import SSHClient


DEBUG = os.getenv('DEBUG_RBSSH')
DEBUG_LOGDIR = os.getenv('RBSSH_LOG_DIR')

SSH_PORT = 22

options = None


class PlatformHandler(object):
    def __init__(self, channel):
        self.channel = channel

    def shell(self):
        raise NotImplementedError

    def transfer(self):
        raise NotImplementedError

    def process_channel(self, channel):
        if channel.closed:
            return False

        logging.debug('!! process_channel\n')
        if channel.recv_ready():
            data = channel.recv(4096)

            if not data:
                logging.debug('!! stdout empty\n')
                return False

            sys.stdout.write(data)
            sys.stdout.flush()

        if channel.recv_stderr_ready():
            data = channel.recv_stderr(4096)

            if not data:
                logging.debug('!! stderr empty\n')
                return False

            sys.stderr.write(data)
            sys.stderr.flush()

        if channel.exit_status_ready():
            logging.debug('!!! exit_status_ready\n')
            return False

        return True

    def process_stdin(self, channel):
        logging.debug('!! process_stdin\n')

        try:
            buf = os.read(sys.stdin.fileno(), 1)
        except OSError:
            buf = None

        if not buf:
            logging.debug('!! stdin empty\n')
            return False

        channel.send(buf)

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
                if not self.process_channel(self.channel):
                    break

            if sys.stdin in rl:
                if not self.process_stdin(self.channel):
                    self.channel.shutdown_write()
                    break


class WindowsHandler(PlatformHandler):
    def shell(self):
        self.handle_communications()

    def transfer(self):
        self.handle_communications()

    def handle_communications(self):
        import threading

        logging.debug('!! begin_windows_transfer\n')

        self.channel.setblocking(0)

        def writeall(channel):
            while self.process_channel(channel):
                pass

            logging.debug('!! Shutting down reading\n')
            channel.shutdown_read()

        writer = threading.Thread(target=writeall, args=(self.channel,))
        writer.start()

        try:
            while self.process_stdin(self.channel):
                pass
        except EOFError:
            pass

        logging.debug('!! Shutting down writing\n')
        self.channel.shutdown_write()


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
    parser.add_option('--rb-disallow-agent',
                      action='store_false', dest='allow_agent',
                      default=os.getenv('RBSSH_ALLOW_AGENT') != '0',
                      help='disable using the SSH agent for authentication')
    parser.add_option('--rb-local-site',
                      dest='local_site_name', metavar='NAME',
                      default=os.getenv('RB_LOCAL_SITE'),
                      help='the local site name containing the SSH keys to '
                           'use')

    (options, args) = parser.parse_args(args)

    if options.subsystem:
        if len(options.subsystem) != 2:
            parser.error('-s requires a hostname and a valid subsystem')
        elif options.subsystem[1] not in ('sftp', 'ssh'):
            parser.error('Invalid subsystem %s' % options.subsystem[1])

        hostname, options.subsystem = options.subsystem

    if len(args) == 0 and not hostname:
        parser.print_help()
        sys.exit(1)

    if not hostname:
        hostname = args[0]
        args = args[1:]

    if options.port:
        port = options.port
    else:
        port = SSH_PORT

    return hostname, port, args


def main():
    os.environ.setdefault(b'DJANGO_SETTINGS_MODULE', b'reviewboard.settings')

    if DEBUG:
        pid = os.getpid()
        log_filename = 'rbssh-%s.log' % pid

        if DEBUG_LOGDIR:
            log_path = os.path.join(DEBUG_LOGDIR, log_filename)
        else:
            log_path = log_filename

        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-18s %(levelname)-8s '
                                   '%(message)s',
                            datefmt='%m-%d %H:%M',
                            filename=log_path,
                            filemode='w')

        logging.debug('%s' % sys.argv)
        logging.debug('PID %s' % pid)

    initialize()

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))
    ch.addFilter(logging.Filter('root'))
    logging.getLogger('').addHandler(ch)

    path, port, command = parse_options(sys.argv[1:])

    if '://' not in path:
        path = 'ssh://' + path

    username, hostname = SCMTool.get_auth_from_uri(path, options.username)

    if username is None:
        username = getpass.getuser()

    logging.debug('!!! %s, %s, %s' % (hostname, username, command))

    client = SSHClient(namespace=options.local_site_name)
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    attempts = 0
    password = None

    key = client.get_user_key()

    while True:
        try:
            client.connect(hostname, port, username=username,
                           password=password, pkey=key,
                           allow_agent=options.allow_agent)
            break
        except paramiko.AuthenticationException as e:
            if attempts == 3 or not sys.stdin.isatty():
                logging.error('Too many authentication failures for %s' %
                              username)
                sys.exit(1)

            attempts += 1
            password = getpass.getpass("%s@%s's password: " %
                                       (username, hostname))
        except paramiko.SSHException as e:
            logging.error('Error connecting to server: %s' % e)
            sys.exit(1)
        except Exception as e:
            logging.error('Unknown exception during connect: %s (%s)' %
                          (e, type(e)))
            sys.exit(1)

    transport = client.get_transport()
    channel = transport.open_session()

    if sys.platform in ('cygwin', 'win32'):
        logging.debug('!!! Using WindowsHandler')
        handler = WindowsHandler(channel)
    else:
        logging.debug('!!! Using PosixHandler')
        handler = PosixHandler(channel)

    if options.subsystem == 'sftp':
        logging.debug('!!! Invoking sftp subsystem')
        channel.invoke_subsystem('sftp')
        handler.transfer()
    elif command:
        logging.debug('!!! Sending command %s' % command)
        channel.exec_command(' '.join(command))
        handler.transfer()
    else:
        logging.debug('!!! Opening shell')
        channel.get_pty()
        channel.invoke_shell()
        handler.shell()

    logging.debug('!!! Done')
    status = channel.recv_exit_status()
    client.close()

    return status


if __name__ == '__main__':
    main()


# ... with blackjack, and hookers.
