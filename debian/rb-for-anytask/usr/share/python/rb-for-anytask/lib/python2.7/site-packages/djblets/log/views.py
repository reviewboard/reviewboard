#
# views.py -- Views for the log app
#
# Copyright (c) 2009  Christian Hammond
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

import calendar
import codecs
import datetime
import logging
import os
import re
import time

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils import six
from django.utils.six.moves.urllib.parse import urlencode
from django.utils.translation import ugettext_lazy as _


LEVELS = (
    (logging.DEBUG, 'debug', _('Debug')),
    (logging.INFO, 'info', _('Info')),
    (logging.WARNING, 'warning', _('Warning')),
    (logging.ERROR, 'error', _('Error')),
    (logging.CRITICAL, 'critical', _('Critical')),
)


# Matches the default timestamp format in the logging module.
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'

LOG_LINE_RE = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - '
    r'(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL) - '
    r'(?P<message>.*)')


def parse_timestamp(format, timestamp_str):
    """Utility function to parse a timestamp into a datetime.datetime.

    Python 2.5 and up have datetime.strptime, but Python 2.4 does not,
    so we roll our own as per the documentation.

    If passed a timestamp_str of None, we will return None as a convenience.
    """
    if not timestamp_str:
        return None

    return datetime.datetime(*time.strptime(timestamp_str, format)[0:6])


def build_query_string(request, params):
    """Builds a query string that includes the specified parameters along
    with those that were passed to the page.

    params is a dictionary.
    """
    query_parts = []

    for key, value in six.iteritems(request.GET):
        if key not in params:
            query_parts.append(urlencode({
                key: value
            }))

    for key, value in six.iteritems(params):
        if value is not None:
            query_parts.append(urlencode({
                key: value
            }))

    return '?' + '&'.join(query_parts)


def iter_log_lines(from_timestamp, to_timestamp, requested_levels):
    """Generator that iterates over lines in a log file, yielding the
    yielding information about the lines."""
    log_filename = os.path.join(settings.LOGGING_DIRECTORY,
                                settings.LOGGING_NAME + '.log')

    line_info = None

    try:
        fp = codecs.open(log_filename, encoding='utf-8')
    except IOError:
        # We'd log this, but it'd do very little good in practice.
        # It would only appear on the console when using the development
        # server, but production users would never see anything. So,
        # just return gracefully. We'll show an empty log, which is
        # about accurate.
        return

    for line in fp:
        line = line.rstrip()

        m = LOG_LINE_RE.match(line)

        if m:
            if line_info:
                # We have a fully-formed log line and this new line isn't
                # part of it, so yield it now.
                yield line_info
                line_info = None

            timestamp_str = m.group('timestamp')
            level = m.group('level')
            message = m.group('message')

            if not requested_levels or level.lower() in requested_levels:
                timestamp = parse_timestamp(TIMESTAMP_FMT,
                                            timestamp_str.split(',')[0])

                timestamp_date = timestamp.date()

                if ((from_timestamp and from_timestamp > timestamp_date) or
                    (to_timestamp and to_timestamp < timestamp_date)):
                    continue

                line_info = (timestamp, level, message)
        elif line_info:
            line_info = (line_info[0],
                         line_info[1],
                         line_info[2] + "\n" + line)

    if line_info:
        yield line_info

    fp.close()


def get_log_filtersets(request, requested_levels,
                       from_timestamp, to_timestamp):
    """Returns the filtersets that will be used in the log view."""
    logger = logging.getLogger('')
    level_filters = [
        {
            'name': _('All'),
            'url': build_query_string(request, {'levels': None}),
            'selected': len(requested_levels) == 0,
        }
    ] + [
        {
            'name': label_name,
            'url': build_query_string(request, {'levels': level_name}),
            'selected': level_name in requested_levels,
        }
        for level_id, level_name, label_name in LEVELS
        if logger.isEnabledFor(level_id)
    ]

    from_timestamp_str = request.GET.get('from', None)
    to_timestamp_str = request.GET.get('to', None)
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    one_week_ago = today - datetime.timedelta(days=7)
    one_week_ago_str = one_week_ago.strftime('%Y-%m-%d')
    month_range = calendar.monthrange(today.year, today.month)
    this_month_begin_str = today.strftime('%Y-%m-01')
    this_month_end_str = today.strftime('%Y-%m-') + str(month_range[1])

    date_filters = [
        {
            'name': _('Any date'),
            'url': build_query_string(request, {
                'from': None,
                'to': None,
            }),
            'selected': (from_timestamp_str is None and
                         to_timestamp_str is None),
        },
        {
            'name': _('Today'),
            'url': build_query_string(request, {
                'from': today_str,
                'to': today_str,
            }),
            'selected': (from_timestamp_str == today_str and
                         to_timestamp_str == today_str),
        },
        {
            'name': _('Past 7 days'),
            'url': build_query_string(request, {
                'from': one_week_ago_str,
                'to': today_str,
            }),
            'selected': (from_timestamp_str == one_week_ago_str and
                         to_timestamp_str == today_str),
        },
        {
            'name': _('This month'),
            'url': build_query_string(request, {
                'from': this_month_begin_str,
                'to': this_month_end_str,
            }),
            'selected': (from_timestamp_str == this_month_begin_str and
                         to_timestamp_str == this_month_end_str),
        },
    ]

    return (
        (_("By date"), date_filters),
        (_("By level"), level_filters),
    )


@staff_member_required
def server_log(request, template_name='log/log.html'):
    """Displays the server log."""

    # First check if logging is even configured. If it's not, just return
    # a 404.
    if (not getattr(settings, "LOGGING_ENABLED", False) or
        not getattr(settings, "LOGGING_DIRECTORY", None)):
        raise Http404()

    requested_levels = []

    # Get the list of levels to show.
    if 'levels' in request.GET:
        requested_levels = request.GET.get('levels').split(',')

    # Get the timestamp ranges.
    from_timestamp = parse_timestamp('%Y-%m-%d', request.GET.get('from'))
    to_timestamp = parse_timestamp('%Y-%m-%d', request.GET.get('to'))

    if from_timestamp:
        from_timestamp = from_timestamp.date()

    if to_timestamp:
        to_timestamp = to_timestamp.date()

    # Get the filters to show.
    filtersets = get_log_filtersets(request, requested_levels,
                                    from_timestamp, to_timestamp)

    # Grab the lines from the log file.
    log_lines = iter_log_lines(from_timestamp, to_timestamp, requested_levels)

    # Figure out the sorting
    sort_type = request.GET.get('sort', 'asc')

    if sort_type == 'asc':
        reverse_sort_type = 'desc'
    else:
        reverse_sort_type = 'asc'
        log_lines = reversed(list(log_lines))

    response = render_to_response(template_name, RequestContext(request, {
        'log_lines': log_lines,
        'filtersets': filtersets,
        'sort_url': build_query_string(request, {'sort': reverse_sort_type}),
        'sort_type': sort_type,
    }))

    return response
