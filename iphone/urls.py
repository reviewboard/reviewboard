from django.conf import settings
from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template',
     {'template': 'iphone/base.html'}),

    # Accounts
    (r'^account/login/$', 'djblets.auth.views.login',
     {'next_page': '/iphone/',
      'template_name': 'iphone/login.html',
      'extra_context': {'BUILTIN_AUTH': settings.BUILTIN_AUTH}}),
    (r'^account/logout/$', 'django.contrib.auth.views.logout',
     {'next_page': '/iphone/'}),
    (r'^account/preferences/$', 'reviewboard.accounts.views.user_preferences',
     {'template_name': 'iphone/user_prefs.html'}),
)

urlpatterns += patterns('reviewboard.reviews.views',
    # Dashboard
    (r'^dashboard/$', 'dashboard',
     {'template_name': 'iphone/dashboard.html'}),
    (r'^dashboard/list/$', 'dashboard',
     {'template_name': 'iphone/dashboard_list.html'}),

    # Users
    (r'^users/$', 'submitter_list',
     {'template_name': 'iphone/submitter_list.html'}),
    (r'^users/(?P<username>[A-Za-z0-9_-]+)/$', 'submitter',
     {'template_name': 'iphone/review_request_list.html'}),

    # Groups
    (r'^groups/$', 'group_list',
     {'template_name': 'iphone/group_list.html'}),
    (r'^groups/(?P<name>[A-Za-z0-9_-]+)/$', 'group',
     {'template_name': 'iphone/review_request_list.html'}),

    # Review Requests
    (r'^r/$', 'all_review_requests',
     {'template_name': 'iphone/review_request_list.html'}),

    (r'^r/(?P<review_request_id>[0-9]+)/$', 'review_detail',
     {'template_name': 'iphone/review_request_detail.html'}),

    # Diffs
    (r'^r/(?P<review_request_id>[0-9]+)/diff/$', 'diff',
     {'template_name': 'iphone/diff_files.html'}),

    (r'^r/(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/(?P<filediff_id>[0-9]+)/$',
     'diff_fragment',
     {'collapseall': True,
      'template_name': 'iphone/diff.html'}),
)
