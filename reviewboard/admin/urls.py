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

from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView
from djblets.feedview.views import view_feed

from reviewboard.admin import forms, views


NEWS_FEED = 'https://www.reviewboard.org/news/feed/'

urlpatterns = [
    url(r'^$', views.dashboard),

    url(r'^cache/$', views.cache_stats, name='admin-server-cache'),

    url(r'^db/', include(admin.site.urls)),

    url(r'^integrations/', include('reviewboard.integrations.urls')),

    url(r'^feed/news/$',
        view_feed,
        kwargs={
            'template_name': 'admin/feed.html',
            'url': NEWS_FEED,
        }),

    url(r'^feed/news/rss/$',
        RedirectView.as_view(url=NEWS_FEED, permanent=True)),

    url(r'^log/', include('djblets.log.urls')),

    url(r'^security/$', views.security, name='admin-security-checks'),

    url(r'^settings/', include([
        url(r'^$', RedirectView.as_view(url='general/', permanent=True),
            name='site-settings'),

        url(r'^general/$',
            views.site_settings,
            kwargs={
                'form_class': forms.GeneralSettingsForm,
                'template_name': 'admin/general_settings.html',
            },
            name='settings-general'),

        url(r'^authentication/$',
            views.site_settings,
            kwargs={
                'form_class': forms.AuthenticationSettingsForm,
                'template_name': 'admin/authentication_settings.html',
            },
            name='settings-authentication'),

        url(r'^avatars/$',
            views.site_settings,
            kwargs={
                'form_class': forms.AvatarServicesForm,
                'template_name': 'admin/avatar_settings.html',
            },
            name='settings-avatars'),

        url(r'^email/$',
            views.site_settings,
            kwargs={
                'form_class': forms.EMailSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-email'),

        url(r'^diffs/$',
            views.site_settings,
            kwargs={
                'form_class': forms.DiffSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-diffs'),

        url(r'^logging/$',
            views.site_settings,
            kwargs={
                'form_class': forms.LoggingSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-logging'),

        url(r'^privacy/$',
            views.site_settings,
            kwargs={
                'form_class': forms.PrivacySettingsForm,
                'template_name': 'admin/privacy_settings.html',
            },
            name='settings-privacy'),

        url(r'^ssh/$',
            views.ssh_settings,
            name='settings-ssh'),

        url(r'^storage/$',
            views.site_settings,
            kwargs={
                'form_class': forms.StorageSettingsForm,
                'template_name': 'admin/storage_settings.html',
            },
            name='settings-storage'),

        url(r'^support/$',
            views.site_settings,
            kwargs={
                'form_class': forms.SupportSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-support'),

        url(r'^search/$',
            views.site_settings,
            kwargs={
                'form_class': forms.SearchSettingsForm,
                'template_name': 'admin/search_settings.html',
            },
            name='settings-search'),
    ])),

    url(r'^widget-activity/$', views.widget_activity),

    url(r'^widget-move/$', views.widget_move),

    url(r'^widget-select/$', views.widget_select),

    url(r'^widget-toggle/$', views.widget_toggle),
]
