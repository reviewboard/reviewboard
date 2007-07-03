#
# test.py -- Nose based tester
#
# Copyright (c) 2007  David Trowbridge
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

import sys

import nose

from django.conf import settings
from django.core import management
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.utils import create_test_db, destroy_test_db

import reviewboard

def runner(module_list, verbosity=1, extra_tests=[]):
    setup_test_environment()
    settings.DEBUG = False
    old_name = settings.DATABASE_NAME
    create_test_db(verbosity)
    management.syncdb(verbosity, interactive=False)

    # Nose uses all local modules, which is really silly.  These were getting
    # tested (and failing), so turn them off.
    exclusion = '|'.join(['setup_test_environment',
                          'teardown_test_environment',
                          'create_test_db',
                          'destroy_test_db'])

    covers = ','.join(['reviewboard'])

    nose_argv=['test.py', '-v',
               '--with-coverage', '--cover-package=' + covers,
               '--with-doctest', '--doctest-extension=.txt',
               '-e', exclusion]
    if len(sys.argv) > 2:
        nose_argv += sys.argv[2:]
    nose.main(argv=nose_argv)

    destroy_test_db(old_name, verbosity)
    teardown_test_environment()
