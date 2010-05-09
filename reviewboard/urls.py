import os.path

from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

from reviewboard.extensions.base import get_extension_manager
from reviewboard.reviews.feeds import RssReviewsFeed, AtomReviewsFeed, \
                                      RssSubmitterReviewsFeed, \
                                      AtomSubmitterReviewsFeed, \
                                      RssGroupReviewsFeed, \
                                      AtomGroupReviewsFeed
from reviewboard import initialize


extension_manager = get_extension_manager()

# Load in all the models for the admin UI.
if not admin.site._registry:
    admin.autodiscover()


# URLs global to all modes
urlpatterns = patterns('',
    (r'^admin/extensions/', include('djblets.extensions.urls'),
     {'extension_manager': extension_manager}),
    (r'^admin/', include('reviewboard.admin.urls')),
)

# Add static media if running in DEBUG mode
if settings.DEBUG or getattr(settings, 'RUNNING_TEST', False):
    urlpatterns += patterns('django.views.static',
        (r'^media/(?P<path>.*)$', 'serve', {
            'show_indexes': True,
            'document_root': settings.MEDIA_ROOT,
            }),
    )

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
urlpatterns += patterns('',
    (r'^account/', include('reviewboard.accounts.urls')),
    (r'^api/', include('reviewboard.webapi.urls')),
    (r'^r/', include('reviewboard.reviews.urls')),
    #(r'^reports/', include('reviewboard.reports.urls')),
)


# reviewboard.reviews.views
urlpatterns += patterns('reviewboard.reviews.views',
    # Review request browsing
    url(r'^dashboard/$', 'dashboard', name="dashboard"),

    # Users
    url(r'^users/$', 'submitter_list', name="all-users"),
    url(r'^users/(?P<username>[A-Za-z0-9@_\-\.]+)/$', 'submitter',
        name="user"),

    # Groups
    url(r'^groups/$', 'group_list', name="all-groups"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/$', 'group', name="group"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/members/$', 'group_members', name="group_members"),
)


# django.contrib
urlpatterns += patterns('django.contrib',
   # Feeds
    url(r'^feeds/rss/(?P<url>.*)/$', 'syndication.views.feed',
        {'feed_dict': rss_feeds},
        name="rss-feed"),
    url(r'^feeds/atom/(?P<url>.*)/$', 'syndication.views.feed',
       {'feed_dict': atom_feeds},
       name="atom-feed"),
    url(r'^account/logout/$', 'auth.views.logout',
        {'next_page': settings.LOGIN_URL},
        name="logout")
)


# And the rest ...
urlpatterns += patterns('',
    url(r'^$', 'django.views.generic.simple.redirect_to',
        {'url': 'dashboard/'},
        name="root"),

    # This must be last.
    url(r'^iphone/', include('reviewboard.iphone.urls', namespace='iphone')),
)

initialize()
