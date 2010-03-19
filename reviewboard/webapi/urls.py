from django.conf.urls.defaults import url, include, patterns
from django.views.generic.simple import redirect_to
from djblets.util.misc import never_cache_patterns

from reviewboard.reviews.models import ReviewRequest
from reviewboard.webapi.resources import diffSetResource, \
                                         repositoryResource, \
                                         reviewDraftResource, \
                                         reviewGroupResource, \
                                         reviewRequestResource, \
                                         reviewRequestDraftResource, \
                                         reviewResource, \
                                         serverInfoResource, \
                                         userResource

def redirect(request, url, *args, **kwargs):
    """Redirects to a new URL, tacking on any specified parameters."""

    extra_params = '&'.join(['%s=%s' % (key, value)
                            for key, value in request.GET.iteritems()])

    if extra_params:
        if '?' in url:
            url += '&' + extra_params
        else:
            url += '?' + extra_params

    return redirect_to(request, url, *args, **kwargs)


urlpatterns = never_cache_patterns('djblets.webapi.auth',
    # Accounts
    (r'^accounts/login/$', 'account_login'),
    (r'^accounts/logout/$', 'account_logout'),
)

# Top-level resources
urlpatterns += patterns('',
    url(r'^info/', include(serverInfoResource.get_url_patterns())),
    url(r'^groups/', include(reviewGroupResource.get_url_patterns())),
    url(r'^repositories/', include(repositoryResource.get_url_patterns())),
    url(r'^reviewrequests/', include(reviewRequestResource.get_url_patterns())),
    url(r'^users/', include(userResource.get_url_patterns())),
)

# Deprecated URLs
urlpatterns += never_cache_patterns('',
    # Review groups
    (r'^groups/(?P<group_name>[A-Za-z0-9_-]+)/star/$', reviewGroupResource,
     {'action': 'star',
      'method': 'PUT'}),
    (r'^groups/(?P<group_name>[A-Za-z0-9_-]+)/unstar/$', reviewGroupResource,
     {'action': 'unstar',
      'method': 'PUT'}),

    # Review request lists
    (r'^reviewrequests/all/$', redirect,
     {'url': '../',
      'permanent': True}),
    (r'^reviewrequests/all/count/$', redirect,
     {'url': '../../?counts-only=1',
      'permanent': True}),
    (r'^reviewrequests/to/group/(?P<group_name>[A-Za-z0-9_-]+)/$', redirect,
     {'url': '../../../?to-groups=%(group_name)s',
      'permanent': True}),
    (r'^reviewrequests/to/group/(?P<group_name>[A-Za-z0-9_-]+)/count/$',
     redirect,
     {'url': '../../../../?to-groups=%(group_name)s&counts-only=1',
      'permanent': True}),
    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/$', redirect,
     {'url': '../../../?to-users=%(username)s',
      'permanent': True}),
    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/count/$', redirect,
     {'url': '../../../../?to-users=%(username)s&counts-only=1',
      'permanent': True}),
    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/directly/$',
     redirect,
     {'url': '../../../../?to-users-directly=%(username)s',
      'permanent': True}),
    (r'^reviewrequests/to/user/(?P<username>[A-Za-z0-9_-]+)/directly/count/$',
     redirect,
     {'url': '../../../../../?to-users-directly=%(username)s&counts-only=1',
      'permanent': True}),
    (r'^reviewrequests/from/user/(?P<username>[A-Za-z0-9_-]+)/$', redirect,
     {'url': '../../../?from-user=%(username)s',
      'permanent': True}),
    (r'^reviewrequests/from/user/(?P<username>[A-Za-z0-9_-]+)/count/$',
     redirect,
     {'url': '../../../../?from-user=%(username)s&counts-only=1',
      'permanent': True}),

    (r'^reviewrequests/repository/(?P<repository_id>[0-9]+)/changenum/(?P<changenum>[0-9]+)/$',
     redirect,
     {'url': '../../../../?repository=%(repository_id)s&changenum=%(changenum)s&_first-result-only=1',
      'permanent': True}),

    # Review request creation
    (r'^reviewrequests/new/$', reviewRequestResource),

    # Review request actions
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/star/$',
     reviewRequestResource,
     {'action': 'star',
      'method': 'PUT'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/unstar/$',
     reviewRequestResource,
     {'action': 'unstar',
      'method': 'PUT'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/close/(?P<type>discarded|submitted)/$',
     reviewRequestResource,
     {'action': 'close',
      'method': 'PUT'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reopen/$',
     reviewRequestResource,
     {'action': 'reopen',
      'method': 'PUT'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/delete/$',
     reviewRequestResource,
     {'method': 'DELETE'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/publish/$',
     reviewRequestResource,
     {'action': 'publish',
      'method': 'PUT'}),

    # Review request draft actions
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/set/$',
     reviewRequestDraftResource,
     {'method': 'PUT',
      'action': 'deprecated_set'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/set/(?P<field_name>[A-Za-z0-9_-]+)/$',
     reviewRequestDraftResource,
     {'method': 'PUT',
      'action': 'deprecated_set_field'}),
    # draft/save is deprecated in favor of draft/publish. So, it's
    # double-deprecated.
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/(save|publish)/$',
     reviewRequestDraftResource,
     {'method': 'PUT',
      'action': 'publish'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/draft/discard/$',
     reviewRequestDraftResource,
     {'method': 'PUT',
      'action': 'deprecated_discard'}),

    # Review lists
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/count/$',
     redirect,
     {'url': '../?counts-only=1&_count-field-alias=reviews',
      'permanent': True}),

    # Review draft actions
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/save/$',
     reviewDraftResource,
     {'method': 'PUT'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/publish/$',
     reviewDraftResource,
     {'method': 'PUT',
      'action': 'publish'}),
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/delete/$',
     reviewDraftResource,
     {'method': 'PUT',
      'action': 'deprecated_delete'}),
)

urlpatterns += never_cache_patterns('reviewboard.webapi.json',
    # Review requests
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/last-update/$',
     'review_request_last_update'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/update_changenum/(?P<changenum>[0-9]+)$',
     'review_request_update_changenum'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/update_from_changenum/$',
     'review_request_draft_update_from_changenum'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/updated/$',
     'review_request_updated'),

    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/reviews/draft/comments/$',
     'review_draft_comments'),

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
    (r'^reviewrequests/(?P<review_request_id>[0-9]+)/diff/$',
     diffSetResource),

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
