import logging
import os.path

from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

# We do this to guarantee we're getting the absolute "djblets.log" and not
# the relative "djblets.log" (which turns into "reviewboard.djblets.log")
# Yes, it's a hack. We can remove it when djblets is removed from the source
# directory.
log = __import__("djblets.log", {}, {}, ["log"])

from reviewboard import VERSION
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.reviews.feeds import RssReviewsFeed, AtomReviewsFeed, \
                                      RssSubmitterReviewsFeed, \
                                      AtomSubmitterReviewsFeed, \
                                      RssGroupReviewsFeed, \
                                      AtomGroupReviewsFeed


# Load all site settings.
load_site_config()

# Set up logging.
log.init_logging()
logging.info("Log file for Review Board v%s" % VERSION)

# Load in all the models for the admin UI.
if not admin.site._registry:
    admin.autodiscover()


# URLs global to all modes
urlpatterns = patterns('',
    (r'^admin/', include('reviewboard.admin.urls')),
)

# Add static media if running in DEBUG mode
if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
        (r'^media/(?P<path>.*)$', 'serve', {
            'show_indexes': True,
            'document_root': os.path.join(settings.HTDOCS_ROOT, "media"),
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
    (r'^api/json/', include('reviewboard.webapi.urls')),
    (r'^r/', include('reviewboard.reviews.urls')),
    (r'^reports/', include('reviewboard.reports.urls')),
)


# reviewboard.reviews.views
urlpatterns += patterns('reviewboard.reviews.views',
    # Review request browsing
    url(r'^dashboard/$', 'dashboard', name="dashboard"),

    # Users
    url(r'^users/$', 'submitter_list', name="all-users"),
    url(r'^users/(?P<username>[A-Za-z0-9_\-\.]+)/$', 'submitter',
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
    (r'^iphone/', include('reviewboard.iphone.urls')),
)
