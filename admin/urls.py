from django.conf.urls.defaults import *


NEWS_FEED = "http://www.review-board.org/news/feed/"

urlpatterns = patterns('reviewboard.admin.views',
    ('^$', 'dashboard'),
    ('^cache/$', 'cache_stats'),
)

urlpatterns += patterns('',
    ('^db/', include('django.contrib.admin.urls')),
    ('^feed/news/$', 'djblets.feedview.views.view_feed',
     {'template_name': 'admin/feed.html',
      'url': NEWS_FEED}),
    ('^feed/news/rss/$', 'django.views.generic.simple.redirect_to',
     {'url': NEWS_FEED}),
)
