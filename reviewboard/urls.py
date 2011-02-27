from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

from reviewboard.reviews.feeds import RssReviewsFeed, AtomReviewsFeed, \
                                      RssSubmitterReviewsFeed, \
                                      AtomSubmitterReviewsFeed, \
                                      RssGroupReviewsFeed, \
                                      AtomGroupReviewsFeed
from reviewboard.webapi.resources import root_resource
from reviewboard import initialize


initialize()

# Load in all the models for the admin UI.
if not admin.site._registry:
    admin.autodiscover()


# URLs global to all modes
urlpatterns = patterns('',
    (r'^admin/', include('reviewboard.admin.urls')),
)

# Add static media if running in DEBUG mode
if settings.DEBUG or getattr(settings, 'RUNNING_TEST', False):
    from django import VERSION

    static_args = {
        'show_indexes': True,
        'document_root': settings.MEDIA_ROOT,
    }

    if (VERSION[0] > 1 or (VERSION[0] == 1 and VERSION[1] >= 3)):
        static_args['insecure'] = True

    urlpatterns += patterns('django.views.static',
        (r'^media/(?P<path>.*)$', 'serve', static_args)
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


localsite_urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.simple.redirect_to',
        {'url': 'dashboard/'},
        name="root"),

    (r'^api/', include(root_resource.get_url_patterns())),
    (r'^r/', include('reviewboard.reviews.urls')),

    # Dashboard
    url(r'^dashboard/$',
        'reviewboard.reviews.views.dashboard', name="dashboard"),

    # Users
    url(r'^users/$',
        'reviewboard.reviews.views.submitter_list', name="all-users"),
    url(r'^users/(?P<username>[A-Za-z0-9@_\-\.]+)/$',
        'reviewboard.reviews.views.submitter', name="user"),
    url(r'^users/(?P<username>[A-Za-z0-9@_\-\.]+)/infobox/$',
        'reviewboard.reviews.views.user_infobox', name="user-infobox"),

    # Groups
    url(r'^groups/$',
        'reviewboard.reviews.views.group_list', name="all-groups"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/$',
        'reviewboard.reviews.views.group', name="group"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/members/$',
        'reviewboard.reviews.views.group_members', name="group_members"),
)


# Main includes
urlpatterns += patterns('',
    (r'^account/', include('reviewboard.accounts.urls')),
    (r'^reports/', include('reviewboard.reports.urls')),

    (r'^s/(?P<local_site_name>[A-Za-z0-9\-_.]+)/',
     include(localsite_urlpatterns)),
)

urlpatterns += localsite_urlpatterns


# django.contrib
urlpatterns += patterns('django.contrib',
   # Feeds
    url(r'^feeds/rss/(?P<url>.*)/$', 'syndication.views.feed',
        {'feed_dict': rss_feeds}, name="rss-feed"),
    url(r'^feeds/atom/(?P<url>.*)/$', 'syndication.views.feed',
        {'feed_dict': atom_feeds}, name="atom-feed"),
    url(r'^account/logout/$', 'auth.views.logout',
        {'next_page': settings.LOGIN_URL}, name="logout")
)
