from django.urls import include, path, re_path

from reviewboard.datagrids import views


urlpatterns = [
    # All Review Requests
    path('r/',
         views.all_review_requests,
         name='all-review-requests'),

    # Dashboard
    path('dashboard/',
         views.dashboard,
         name='dashboard'),

    # Users
    path('users/', include([
        path('',
             views.users_list,
             name='all-users'),
        re_path(r'^(?P<username>[\w.@+-]+)/$',
                views.submitter,
                name='user'),
        re_path(r'^(?P<username>[\w.@+-]+)/(?P<grid>[a-z-]+)/$',
                views.submitter,
                name='user-grid'),
    ])),

    # Groups
    path('groups/', include([
        path('',
             views.group_list,
             name='all-groups'),
        path('<str:name>/',
             views.group,
             name='group'),
        path('<str:name>/members/',
             views.group_members,
             name='group-members'),
    ])),
]
