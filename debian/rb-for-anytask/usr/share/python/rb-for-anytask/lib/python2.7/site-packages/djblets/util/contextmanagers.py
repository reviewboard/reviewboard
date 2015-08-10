#
# misc.py -- Miscellaneous utilities.
#
# Copyright (c) 2011  Beanbag, Inc.
# Copyright (c) 2011  Mike Conley
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

from contextlib import contextmanager
import logging
import os
import signal
import sys

from django.utils.translation import ugettext as _


def kill_process(pid):
    """Kill a process."""
    # This is necessary because we need to continue supporting Python 2.5,
    # which doesn't have Popen.kill(). This is inspired by
    # http://stackoverflow.com/questions/1064335
    if sys.platform == 'win32':
        import ctypes
        PROCESS_TERMINATE = 1
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_TERMINATE, False, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGKILL)


@contextmanager
def controlled_subprocess(process_name, process):
    """
    A context manager for a subprocess that guarantees that a process
    is terminated, even if exceptions are thrown while using it.

    The process_name argument is used for logging when the process goes
    down fighting.  The process argument is a process returned by
    subprocess.Popen.

    Example usage:

    process = subprocess.Popen(['patch', '-o', newfile, oldfile])

    with controlled_subprocess("patch", process) as p:
        # ... do things with the process p

    Once outside the with block, you can rest assured that the subprocess
    is no longer running.
    """

    caught_exception = None

    try:
        yield process
    except Exception as e:
        caught_exception = e

    # If we haven't gotten a returncode at this point, we assume the
    # process is blocked.  Let's kill it.
    if process.returncode is None and process.poll() is None:
        logging.warning(
            _("The process '%(name)s' with PID '%(pid)s' did not exit "
              "cleanly and will be killed automatically.")
            % {
                'name': process_name,
                'pid': process.pid,
            })

        kill_process(process.pid)
        # Now that we've killed the process, we'll grab the return code,
        # in order to clear the zombie.
        process.wait()

    # If we caught an exception earlier, re-raise it.
    if caught_exception:
        raise caught_exception
