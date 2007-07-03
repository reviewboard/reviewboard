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

    (r'^$', 'django.views.generic.simple.redirect_to',
     {'url': '/dashboard/'}),

    # Review request browsing
    (r'^dashboard/$', 'reviewboard.reviews.views.dashboard'),

    (r'^r/$', 'reviewboard.reviews.views.all_review_requests'),

    # Review request creation
    (r'^r/new/$', 'reviewboard.reviews.views.new_review_request'),

    # Review request detail
    (r'^r/(?P<object_id>[0-9]+)/$',
     'reviewboard.reviews.views.review_detail',
     {'template_name': 'reviews/review_detail.html'}),

    # Review request diffs
    (r'^r/(?P<review_request_id>[0-9]+)/diff/$',
     'reviewboard.reviews.views.diff'),
    (r'^r/(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/$',
     'reviewboard.reviews.views.diff'),

    (r'^r/(?P<review_request_id>[0-9]+)/diff/raw/$',
     'reviewboard.reviews.views.raw_diff'),
    (r'^r/(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/raw/$',
     'reviewboard.reviews.views.raw_diff'),

    (r'^r/(?P<object_id>[0-9]+)/diff/(?P<revision>[0-9]+)/fragment/(?P<filediff_id>[0-9]+)/$',
     'reviewboard.reviews.views.diff_fragment'),
    (r'^r/(?P<object_id>[0-9]+)/diff/(?P<revision>[0-9]+)/fragment/(?P<filediff_id>[0-9]+)/chunk/(?P<chunkindex>[0-9]+)/$',
     'reviewboard.reviews.views.diff_fragment'),

    # Review request interdiffs
    (r'^r/(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)-(?P<interdiff_revision>[0-9]+)/$',
     'reviewboard.reviews.views.diff'),


    # Review request modification
    (r'^r/[0-9]+/diff/upload/$',
     'reviewboard.diffviewer.views.upload',
      {'donepath': 'done/%s/'}),

    (r'^r/(?P<review_request_id>[0-9]+)/diff/upload/done/(?P<diffset_id>[0-9]+)/$',
     'reviewboard.reviews.views.upload_diff_done'),

    (r'^r/(?P<review_request_id>[0-9]+)/publish/$',
     'reviewboard.reviews.views.publish'),

    (r'^r/(?P<review_request_id>[0-9]+)/(?P<action>(discard|submitted|reopen))/$',
     'reviewboard.reviews.views.setstatus'),

    # Screenshots
    (r'^r/(?P<review_request_id>[0-9]+)/s/(?P<screenshot_id>[0-9]+)/$',
     'reviewboard.reviews.views.view_screenshot'),

    (r'^r/(?P<review_request_id>[0-9]+)/s/upload/$',
     'reviewboard.reviews.views.upload_screenshot'),

    (r'^r/(?P<review_request_id>[0-9]+)/s/(?P<screenshot_id>[0-9]+)/delete/$',
     'reviewboard.reviews.views.delete_screenshot'),

    # E-mail previews
    (r'^r/(?P<review_request_id>[0-9]+)/preview-email/$',
     'reviewboard.reviews.views.preview_review_request_email'),
    (r'^r/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/preview-email/$',
     'reviewboard.reviews.views.preview_review_email'),
    (r'^r/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/replies/(?P<reply_id>[0-9]+)/preview-email/$',
     'reviewboard.reviews.views.preview_reply_email'),

    # Users
    (r'^users/$', 'reviewboard.reviews.views.submitter_list'),
    (r'^users/(?P<username>[A-Za-z0-9_-]+)/$',
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
