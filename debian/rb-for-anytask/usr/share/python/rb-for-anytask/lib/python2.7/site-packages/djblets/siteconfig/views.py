#
# views.py -- Views for the siteconfig app
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

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect

from djblets.siteconfig.models import SiteConfiguration


@csrf_protect
@staff_member_required
def site_settings(request, form_class,
                  template_name="siteconfig/settings.html",
                  extra_context={}):
    """
    Provides a front-end for customizing Review Board settings.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if request.method == "POST":
        form = form_class(siteconfig, request.POST, request.FILES,
                          request=request)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(".?saved=1")
    else:
        form = form_class(siteconfig, request=request)

    context = {
        'form': form,
        'saved': request.GET.get('saved', 0)
    }
    context.update(extra_context)

    return render_to_response(template_name, RequestContext(request, context))
