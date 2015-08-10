#
# __init__.py -- Basic version and package information
#
# Copyright (c) 2007-2013  Christian Hammond
# Copyright (c) 2007-2013  David Trowbridge
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


# The version of Djblets
#
# This is in the format of:
#
#   (Major, Minor, Micro, alpha/beta/rc/final, Release Number, Released)
#
VERSION = (0, 8, 21, 'final', 0, True)


# Required version of Django
django_version = 'Django>=1.6.11,<1.7'


def get_version_string():
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += ".%s" % VERSION[2]

    if VERSION[3] != 'final':
        if VERSION[3] == 'rc':
            version += ' RC%s' % VERSION[4]
        else:
            version += ' %s %s' % (VERSION[3], VERSION[4])

    if not is_release():
        version += " (dev)"

    return version


def get_package_version():
    version = '%d.%d' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += ".%d" % VERSION[2]

    if VERSION[3] != 'final':
        version += '%s%d' % (VERSION[3], VERSION[4])

    return version


def is_release():
    return VERSION[5]


__version_info__ = VERSION[:-1]
__version__ = get_package_version()
