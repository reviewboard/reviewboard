import os.path

from django.conf import settings
from django.conf.urls.defaults import patterns, include

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

urlpatterns = patterns('',
    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^api/json/', include('reviewboard.reviews.urls.json')),
    (r'^r/', include('reviewboard.reviews.urls.reviews')),
    (r'^reports/', include('reviewboard.reports.urls')),

    (r'^$', 'django.views.generic.simple.redirect_to',
     {'url': '/dashboard/'}),

    # Review request browsing
    (r'^dashboard/$', 'reviewboard.reviews.views.dashboard'),

    # Users
    (r'^users/$', 'reviewboard.reviews.views.submitter_list'),
    (r'^users/(?P<username>[A-Za-z0-9_\-\.]+)/$',
     'reviewboard.reviews.views.submitter'),

    # Groups
    (r'^groups/$', 'reviewboard.reviews.views.group_list'),
    (r'^groups/(?P<name>[A-Za-z0-9_-]+)/$', 'reviewboard.reviews.views.group'),

    # Feeds
    (r'^feeds/rss/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
     {'feed_dict': rss_feeds}),
    (r'^feeds/atom/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
     {'feed_dict': atom_feeds}),

    # Authentication and accounts
    (r'^account/login/$', 'djblets.auth.views.login',
     {'next_page': '/dashboard/',
      'extra_context': {'BUILTIN_AUTH': settings.BUILTIN_AUTH}}),
    (r'^account/logout/$', 'django.contrib.auth.views.logout',
     {'next_page': settings.LOGIN_URL}),
    (r'^account/preferences/$', 'reviewboard.accounts.views.user_preferences',),

    # This must be last.
    (r'^iphone/', include('reviewboard.iphone.urls')),
)


if settings.BUILTIN_AUTH:
    urlpatterns += patterns('',
        (r'^account/register/$', 'djblets.auth.views.register',
         {'next_page': '/dashboard/'}),
    )
else:
    urlpatterns += patterns('',
        (r'^account/register/$',
         'django.views.generic.simple.redirect_to',
         {'url': '/account/login/'}))

# Add static media if running in DEBUG mode
if settings.DEBUG:
    def htdocs_path(leaf):
        return os.path.join(settings.HTDOCS_ROOT, leaf)

    urlpatterns += patterns('',
        (r'^css/(?P<path>.*)$', 'django.views.static.serve', {
            'show_indexes': True,
            'document_root': htdocs_path('css'),
            }),
        (r'^images/(?P<path>.*)$', 'django.views.static.serve', {
            'show_indexes': True,
            'document_root': htdocs_path('images'),
            }),
        (r'^scripts/(?P<path>.*)$', 'django.views.static.serve', {
            'show_indexes': True,
            'document_root': htdocs_path('scripts')
            }),
    )
