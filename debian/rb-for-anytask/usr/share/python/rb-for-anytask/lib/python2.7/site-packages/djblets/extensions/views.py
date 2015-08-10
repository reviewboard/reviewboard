#
# views.py -- Views for the Admin UI.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
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

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect


@csrf_protect
@staff_member_required
def extension_list(request, extension_manager,
                   template_name='extensions/extension_list.html'):
    if request.method == 'POST':
        if 'full-reload' in request.POST:
            extension_manager.load(full_reload=True)

        return HttpResponseRedirect('.')
    else:
        # Refresh the extension list.
        extension_manager.load()

        return render_to_response(template_name, RequestContext(request))


@csrf_protect
@staff_member_required
def configure_extension(request, ext_class, form_class, extension_manager,
                        template_name='extensions/configure_extension.html'):
    extension = extension_manager.get_enabled_extension(ext_class.id)

    if not extension or not extension.is_configurable:
        raise Http404

    if request.method == 'POST':
        form = form_class(extension, request.POST, request.FILES)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(request.path + '?saved=1')
    else:
        form = form_class(extension)

    return render_to_response(template_name, RequestContext(request, {
        'extension': extension,
        'form': form,
        'saved': request.GET.get('saved', 0),
    }))
