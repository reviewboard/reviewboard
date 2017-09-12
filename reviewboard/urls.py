from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView
from djblets.util.views import cached_javascript_catalog

from reviewboard.accounts import views as accounts_views
from reviewboard.admin import views as admin_views
from reviewboard.attachments import views as attachments_views
from reviewboard.datagrids.urls import urlpatterns as datagrid_urlpatterns
from reviewboard.extensions.base import get_extension_manager
from reviewboard.hostingsvcs.urls import urlpatterns as hostingsvcs_urlpatterns
from reviewboard.reviews import views as reviews_views
from reviewboard.webapi.resources import resources


extension_manager = get_extension_manager()


handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'


# Useful collections of URL names that may be interesting to callers.
# This is especially useful for any apply_to lists in hooks.
diffviewer_url_names = [
    'view-diff',
    'view-interdiff',
    'view-diff-revision',
]

reviewable_url_names = diffviewer_url_names + [
    'file-attachment',
    'screenshot',
]

main_review_request_url_name = 'review-request-detail'

review_request_url_names = diffviewer_url_names + [
    main_review_request_url_name,
]


# Load in all the models for the admin UI.
if not admin.site._registry:
    admin.autodiscover()


# URLs global to all modes
urlpatterns = [
    url(r'^admin/extensions/',
        include('djblets.extensions.urls'),
        kwargs={
            'extension_manager': extension_manager,
        }),
    url(r'^admin/', include('reviewboard.admin.urls')),
    url(r'^jsi18n/',
        cached_javascript_catalog,
        kwargs={
            'packages': ('reviewboard', 'djblets'),
        },
        name='js-catalog'),
]


urlpatterns += extension_manager.get_url_patterns()


# Add static media if running in DEBUG mode on a non-production host.
if settings.DEBUG and not settings.PRODUCTION:
    urlpatterns += static(settings.STATIC_DIRECTORY,
                          view='pipeline.views.serve_static',
                          show_indexes=True)
    urlpatterns += static(settings.MEDIA_DIRECTORY,
                          document_root=settings.MEDIA_ROOT,
                          view='reviewboard.attachments.views.serve_safe',
                          show_indexes=True)

    urlpatterns += [
        url(r'^js-tests/$',
            TemplateView.as_view(template_name='js/tests.html'),
            name='js-tests'),
        url(r'^js-tests/extensions/$',
            TemplateView.as_view(template_name='js/extension_tests.html'),
            name='js-extensions-tests'),
    ]


localsite_urlpatterns = [
    url(r'^$', reviews_views.RootView.as_view(), name='root'),

    url(r'^api/', include(resources.root.get_url_patterns())),
    url(r'^r/', include('reviewboard.reviews.urls')),

    # Support
    url(r'^support/$',
        admin_views.support_redirect,
        name='support'),

    # Users
    url(r'^users/(?P<username>[\w.@+-]+)/', include([
        # User info box
        url(r'^infobox/$',
            accounts_views.UserInfoboxView.as_view(),
            name='user-infobox'),

        # User file attachments
        url(r'file-attachments/(?P<file_attachment_uuid>[a-zA-Z0-9-]+)/$',
            attachments_views.user_file_attachment,
            name='user-file-attachment'),
    ])),

    # Search
    url(r'^search/', include('reviewboard.search.urls')),
]


localsite_urlpatterns += datagrid_urlpatterns
localsite_urlpatterns += hostingsvcs_urlpatterns


# Main includes
urlpatterns += [
    url(r'^account/', include('reviewboard.accounts.urls')),
    url(r'^oauth2/', include('reviewboard.oauth.urls')),
    url(r'^s/(?P<local_site_name>[\w\.-]+)/',
        include(localsite_urlpatterns)),
]


urlpatterns += localsite_urlpatterns
