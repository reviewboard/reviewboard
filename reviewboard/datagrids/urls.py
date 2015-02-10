from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'reviewboard.datagrids.views',

    # All Review Requests
    url(r'^r/$', 'all_review_requests', name="all-review-requests"),

    # Dashboard
    url(r'^dashboard/$', 'dashboard', name='dashboard'),

    # Users
    url(r'^users/$', 'users_list', name='all-users'),
    url(r"^users/(?P<username>[A-Za-z0-9@_\-\.'\+]+)/$",
        'submitter', name='user'),
    url(r"^users/(?P<username>[A-Za-z0-9@_\-\.'\+]+)/(?P<grid>[a-z-]+)/$",
        'submitter', name='user-grid'),


    # Groups
    url(r'^groups/$', 'group_list', name='all-groups'),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/$', 'group', name='group'),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/members/$',
        'group_members', name='group-members'),
)
