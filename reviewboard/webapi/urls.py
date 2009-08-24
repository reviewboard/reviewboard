from djblets.util.misc import never_cache_patterns

from reviewboard.reviews.models import ReviewRequest


urlpatterns = never_cache_patterns('djblets.webapi.auth',
    # Accounts
    (r'^accounts/login/$', 'account_login'),
    (r'^accounts/logout/$', 'account_logout'),
)


urlpatterns += never_cache_patterns('reviewboard.webapi.json',
    # Server information
    (r'^info/$', 'server_info'),

    # Repositories
    (r'^repositories/$', 'repository_list'),
    (r'^repositories/(?P<repository_id>[0-9]+)/info/$', 'repository_info'),

    # Users
    (r'^users/$', 'user_list'),

    # Groups
    (r'^groups/$', 'group_list'),
    (r'^groups/(?P<group_name>[A-Za-z0-9_-]+)/users/$', 'users_in_group'),

    # Review groups
    (r'^groups/(?P<group_name>[A-Za-z0-9_-]+)/star/$',
     'group_star'),
    (r'^groups/(?P<group_name>[A-Za-z0-9_-]+)/unstar/$',
     'group_unstar'),

    # Review request lists
    (r'^reviewrequests/all/$', 'review_request_list',
     {'func': ReviewRequest.objects.public}),
    (r'^reviewrequests/all/count/$', 'count_review_requests',
     {'func': ReviewRequest.objects.public}),

    (r'^reviewrequests/to/group/(?P<group_name>[A-Za-z0-9_-]+)/$',
     'review_request_list',
     {'func': ReviewRequest.objects.to_group}),
    (r'^reviewrequests/to/group/(?P<group_name>[A-Za-z0-9_-]+)/count/$',
     'count_review_requests',
     {'func': ReviewRequest.objects.to_group}),

    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/$',
     'review_request_list',
     {'func': ReviewRequest.objects.to_user}),
    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/count/$',
     'count_review_requests',
     {'func': ReviewRequest.objects.to_user}),

    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/directly/$',
     'review_request_list',
     {'func': ReviewRequest.objects.to_user_directly}),
    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/directly/count/$',
     'count_review_requests',
     {'func': ReviewRequest.objects.to_user_directly}),

    (r'^reviewrequests/from/user/(?P<username>[A-Za-z0-9_-]+)/$',
     'review_request_list',
     {'func': ReviewRequest.objects.from_user}),
    (r'^reviewrequests/from/user/(?P<username>[A-Za-z0-9_-]+)/count/$',
     'count_review_requests',
     {'func': ReviewRequest.objects.from_user}),

    # Review requests
    (r'^reviewrequests/new/$', 'new_review_request'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/$', 'review_request'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/last-update/$',
     'review_request_last_update'),

    (r'^reviewrequests/repository/(?P<repository_id>[0-9]+)/changenum/(?P<changenum>[0-9]+)/$',
     'review_request_by_changenum'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/star/$',
     'review_request_star'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/unstar/$',
     'review_request_unstar'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/close/(?P<type>discarded|submitted)/$',
     'review_request_close'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reopen/$',
     'review_request_reopen'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/update_changenum/(?P<changenum>[0-9]+)$',
     'review_request_update_changenum'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/delete/$',
     'review_request_delete'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/publish/$',
     'review_request_publish'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/update_from_changenum/$',
     'review_request_draft_update_from_changenum'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/$',
     'review_request_draft'),

    # draft/save is deprecated in favor of draft/publish
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/save/$',
     'review_request_draft_publish'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/publish/$',
     'review_request_draft_publish'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/discard/$',
     'review_request_draft_discard'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/set/(?P<field_name>[A-Za-z0-9_-]+)/$',
     'review_request_draft_set_field'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/set/$',
     'review_request_draft_set'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/updated/$',
     'review_request_updated'),

    # Reviews
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/save/$',
     'review_draft_save'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/publish/$',
     'review_draft_save',
     {'publish': True}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/delete/$',
     'review_draft_delete'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/comments/$',
     'review_draft_comments'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/$',
     'review_draft'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/$',
     'review_list'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/count/$',
     'count_review_list'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/$',
     'review'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/comments/$',
     'review_comments_list'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/comments/count/$',
     'count_review_comments'),

    # Replies
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/replies/draft/$',
     'review_reply_draft'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/replies/draft/save/$',
     'review_reply_draft_save'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/replies/draft/discard/$',
     'review_reply_draft_discard'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/replies/$',
     'review_replies_list'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/(?P<review_id>[0-9]+)/replies/count/$',
     'count_review_replies'),

    # Diffs
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/diff/new/$',
     'new_diff'),

    # Screenshots
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/screenshot/new/$',
     'new_screenshot'),

    # Diff comments
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/diff/(?P<diff_revision>[0-9]+)/file/(?P<filediff_id>[0-9]+)/line/(?P<line>[0-9]+)/comments/$',
     'diff_line_comments'),

    # Interdiff comments
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/diff/(?P<diff_revision>[0-9]+)-(?P<interdiff_revision>[0-9]+)/file/(?P<filediff_id>[0-9]+)-(?P<interfilediff_id>[0-9]+)/line/(?P<line>[0-9]+)/comments/$',
     'diff_line_comments'),

    # Screenshot comments
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/s/(?P<screenshot_id>[0-9]+)/comments/(?P<w>[0-9]+)x(?P<h>[0-9]+)\+(?P<x>[0-9]+)\+(?P<y>[0-9]+)/$',
     'screenshot_comments'),
)
