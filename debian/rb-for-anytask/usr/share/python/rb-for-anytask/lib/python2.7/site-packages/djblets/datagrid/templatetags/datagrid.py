#
# datagrid.py -- Template tags used in datagrids
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2008-2009  David Trowbridge
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

from django import template


register = template.Library()


# Heavily based on paginator by insin
# http://www.djangosnippets.org/snippets/73/
@register.inclusion_tag('datagrid/paginator.html', takes_context=True)
def paginator(context, adjacent_pages=3):
    """Renders a paginator used for jumping between pages of results."""

    warnings.warn('djblets.datagrid.templatetags datagrid is deprecated,'
                  ' Use DataGrid.render_paginator', DeprecationWarning)

    page_nums = range(max(1, context['page'] - adjacent_pages),
                      min(context['pages'], context['page'] + adjacent_pages)
                      + 1)

    extra_query = context.get('extra_query', None)
    if extra_query:
        extra_query += '&'

    return {
        'hits': context['hits'],
        'results_per_page': context['results_per_page'],
        'page': context['page'],
        'pages': context['pages'],
        'page_numbers': page_nums,
        'next': context['next'],
        'previous': context['previous'],
        'has_next': context['has_next'],
        'has_previous': context['has_previous'],
        'show_first': 1 not in page_nums,
        'show_last': context['pages'] not in page_nums,
        'extra_query': extra_query,
    }
