from django.conf import settings
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.simple.direct_to_template',
     {'template': 'iphone/base.html'}),

    # Accounts
    url(r'^account/login/$', 'djblets.auth.views.login',
        {'next_page': settings.SITE_ROOT + 'iphone/',
         'template_name': 'iphone/login.html'},
        name="login"),
    url(r'^account/logout/$', 'django.contrib.auth.views.logout',
        {'next_page': settings.SITE_ROOT + 'iphone/'},
        name="logout"),
    url(r'^account/preferences/$',
        'reviewboard.accounts.views.user_preferences',
        {'template_name': 'iphone/user_prefs.html'},
        name="user-preferences"),
)

urlpatterns += patterns('reviewboard.reviews.views',
    # Dashboard
    url(r'^dashboard/$', 'dashboard',
        {'template_name': 'iphone/dashboard.html'},
        name="dashboard"),
    url(r'^dashboard/list/$', 'dashboard',
        {'template_name': 'iphone/dashboard_list.html'},
        name="dashboard-list"),

    # Users
    url(r'^users/$', 'submitter_list',
        {'template_name': 'iphone/submitter_list.html'},
        name="users"),
    url(r'^users/(?P<username>[A-Za-z0-9_-]+)/$', 'submitter',
        {'template_name': 'iphone/review_request_list.html'},
        name="user"),

    # Groups
    url(r'^groups/$', 'group_list',
        {'template_name': 'iphone/group_list.html'},
        name="groups"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/$', 'group',
        {'template_name': 'iphone/review_request_list.html'},
        name="group"),

    # Review Requests
    url(r'^r/$', 'all_review_requests',
        {'template_name': 'iphone/review_request_list.html'},
        name="all-review-requests"),

    url(r'^r/(?P<review_request_id>[0-9]+)/$', 'review_detail',
        {'template_name': 'iphone/review_request_detail.html'},
        name="review-request"),

    # Diffs
    url(r'^r/(?P<review_request_id>[0-9]+)/diff/$', 'diff',
        {'template_name': 'iphone/diff_files.html'},
        name="diff"),

    url(r'^r/(?P<review_request_id>[0-9]+)/diff/(?P<revision>[0-9]+)/(?P<filediff_id>[0-9]+)/$',
        'diff_fragment',
        {'collapseall': True,
         'template_name': 'iphone/diff.html'},
        name="diff-fragment"),
)
