#
# djblets_email.py -- E-mail formatting template tags
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

import re

from django import template
from django.template.loader import render_to_string

from djblets.util.decorators import basictag, blocktag


register = template.Library()


@register.tag
@basictag(takes_context=True)
def quoted_email(context, template_name):
    """
    Renders a specified template as a quoted reply, using the current context.
    """
    return quote_text(render_to_string(template_name, context))


@register.tag
@blocktag
def condense(context, nodelist, max_newlines=3):
    """Condenses a block of text.

    This will ensure that there are never more than the given number of
    consecutive newlines. It's particularly useful when formatting plain text
    output, to avoid issues with template tags adding unwanted newlines.
    """
    text = nodelist.render(context).strip()
    text = re.sub(r'\n{%d,}' % (max_newlines + 1), '\n' * max_newlines, text)
    return text


@register.filter
def quote_text(text, level=1):
    """
    Quotes a block of text the specified number of times.
    """
    lines = text.split("\n")
    quoted = ""

    for line in lines:
        quoted += "%s%s\n" % ("> " * level, line)

    return quoted.rstrip()
