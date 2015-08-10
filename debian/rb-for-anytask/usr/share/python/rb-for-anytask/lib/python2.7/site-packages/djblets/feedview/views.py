from __future__ import unicode_literals

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.six.moves import http_client
from django.utils.six.moves.urllib.error import URLError
from django.utils.six.moves.urllib.request import urlopen

from djblets.cache.backend import cache_memoize


DEFAULT_EXPIRATION = 2 * 24 * 60 * 60  # 2 days


def view_feed(request, url, template_name="feedview/feed-page.html",
              cache_expiration=DEFAULT_EXPIRATION, extra_context={}):
    """
    Renders an RSS or Atom feed using the given template. This will use
    a cached copy if available in order to reduce hits to the server.
    """
    def fetch_feed():
        import feedparser

        data = urlopen(url).read()

        parser = feedparser.parse(data)

        context = {
            'parser': parser,
        }
        context.update(extra_context)

        return render_to_string(template_name,
                                RequestContext(request, context))

    try:
        return HttpResponse(cache_memoize("feed-%s" % url, fetch_feed,
                            cache_expiration,
                            force_overwrite=('reload' in request.GET)))
    except (URLError, http_client.HTTPException) as e:
        context = {
            'error': e,
        }
        context.update(extra_context)

        return render_to_response(template_name,
                                  RequestContext(request, context))
