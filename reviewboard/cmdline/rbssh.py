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
import logging
import os
import select
import sys
import warnings
from optparse import OptionParser


# We don't want any warnings to end up impacting output.
warnings.simplefilter('ignore')

logger = logging.getLogger(__name__)


if str('RBSITE_PYTHONPATH') in os.environ:
    for path in reversed(os.environ[str('RBSITE_PYTHONPATH')].split(str(':'))):
        sys.path.insert(1, path)

os.environ[str('DJANGO_SETTINGS_MODULE')] = \
    str('reviewboard.cmdline.conf.rbssh.settings')

import django
import paramiko

import reviewboard
from reviewboard import get_version_string


DEBUG = os.getenv('RBSSH_DEBUG') or os.getenv('DEBUG_RBSSH')
DEBUG_LOGDIR = os.getenv('RBSSH_LOG_DIR')
STORAGE_BACKEND = os.getenv('RBSSH_STORAGE_BACKEND')

SSH_PORT = 22

# This is the maximum size we'll read from the buffer. If there's less
# data available than this, it won't block, it'll just return the
# available data.
BUFFER_SIZE = 16384


options = None


if DEBUG:
    debug = logging.debug
else:
    debug = lambda *args, **kwargs: None


class PlatformHandler(object):
    """A generic base class for wrapping platform-specific operations.

    This should be subclassed for each major platform.
    """

    def __init__(self, channel):
        """Initialize the handler.

        Args:
            channel (paramiko.channel.Channel):
                The channel to process.
        """
        self.channel = channel
        self.stdin_fd = sys.stdin.fileno()
        self.stdout_fd = sys.stdout.fileno()
        self.stderr_fd = sys.stderr.fileno()

    def shell(self):
        """Open a shell."""
        raise NotImplementedError

    def transfer(self):
        """Transfer data over the channel."""
        raise NotImplementedError

    def write_input(self, data):
        """Write input to a channel.

        This will write to the channel, ensuring the full contents of the data
        have been written before this returns.

        This is used for stdin.

        Version Added:
            4.0.11

        Args:
            data (bytes):
                The data to write.
        """
        channel = self.channel
        written = 0

        while written < len(data):
            try:
                written += channel.send(data[written:])
            except OSError:
                pass

    def write_output(self, fd, data):
        """Write output to a file descriptor.

        This will write to the file descriptor, handling blocking I/O errors
        and ensuring the full contents of the data have been written before
        this returns.

        This is used for stdout and stderr.

        Args:
            fd (int):
                The file descriptor.

            data (bytes):
                The data to write.
        """
        written = 0

        while written < len(data):
            try:
                written += os.write(fd, data[written:])
            except OSError:
                pass

    def process_channel(self, channel):
        """Process the given channel.

        This will retrieve any data from the output and error streams and
        output it to stdout and stderr.

        Processing will finish when no new data can be read, no new data is
        available to read, and an exit status is available.

        Args:
            channel (paramiko.channel.Channel):
                The channel to process.

        Returns:
            bool:
            ``True`` if the channel should continue to be processed.
            ``False`` if processing has completed.
        """
        debug('!! process_channel\n')

        has_data = False

        if channel.recv_ready():
            data = channel.recv(BUFFER_SIZE)

            if data:
                debug('!! got stdout=%r\n' % data)
                has_data = True

                self.write_output(self.stdout_fd, data)

        if channel.recv_stderr_ready():
            data = channel.recv_stderr(BUFFER_SIZE)

            if data:
                debug('!! got stderr=%r\n' % data)
                has_data = True

                self.write_output(self.stderr_fd, data)

        if (not has_data and
            channel.exit_status_ready() and
            not channel.recv_ready() and
            not channel.recv_stderr_ready()):
            # There should truly be nothing left to process. Everything has
            # indicated that the communication is done.
            debug('!!! no data to read; exit ready; channel closed.\n')
            return False

        return True

    def process_stdin(self):
        """Read data from stdin and send it over the channel.

        Version Changed:
            4.0.11:
            Removed the ``channel`` argument.

        Returns:
            bool:
            ``True`` if the channel should continue to be processed.
            ``False`` if processing has completed.
        """
        debug('!! process_stdin\n')

        try:
            buf = os.read(self.stdin_fd, BUFFER_SIZE)
        except OSError:
            buf = None

        if not buf:
            debug('!! stdin empty\n')
            return False

        self.write_input(buf)

        return True


class PosixHandler(PlatformHandler):
    """A platform handler for POSIX-type platforms."""

    def shell(self):
        """Open a shell."""
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
        """Transfer data over the channel."""
        import fcntl

        # Set all streams to be non-blocking. We'll manage the reading/writing
        # accordingly, handling any blocking I/O errors. This will ensure
        # that we don't buffer too long and risk any communication issues.
        for stream in (sys.stdin, sys.stdout, sys.stderr):
            fd = stream.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.handle_communications()

    def handle_communications(self):
        """Handle any pending data over the channel or stdin."""
        channel = self.channel

        while True:
            rl, wl, el = select.select([channel, sys.stdin], [], [])

            if channel in rl:
                if not self.process_channel(channel):
                    break

            if sys.stdin in rl:
                if not self.process_stdin():
                    channel.shutdown_write()
                    break


class WindowsHandler(PlatformHandler):
    """A platform handler for Microsoft Windows platforms."""

    def shell(self):
        """Open a shell."""
        self.handle_communications()

    def transfer(self):
        """Transfer data over the channel."""
        self.handle_communications()

    def handle_communications(self):
        """Handle any pending data over the channel or stdin."""
        import threading

        debug('!! begin_windows_transfer\n')

        self.channel.setblocking(0)

        def writeall(channel):
            while self.process_channel(channel):
                pass

            debug('!! Shutting down reading\n')
            channel.shutdown_read()

        writer = threading.Thread(target=writeall, args=(self.channel,))
        writer.start()

        try:
            while self.process_stdin():
                pass
        except EOFError:
            pass

        debug('!! Shutting down writing\n')
        self.channel.shutdown_write()


def print_version(option, opt, value, parser):
    """Print the current version and exit."""
    parser.print_version()
    sys.exit(0)


def parse_options(args):
    """Parse the given arguments into the global ``options`` dictionary."""
    global options

    hostname = None

    # NOTE: Update to use RBProgVersionAction when this is ported to argparse.
    parser = OptionParser(
        usage='%prog [options] [user@]hostname [command]',
        version=(
            '%%prog %s\n'
            'Python %s\n'
            'Installed to %s'
            % (get_version_string(),
               sys.version.splitlines()[0],
               os.path.dirname(reviewboard.__file__))
        ))
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
    """Run the application."""
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

        debug('%s', sys.argv)
        debug('PID %s', pid)

    # Perform the bare minimum to initialize the Django/Review Board
    # environment. We're not calling Review Board's initialize() because
    # we want to completely minimize what we import and set up.
    if hasattr(django, 'setup'):
        django.setup()

    from reviewboard.scmtools.core import SCMTool
    from reviewboard.ssh.client import SSHClient

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

    client = SSHClient(namespace=options.local_site_name,
                       storage_backend=STORAGE_BACKEND)
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    if command:
        purpose = command
    else:
        purpose = 'interactive shell'

    debug('!!! SSH backend = %s', type(client.storage))
    debug('!!! Preparing to connect to %s@%s for %s',
          username, hostname, purpose)

    attempts = 0
    password = None

    key = client.get_user_key()

    while True:
        try:
            client.connect(hostname, port, username=username,
                           password=password, pkey=key,
                           allow_agent=options.allow_agent)
            break
        except paramiko.AuthenticationException:
            if attempts == 3 or not sys.stdin.isatty():
                logger.error('Too many authentication failures for %s',
                             username)
                sys.exit(1)

            attempts += 1
            password = getpass.getpass("%s@%s's password: " %
                                       (username, hostname))
        except paramiko.SSHException as e:
            logger.error('Error connecting to server: %s', e)
            sys.exit(1)
        except Exception as e:
            logger.error('Unknown exception during connect: %s (%s)',
                         e, type(e))
            sys.exit(1)

    transport = client.get_transport()
    channel = transport.open_session()

    if sys.platform in ('cygwin', 'win32'):
        debug('!!! Using WindowsHandler')
        handler = WindowsHandler(channel)
    else:
        debug('!!! Using PosixHandler')
        handler = PosixHandler(channel)

    if options.subsystem == 'sftp':
        debug('!!! Invoking sftp subsystem')
        channel.invoke_subsystem('sftp')
        handler.transfer()
    elif command:
        debug('!!! Sending command %s', command)
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

    return status


if __name__ == '__main__':
    main()


# ... with blackjack, and hookers.
