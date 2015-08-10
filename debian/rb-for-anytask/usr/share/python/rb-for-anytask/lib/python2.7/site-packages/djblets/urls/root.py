#
# rooturl.py -- URL patterns for rooted sites.
#
# Copyright (c) 2007-2010  Christian Hammond
# Copyright (c) 2010-2013  Beanbag, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# 'Software'), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, include, handler404, handler500
from django.core.exceptions import ImproperlyConfigured


# Ensures that we can run nose on this without needing to set SITE_ROOT.
# Also serves to let people know if they set one variable without the other.
if hasattr(settings, 'SITE_ROOT'):
    if not hasattr(settings, 'SITE_ROOT_URLCONF'):
        raise ImproperlyConfigured('SITE_ROOT_URLCONF must be set when '
                                   'using SITE_ROOT')

    urlpatterns = patterns(
        '',

        (r'^%s' % settings.SITE_ROOT[1:], include(settings.SITE_ROOT_URLCONF)),
    )
else:
    urlpatterns = None


__all__ = [
    'handler404',
    'handler500',
    'urlpatterns',
]
