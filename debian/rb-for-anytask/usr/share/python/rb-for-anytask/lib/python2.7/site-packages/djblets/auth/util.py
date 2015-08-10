#
# util.py - Helper utilities for authentication
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
# Copyright (c) 2007  Micah Dowty
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

from django import forms
from django.utils.translation import ugettext as _


def validate_test_cookie(form, request):
    if not request.session.test_cookie_worked():
        form.errors['submit'] = forms.util.ErrorList(
            [_('Cookies must be enabled.')])


def validate_old_password(form, user, field_name='password'):
    if (not form.errors.get(field_name) and
            not user.check_password(form.data.get(field_name))):
        form.errors[field_name] = forms.util.ErrorList(
            [_('Incorrect password.')])
