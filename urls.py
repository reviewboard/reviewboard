import os.path

from django.conf import settings
from django.conf.urls.defaults import patterns, include, handler404, handler500

from reviewboard.reviews.feeds import RssReviewsFeed, AtomReviewsFeed, \
                                      RssSubmitterReviewsFeed, \
                                      AtomSubmitterReviewsFeed, \
                                      RssGroupReviewsFeed, \
                                      AtomGroupReviewsFeed


rss_feeds = {
    'r': RssReviewsFeed,
    'users': RssSubmitterReviewsFeed,
    'groups': RssGroupReviewsFeed,
}


atom_feeds = {
    'r': AtomReviewsFeed,
    'users': AtomSubmitterReviewsFeed,
    'groups': AtomGroupReviewsFeed,
}


# Main includes
urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^api/json/', include('reviewboard.webapi.urls')),
    (r'^r/', include('reviewboard.reviews.urls')),
    (r'^reports/', include('reviewboard.reports.urls')),
)


# reviewboard.reviews.views
urlpatterns += patterns('reviewboard.reviews.views',
    # Review request browsing
    (r'^dashboard/$', 'dashboard'),

    # Users
    (r'^users/$', 'submitter_list'),
    (r'^users/(?P<username>[A-Za-z0-9_\-\.]+)/$', 'submitter'),

    # Groups
    (r'^groups/$', 'group_list'),
    (r'^groups/(?P<name>[A-Za-z0-9_-]+)/$', 'group'),
)


# django.contrib
urlpatterns += patterns('django.contrib',
   # Feeds
    (r'^feeds/rss/(?P<url>.*)/$', 'syndication.views.feed',
     {'feed_dict': rss_feeds}),
    (r'^feeds/atom/(?P<url>.*)/$', 'syndication.views.feed',
     {'feed_dict': atom_feeds}),
    (r'^account/logout/$', 'auth.views.logout',
     {'next_page': settings.LOGIN_URL}),
)


# And the rest ...
urlpatterns += patterns('',
    (r'^$', 'django.views.generic.simple.redirect_to', {'url': 'dashboard/'}),

    # Authentication and accounts
    (r'^account/login/$', 'djblets.auth.views.login',
     {'next_page': settings.SITE_ROOT + 'dashboard/',
      'extra_context': {'BUILTIN_AUTH': settings.BUILTIN_AUTH}}),
    (r'^account/preferences/$', 'reviewboard.accounts.views.user_preferences',),

    # This must be last.
    (r'^iphone/', include('reviewboard.iphone.urls')),
)

if settings.BUILTIN_AUTH:
    urlpatterns += patterns('',
        (r'^account/register/$', 'djblets.auth.views.register',
         {'next_page': settings.SITE_ROOT + 'dashboard/'}),
    )
else:
    urlpatterns += patterns('',
        (r'^account/register/$',
         'django.views.generic.simple.redirect_to',
         {'url': settings.SITE_ROOT + 'account/login/'}))


# Add static media if running in DEBUG mode
if settings.DEBUG:
    def htdocs_path(leaf):
        return os.path.join(settings.HTDOCS_ROOT, leaf)

    urlpatterns += patterns('django.views.static',
        (r'^css/(?P<path>.*)$', 'serve', {
            'show_indexes': True,
            'document_root': htdocs_path('css'),
            }),
        (r'^images/(?P<path>.*)$', 'serve', {
            'show_indexes': True,
            'document_root': htdocs_path('images'),
            }),
        (r'^scripts/(?P<path>.*)$', 'serve', {
            'show_indexes': True,
            'document_root': htdocs_path('scripts')
            }),
    )
