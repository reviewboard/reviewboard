#
# reviewboard/admin/urls.py -- URLs for the admin app
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from django.conf.urls import include, patterns, url
from django.contrib import admin
from django.views.generic import RedirectView

from reviewboard.admin import forms


NEWS_FEED = "https://www.reviewboard.org/news/feed/"

settings_urlpatterns = patterns(
    'reviewboard.admin.views',

    url(r'^general/$', 'site_settings',
        {'form_class': forms.GeneralSettingsForm,
         'template_name': 'admin/general_settings.html'},
        name="settings-general"),
    url(r'^authentication/$', 'site_settings',
        {'form_class': forms.AuthenticationSettingsForm,
         'template_name': 'admin/authentication_settings.html'},
        name="settings-authentication"),
    url(r'^email/$', 'site_settings',
        {'form_class': forms.EMailSettingsForm,
         'template_name': 'admin/settings.html'},
        name="settings-email"),
    url(r'^diffs/$', 'site_settings',
        {'form_class': forms.DiffSettingsForm,
         'template_name': 'admin/settings.html'},
        name="settings-diffs"),
    url(r'^logging/$', 'site_settings',
        {'form_class': forms.LoggingSettingsForm,
         'template_name': 'admin/settings.html'},
        name="settings-logging"),
    url(r'^ssh/$', 'ssh_settings', name="settings-ssh"),
    url(r'^storage/$', 'site_settings',
        {'form_class': forms.StorageSettingsForm,
         'template_name': 'admin/storage_settings.html'},
        name="settings-storage"),
    url(r'^support/$', 'site_settings',
        {'form_class': forms.SupportSettingsForm,
         'template_name': 'admin/settings.html'},
        name="settings-support"),
)

urlpatterns = patterns(
    'reviewboard.admin.views',

    (r'^$', 'dashboard'),
    url(r'^cache/$', 'cache_stats', name='admin-server-cache'),
    (r'^settings/', include(settings_urlpatterns)),
    (r'^widget-toggle/', 'widget_toggle'),
    (r'^widget-move/', 'widget_move'),
    (r'^widget-activity/', 'widget_activity'),
    url(r'^security/$', 'security', name='admin-security-checks'),
)

urlpatterns += patterns(
    '',

    (r'^log/', include('djblets.log.urls')),

    ('^db/', include(admin.site.urls)),
    ('^feed/news/$', 'djblets.feedview.views.view_feed',
     {'template_name': 'admin/feed.html',
      'url': NEWS_FEED}),
    (r'^feed/news/rss/$', RedirectView.as_view(url=NEWS_FEED)),

    url(r'^settings/$', RedirectView.as_view(url='general/'),
        name="site-settings"),
)
