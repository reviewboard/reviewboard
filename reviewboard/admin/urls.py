from django.conf.urls.defaults import include, patterns, url
from django.contrib import admin

from reviewboard.admin import forms


NEWS_FEED = "http://www.review-board.org/news/feed/"

urlpatterns = patterns('reviewboard.admin.views',
    (r'^$', 'dashboard'),
    (r'^cache/$', 'cache_stats'),

    # Settings
    url(r'^settings/general/$', 'site_settings',
        {'form_class': forms.GeneralSettingsForm,
         'template_name': 'admin/general_settings.html'},
        name="settings-general"),
    url(r'^settings/email/$', 'site_settings',
        {'form_class': forms.EMailSettingsForm,
         'template_name': 'admin/settings.html'},
        name="settings-email"),
    url(r'^settings/diffs/$', 'site_settings',
        {'form_class': forms.DiffSettingsForm,
         'template_name': 'admin/settings.html'},
        name="settings-diffs"),
    url(r'^settings/logging/$', 'site_settings',
        {'form_class': forms.LoggingSettingsForm,
         'template_name': 'admin/settings.html'},
        name="settings-logging"),
)

urlpatterns += patterns('',
    (r'^log/', include('djblets.log.urls')),

    ('^db/(.*)', admin.site.root),
    ('^feed/news/$', 'djblets.feedview.views.view_feed',
     {'template_name': 'admin/feed.html',
      'url': NEWS_FEED}),
    (r'^feed/news/rss/$', 'django.views.generic.simple.redirect_to',
     {'url': NEWS_FEED}),

    url(r'^settings/$', 'django.views.generic.simple.redirect_to',
        {'url': 'general/'},
        name="site-settings"),
)
