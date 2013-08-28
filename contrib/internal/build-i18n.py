#!/usr/bin/env python

import os
import sys

from django.core.management.commands.compilemessages import compile_messages
from djblets.util.filesystem import is_exe_in_path


if not is_exe_in_path('msgfmt'):
    raise RuntimeError('Could not find the "msgfmt" binary.')

cwd = os.getcwd()
os.chdir(os.path.realpath('reviewboard'))
compile_messages(stderr=sys.stderr)
os.chdir(cwd)
