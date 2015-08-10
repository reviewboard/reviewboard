#
# djblets_deco.py -- Decorational template tags
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

from __future__ import unicode_literals

from django import template
from django.template.loader import render_to_string

from djblets.util.decorators import blocktag


register = template.Library()


@register.tag
@blocktag
def box(context, nodelist, classname=None):
    """
    Displays a box container around content, with an optional class name.
    """
    return render_to_string('deco/box.html', {
        'classname': classname or "",
        'content': nodelist.render(context)
    })


@register.tag
@blocktag
def errorbox(context, nodelist, box_id=None):
    """
    Displays an error box around content, with an optional ID.
    """
    return render_to_string('deco/errorbox.html', {
        'box_id': box_id or "",
        'content': nodelist.render(context)
    })
