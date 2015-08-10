from __future__ import unicode_literals

from django.conf.urls import url
from django.core.urlresolvers import RegexURLPattern
from django.views.decorators.cache import never_cache


def never_cache_patterns(prefix, *args):
    """
    Prevents any included URLs from being cached by the browser.

    It's sometimes desirable not to allow browser caching for a set of URLs.
    This can be used just like patterns().
    """
    pattern_list = []
    for t in args:
        if isinstance(t, (list, tuple)):
            t = url(prefix=prefix, *t)
        elif isinstance(t, RegexURLPattern):
            t.add_prefix(prefix)

        t._callback = never_cache(t.callback)
        pattern_list.append(t)

    return pattern_list
