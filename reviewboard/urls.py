import os

from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView

from reviewboard.extensions.base import get_extension_manager
from reviewboard.webapi.resources import root_resource


extension_manager = get_extension_manager()


handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'


# Load in all the models for the admin UI.
if not admin.site._registry:
    admin.autodiscover()


# URLs global to all modes
urlpatterns = patterns('',
    (r'^admin/extensions/', include('djblets.extensions.urls'),
     {'extension_manager': extension_manager}),
    (r'^admin/', include('reviewboard.admin.urls')),
)

urlpatterns += extension_manager.get_url_patterns()

# Add static media if running in DEBUG mode
if settings.DEBUG or getattr(settings, 'RUNNING_TEST', False):
    # Django's handling of staticfiles is a bit of a mess. It has two
    # implementations of the entry points for serving static content.
    #
    # One (django.contrib.staticfiles.views.serve) will use the
    # STATICFILES_FINDERS to try to find the files.
    #
    # Another (django.views.static.serve) will just try the path given.
    #
    # Django expects we'll use staticfiles_urlpatterns (which uses the former)
    # and that things will Just Work, but this isn't the reality for us.
    # What happens is that it will try to look for Pipeline's processed and
    # outputted files in the source directories, which it will fail to find.
    #
    # Using just the other view fails in DEBUG mode because it expects to
    # find them in the static output directory (STATIC_ROOT), which won't
    # exist in a typical developer build.
    #
    # So, we use both, and try to determine based on whether this is a
    # production install and whether the static directory exists.
    staticfiles_kwargs = {}

    if not settings.PRODUCTION and not os.path.exists(settings.STATIC_ROOT):
        staticfiles_kwargs['view'] = 'django.contrib.staticfiles.views.serve'

    urlpatterns += static(settings.STATIC_DIRECTORY,
                          document_root=settings.STATIC_ROOT,
                          show_indexes=True,
                          **staticfiles_kwargs)
    urlpatterns += static(settings.MEDIA_DIRECTORY,
                          document_root=settings.MEDIA_ROOT,
                          show_indexes=True)

    urlpatterns += patterns('',
        url(r'^js-tests/$',
            TemplateView.as_view(template_name='js/tests.html')),
    )

localsite_urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.simple.redirect_to',
        {'url': 'dashboard/'},
        name="root"),

    (r'^api/', include(root_resource.get_url_patterns())),
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
    url(r'^users/(?P<username>[A-Za-z0-9@_\-\.]+)/$',
        'reviewboard.reviews.views.submitter', name="user"),
    url(r'^users/(?P<username>[A-Za-z0-9@_\-\.]+)/infobox/$',
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
urlpatterns += patterns('',
    (r'^account/', include('reviewboard.accounts.urls')),

    (r'^s/(?P<local_site_name>[A-Za-z0-9\-_.]+)/',
     include(localsite_urlpatterns)),
)

urlpatterns += localsite_urlpatterns


# django.contrib
urlpatterns += patterns('django.contrib',
    url(r'^account/logout/$', 'auth.views.logout',
        {'next_page': settings.LOGIN_URL}, name="logout")
)
