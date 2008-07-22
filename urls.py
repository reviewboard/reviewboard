import os.path

from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

from reviewboard.admin.checks import check_updates_required
from reviewboard.reviews.feeds import RssReviewsFeed, AtomReviewsFeed, \
                                      RssSubmitterReviewsFeed, \
                                      AtomSubmitterReviewsFeed, \
                                      RssGroupReviewsFeed, \
                                      AtomGroupReviewsFeed


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


# Check that we're actually able to run. There may have been changes that
# require the user to manually update things on the server and restart.
if check_updates_required():
    # There's updates required. Disable the main URLs for now, since it might
    # be useless.

    urlpatterns += patterns('',
        (r'^.*', 'reviewboard.admin.views.manual_updates_required'),
    )
else:
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

        # Authentication and accounts
        url(r'^account/login/$', 'djblets.auth.views.login',
            {'next_page': settings.SITE_ROOT + 'dashboard/',
             'extra_context': {'BUILTIN_AUTH': settings.BUILTIN_AUTH}},
            name="login"),
        url(r'^account/preferences/$',
            'reviewboard.accounts.views.user_preferences',
            name="user-preferences"),

        # This must be last.
        (r'^iphone/', include('reviewboard.iphone.urls')),
    )

    if settings.BUILTIN_AUTH:
        urlpatterns += patterns('',
            url(r'^account/register/$', 'djblets.auth.views.register',
                {'next_page': settings.SITE_ROOT + 'dashboard/'},
                name="register"),
        )
    else:
        urlpatterns += patterns('',
            (r'^account/register/$',
             'django.views.generic.simple.redirect_to',
             {'url': settings.SITE_ROOT + 'account/login/'}))
