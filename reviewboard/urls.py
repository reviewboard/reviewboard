from __future__ import unicode_literals

import os

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import RedirectView, TemplateView

from reviewboard.extensions.base import get_extension_manager
from reviewboard.webapi.resources import resources


extension_manager = get_extension_manager()


handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'


# Useful collections of URL names that may be interesting to callers.
# This is especially useful for any apply_to lists in hooks.
diffviewer_url_names = [
    'view_diff',
    'view_interdiff',
    'view_diff_revision',
]

reviewable_url_names = diffviewer_url_names + [
    'file_attachment',
    'screenshot',
]

review_request_url_names = diffviewer_url_names + [
    'review-request-detail',
]


# Load in all the models for the admin UI.
if not admin.site._registry:
    admin.autodiscover()


# URLs global to all modes
urlpatterns = patterns(
    '',

    (r'^admin/extensions/', include('djblets.extensions.urls'),
     {'extension_manager': extension_manager}),
    (r'^admin/', include('reviewboard.admin.urls')),

    url(r'^jsi18n/', 'djblets.util.views.cached_javascript_catalog',
        {'packages': ('reviewboard', 'djblets')},
        name='js-catalog')
)


urlpatterns += extension_manager.get_url_patterns()

# Add static media if running in DEBUG mode on a non-production host.
if settings.DEBUG and not settings.PRODUCTION:
    urlpatterns += static(settings.STATIC_DIRECTORY,
                          view='django.contrib.staticfiles.views.serve',
                          show_indexes=True)
    urlpatterns += static(settings.MEDIA_DIRECTORY,
                          view='django.contrib.staticfiles.views.serve',
                          show_indexes=True)

    urlpatterns += patterns(
        '',

        url(r'^js-tests/$',
            TemplateView.as_view(template_name='js/tests.html')),
    )

localsite_urlpatterns = patterns(
    '',

    url(r'^$', 'reviewboard.reviews.views.root', name="root"),

    (r'^api/', include(resources.root.get_url_patterns())),
    (r'^r/', include('reviewboard.reviews.urls')),

    # Dashboard
    url(r'^dashboard/$',
        'reviewboard.reviews.views.dashboard', name="dashboard"),

    # Support
    url(r'^support/$',
        'reviewboard.admin.views.support_redirect', name="support"),

    # Users
    url(r'^users/$',
        'reviewboard.reviews.views.submitter_list', name="all-users"),
    url(r"^users/(?P<username>[A-Za-z0-9@_\-\.'\+]+)/$",
        'reviewboard.reviews.views.submitter', name="user"),
    url(r"^users/(?P<username>[A-Za-z0-9@_\-\.'\+]+)/infobox/$",
        'reviewboard.reviews.views.user_infobox', name="user-infobox"),

    # Groups
    url(r'^groups/$',
        'reviewboard.reviews.views.group_list', name="all-groups"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/$',
        'reviewboard.reviews.views.group', name="group"),
    url(r'^groups/(?P<name>[A-Za-z0-9_-]+)/members/$',
        'reviewboard.reviews.views.group_members', name="group_members"),
)


# Main includes
urlpatterns += patterns(
    '',

    (r'^account/', include('reviewboard.accounts.urls')),

    (r'^s/(?P<local_site_name>[A-Za-z0-9\-_.]+)/',
     include(localsite_urlpatterns)),
)

urlpatterns += localsite_urlpatterns
