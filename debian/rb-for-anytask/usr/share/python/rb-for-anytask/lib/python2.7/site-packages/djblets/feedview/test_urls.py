from __future__ import unicode_literals

import os.path

from django.conf.urls import patterns


FEED_URL = "file://%s/testdata/sample.rss" % os.path.dirname(__file__)


urlpatterns = patterns(
    'djblets.feedview.views',

    (r'^feed/$',
     'view_feed',
     {
         'template_name': 'feedview/feed-page.html',
         'url': FEED_URL
     }),
    (r'^feed-inline/$',
     'view_feed',
     {
         'template_name': 'feedview/feed-inline.html',
         'url': FEED_URL
     }),
    (r'^feed-error/$',
     'view_feed',
     {
         'template_name':
         'feedview/feed-inline.html',
         'url': 'http://example.fake/dummy.rss'
     }),
)
