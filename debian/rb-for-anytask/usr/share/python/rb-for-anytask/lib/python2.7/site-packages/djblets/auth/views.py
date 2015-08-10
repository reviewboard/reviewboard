#
# views.py -- Views for the authentication app
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
# Copyright (C) 2007 Micah Dowty
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

from django.contrib import auth
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect

from djblets.auth.forms import RegistrationForm
from djblets.auth.signals import user_registered
from djblets.auth.util import validate_test_cookie


###########################
#    User Registration    #
###########################

@csrf_protect
def register(request, next_page, form_class=RegistrationForm,
             extra_context={},
             template_name="accounts/register.html"):
    if request.method == 'POST':
        form = form_class(data=request.POST, request=request)
        form.full_clean()
        validate_test_cookie(form, request)

        if form.is_valid():
            user = form.save()
            if user:
                user = auth.authenticate(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1'])
                assert user
                auth.login(request, user)
                try:
                    request.session.delete_test_cookie()
                except KeyError:
                    # Do nothing
                    pass

                # Other components can listen to this signal to
                # perform additional tasks when a new user registers
                user_registered.send(sender=None, user=request.user)

                return HttpResponseRedirect(next_page)
    else:
        form = form_class(request=request)

    request.session.set_test_cookie()

    context = {
        'form': form,
    }
    context.update(extra_context)

    return render_to_response(template_name, RequestContext(request, context))
