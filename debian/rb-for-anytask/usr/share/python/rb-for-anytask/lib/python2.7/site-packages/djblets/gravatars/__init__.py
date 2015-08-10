#
# __init__.py -- Gravatar functionality
#
# Copyright (c) 2012       Beanbag, Inc.
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

from __future__ import unicode_literals

from hashlib import md5

from django.conf import settings


def get_gravatar_url_for_email(request, email, size=None):
    email_hash = md5(email.encode('utf-8')).hexdigest()

    if request.is_secure():
        url_base = 'https://secure.gravatar.com'
    else:
        url_base = 'http://www.gravatar.com'

    url = "%s/avatar/%s" % (url_base, email_hash)
    params = []

    if not size and hasattr(settings, "GRAVATAR_SIZE"):
        size = settings.GRAVATAR_SIZE

    if size:
        params.append("s=%s" % size)

    if hasattr(settings, "GRAVATAR_RATING"):
        params.append("r=%s" % settings.GRAVATAR_RATING)

    if hasattr(settings, "GRAVATAR_DEFAULT"):
        params.append("d=%s" % settings.GRAVATAR_DEFAULT)

    if params:
        url += "?" + "&".join(params)

    return url


def get_gravatar_url(request, user, size=None):
    if user.is_anonymous() or not user.email:
        return ""

    email = user.email.strip().lower()
    return get_gravatar_url_for_email(request, email, size)
