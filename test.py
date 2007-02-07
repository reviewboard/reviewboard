#!/usr/bin/env python
#
# test.py -- Nose based tester
#
# Copyright (C) 2007 David Trowbridge
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from django.conf import settings
from django.core import management
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.utils import create_test_db, destroy_test_db
import nose
import reviewboard

def runner(module_list, verbosity=1, extra_tests=[]):
    setup_test_environment()
    settings.DEBUG = False
    old_name = settings.DATABASE_NAME
    create_test_db(verbosity)
    management.syncdb(verbosity, interactive=False)

    # nose uses pretty much everything in locals, which is really silly
    exclusion = '|'.join(['setup_test_environment',
                          'teardown_test_environment',
                          'create_test_db',
                          'destroy_test_db'])

    covers = ','.join(['reviewboard'])

    nose.main(argv=['test.py', '-v',
                    '--with-coverage', '--cover-package=' + covers,
                    '--with-doctest', '--doctest-extension=.py',
                    '-e', exclusion])

    destroy_test_db(old_name, verbosity)
    teardown_test_environment()
