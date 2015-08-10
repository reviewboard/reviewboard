from __future__ import unicode_literals

import calendar
import datetime

from django import template


register = template.Library()


@register.filter
def feeddate(datetuple):
    """
    A filter that converts the date tuple provided from feedparser into
    a datetime object.
    """
    return datetime.datetime.utcfromtimestamp(calendar.timegm(datetuple))
