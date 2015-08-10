#
# siteconfig.py -- Siteconfig definitions for the log app
#
# Copyright (c) 2008-2009  Christian Hammond
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

from djblets.log import DEFAULT_LOG_LEVEL

settings_map = {
    'logging_enabled':         'LOGGING_ENABLED',
    'logging_directory':       'LOGGING_DIRECTORY',
    'logging_allow_profiling': 'LOGGING_ALLOW_PROFILING',
    'logging_level':           'LOGGING_LEVEL',
}

defaults = {
    'logging_enabled':         False,
    'logging_directory':       None,
    'logging_allow_profiling': False,
    'logging_level':           DEFAULT_LOG_LEVEL,
}
