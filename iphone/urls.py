from django.conf import settings
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template',
     {'template': 'iphone/base.html'}),

    # Accounts
    url(r'^account/login/$', 'djblets.auth.views.login',
        {'next_page': settings.SITE_ROOT + '/iphone/',
         'template_name': 'iphone/login.html',
         'extra_context': {'BUILTIN_AUTH': settings.BUILTIN_AUTH}},
        name="iphone-login"),
    url(r'^account/logout/$', 'django.contrib.auth.views.logout',
        {'next_page': settings.SITE_ROOT + 'iphone/'},
        name="iphone-logout"),
    url(r'^account/preferences/$',
        'reviewboard.accounts.views.user_preferences',
        {'template_name': 'iphone/user_prefs.html'},
        name="iphone-user-preferences"),
)

urlpatterns += patterns('reviewboard.reviews.views',
    # Dashboard
    url(r'^dashboard/$', 'dashboard',
        {'template_name': 'iphone/dashboard.html'},
        name="iphone-dashboard"),
    url(r'^dashboard/list/$', 'dashboard',
        {'template_name': 'iphone/dashboard_list.html'},
        name="iphone-dashboard-list"),

    # Users
    url(r'^users/$', 'submitter_list',
        {'template_name': 'iphone/submitter_list.html'},
        name="iphone-users"),
    url(r'^users/(?P<username>[A-Za-z0-9_-]+)/$', 'submitter',
        {'template_name': 'iphone/review_request_list.html'},
        name="iphone-user"),

    # Groups
    url(r'^groups/$', 'group_list',
        {'template_name': 'iphone/group_list.html'},
        name="iphone-groups"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/$', 'group',
        {'template_name': 'iphone/review_request_list.html'},
        name="iphone-group"),

    # Review Requests
    url(r'^r/$', 'all_review_requests',
        {'template_name': 'iphone/review_request_list.html'},
        name="iphone-all-review-requests"),

    url(r'^r/(?P<review_request_id>[0-9]+)/$', 'review_detail',
        {'template_name': 'iphone/review_request_detail.html'},
        name="iphone-review-request"),

    # Diffs
    url(r'^r/(?P<review_request_id>[0-9]+)/diff/$', 'diff',
        {'template_name': 'iphone/diff_files.html'},
        name="iphone-diff"),

    url(r'^r/(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/(?P<filediff_id>[0-9]+)/$',
        'diff_fragment',
        {'collapseall': True,
         'template_name': 'iphone/diff.html'},
        name="iphone-diff-fragment"),
)
