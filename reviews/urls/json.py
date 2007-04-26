from django.conf.urls.defaults import *
from reviewboard.reviews.db import *

urlpatterns = patterns('reviewboard.reviews.json',
    # Review request lists
    (r'^reviewrequests/all/$', 'review_request_list',
     {'func': get_all_review_requests}),
    (r'^reviewrequests/all/count/$', 'count_review_requests',
     {'func': get_all_review_requests}),

    (r'^reviewrequests/to/group/(?P<group_name>[A-Za-z0-9_-]+)/$',
     'review_request_list',
     {'func': get_review_requests_to_group}),
    (r'^reviewrequests/to/group/(?P<group_name>[A-Za-z0-9_-]+)/count/$',
     'count_review_requests',
     {'func': get_review_requests_to_group}),

    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/$',
     'review_request_list',
     {'func': get_review_requests_to_user}),
    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/count/$',
     'count_review_requests',
     {'func': get_review_requests_to_user}),

    (r'^reviewrequests/from/user/(?P<username>[A-Za-z0-9_-]+)/$',
     'review_request_list',
     {'func': get_review_requests_from_user}),
    (r'^reviewrequests/from/user/(?P<username>[A-Za-z0-9_-]+)/count/$',
     'count_review_requests',
     {'func': get_review_requests_from_user}),

    # Review requests
    (r'^reviewrequests/new/$', 'new_review_request'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/$', 'review_request'),

    (r'^reviewrequests/changenum/(?P<changenum>[0-9]+)/$',
     'review_request_by_changenum'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/save/$',
     'review_request_draft_save'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/discard/$',
     'review_request_draft_discard'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/set/(?P<field_name>[A-Za-z0-9_-]+)/$',
     'review_request_draft_set_field'),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/set/$',
     'review_request_draft_set'),

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

    # Comments
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/diff/(?P<diff_revision>[0-9]+)/file/(?P<filediff_id>[0-9]+)/line/(?P<line>[0-9]+)/comments/$',
     'diff_line_comments'),
)
