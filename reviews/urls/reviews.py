from django.conf.urls.defaults import patterns

urlpatterns = patterns('reviewboard.reviews.views',
    (r'^$', 'all_review_requests'),

    # Review request creation
    (r'^new/$', 'new_review_request'),

    # Review request detail
    (r'^(?P<review_request_id>[0-9]+)/$', 'review_detail',
     {'template_name': 'reviews/review_detail.html'}),

    # Review request diffs
    (r'^(?P<review_request_id>[0-9]+)/diff/$', 'diff'),
    (r'^(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/$', 'diff'),

    (r'^(?P<review_request_id>[0-9]+)/diff/raw/$', 'raw_diff'),
    (r'^(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/raw/$',
     'raw_diff'),

    (r'^(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/fragment/(?P<filediff_id>[0-9]+)/$',
     'diff_fragment'),
    (r'^(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/fragment/(?P<filediff_id>[0-9]+)/chunk/(?P<chunkindex>[0-9]+)/$',
     'diff_fragment'),

    # Review request interdiffs
    (r'^(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)-(?P<interdiff_revision>[0-9]+)/$',
     'diff'),

    # Review request modification
    (r'^(?P<review_request_id>[0-9]+)/publish/$', 'publish'),

    (r'^(?P<review_request_id>[0-9]+)/(?P<action>(discard|submitted|reopen))/$',
     'setstatus'),

    # Screenshots
    (r'^(?P<review_request_id>[0-9]+)/s/(?P<screenshot_id>[0-9]+)/$',
     'view_screenshot'),

    (r'^(?P<review_request_id>[0-9]+)/s/(?P<screenshot_id>[0-9]+)/delete/$',
     'delete_screenshot'),

    # E-mail previews
    (r'^(?P<review_request_id>[0-9]+)/preview-email/$',
     'preview_review_request_email'),
    (r'^(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/preview-email/$',
     'preview_review_email'),
    (r'^(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/replies/(?P<reply_id>[0-9]+)/preview-email/$',
     'preview_reply_email'),
)
