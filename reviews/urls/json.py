from django.conf.urls.defaults import *
from reviewboard.reviews.db import *

urlpatterns = patterns('reviewboard.reviews.json',
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
)
