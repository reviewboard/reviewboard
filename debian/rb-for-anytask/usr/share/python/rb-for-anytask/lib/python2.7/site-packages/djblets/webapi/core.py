#
# core.py -- Core classes for webapi
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

from djblets.webapi.decorators import SPECIAL_PARAMS
from djblets.webapi.encoders import (BasicAPIEncoder, JSONEncoderAdapter,
                                     WebAPIEncoder, XMLEncoderAdapter,
                                     get_registered_encoders)
from djblets.webapi.responses import (WebAPIResponse, WebAPIResponseError,
                                      WebAPIResponseFormError,
                                      WebAPIResponsePaginated)


warnings.warn('djblets.webapi.core is deprecated', DeprecationWarning)


__all__ = [
    'BasicAPIEncoder',
    'JSONEncoderAdapter',
    'SPECIAL_PARAMS',
    'WebAPIEncoder',
    'WebAPIResponse',
    'WebAPIResponseError',
    'WebAPIResponseFormError',
    'WebAPIResponsePaginated',
    'XMLEncoderAdapter',
    'get_registered_encoders',
]
