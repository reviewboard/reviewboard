from __future__ import unicode_literals

from django.conf.urls import include, url

from reviewboard.datagrids import views


urlpatterns = [
    # All Review Requests
    url(r'^r/$',
        views.all_review_requests,
        name='all-review-requests'),

    # Dashboard
    url(r'^dashboard/$',
        views.dashboard,
        name='dashboard'),

    # Users
    url(r'^users/', include([
        url(r'^$',
            views.users_list,
            name='all-users'),
        url(r'^(?P<username>[\w.@+-]+)/$',
            views.submitter,
            name='user'),
        url(r'^(?P<username>[\w.@+-]+)/(?P<grid>[a-z-]+)/$',
            views.submitter,
            name='user-grid'),
    ])),

    # Groups
    url(r'^groups/', include([
        url(r'^$',
            views.group_list,
            name='all-groups'),
        url(r'^(?P<name>[\w-]+)/$',
            views.group,
            name='group'),
        url(r'^(?P<name>[\w-]+)/members/$',
            views.group_members,
            name='group-members'),
    ])),
]
