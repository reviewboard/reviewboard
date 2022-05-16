from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from djblets.util.views import cached_javascript_catalog
from pipeline import views as pipeline_views

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


# URLs global to all modes
urlpatterns = [
    path('admin/extensions/',
         include('djblets.extensions.urls'),
         kwargs={
             'extension_manager': extension_manager,
         }),
    path('admin/', include('reviewboard.admin.urls')),
    path('jsi18n/',
         cached_javascript_catalog,
         kwargs={
             'packages': ('reviewboard', 'djblets'),
         },
         name='js-catalog'),
    path('read-only/',
         TemplateView.as_view(template_name='read_only.html'),
         name='read-only'),
]


urlpatterns += extension_manager.get_url_patterns()


# Add static media if running in DEBUG mode on a non-production host.
if settings.DEBUG and not settings.PRODUCTION:
    urlpatterns += static(settings.STATIC_DIRECTORY,
                          view=pipeline_views.serve_static,
                          show_indexes=True)
    urlpatterns += static(settings.MEDIA_DIRECTORY,
                          document_root=settings.MEDIA_ROOT,
                          view=attachments_views.serve_safe,
                          show_indexes=True)

    urlpatterns += [
        path('js-tests/',
             TemplateView.as_view(template_name='js/tests.html'),
             name='js-tests'),
        path('js-tests/extensions/',
             TemplateView.as_view(template_name='js/extension_tests.html'),
             name='js-extensions-tests'),
    ]


localsite_urlpatterns = [
    path('', reviews_views.RootView.as_view(), name='root'),

    path('api/', include(resources.root.get_url_patterns())),
    path('r/', include('reviewboard.reviews.urls')),

    # Support
    path('support/',
         admin_views.support_redirect,
         name='support'),

    # Users
    re_path(r'^users/(?P<username>[\w.@+-]+)/', include([
        # User info box
        path('infobox/',
             accounts_views.UserInfoboxView.as_view(),
             name='user-infobox'),

        # User file attachments
        path(r'file-attachments/<uuid:file_attachment_uuid>/',
            attachments_views.user_file_attachment,
            name='user-file-attachment'),
    ])),

    # Search
    path('search/', include('reviewboard.search.urls')),
]


localsite_urlpatterns += datagrid_urlpatterns
localsite_urlpatterns += hostingsvcs_urlpatterns


# Main includes
urlpatterns += [
    path('account/', include('reviewboard.accounts.urls')),
    path('oauth2/', include('reviewboard.oauth.urls')),
    re_path(r'^s/(?P<local_site_name>[\w\.-]+)/',
            include(localsite_urlpatterns)),
]


urlpatterns += localsite_urlpatterns
