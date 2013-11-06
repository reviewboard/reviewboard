#!/usr/bin/env python

from __future__ import unicode_literals

import os
import sys

from django.core.management.commands.compilemessages import compile_messages
from djblets.util.filesystem import is_exe_in_path


if __name__ == '__main__':
    if not is_exe_in_path('msgfmt'):
        raise RuntimeError('Could not find the "msgfmt" binary.')

    cwd = os.getcwd()
    os.chdir(os.path.realpath('reviewboard'))
    compile_messages(sys.stdout)
    os.chdir(cwd)
