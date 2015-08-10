#
# misc.py -- Miscellaneous utilities.
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
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
import warnings

from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.cache.serials import (generate_ajax_serial,
                                   generate_cache_serials,
                                   generate_locale_serial,
                                   generate_media_serial)
from djblets.db.query import get_object_or_none
from djblets.urls.patterns import never_cache_patterns


warnings.warn('djblets.util.misc is deprecated', DeprecationWarning)


__all__ = [
    'cache_memoize',
    'generate_ajax_serial',
    'generate_cache_serials',
    'generate_locale_serial',
    'generate_media_serial',
    'get_object_or_none',
    'make_cache_key',
    'never_cache_patterns',
]
