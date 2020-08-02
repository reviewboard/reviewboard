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
from django.views.generic import RedirectView

from reviewboard.admin import admin_site, views
from reviewboard.admin.forms.auth_settings import AuthenticationSettingsForm
from reviewboard.admin.forms.avatar_settings import AvatarServicesForm
from reviewboard.admin.forms.diff_settings import DiffSettingsForm
from reviewboard.admin.forms.email_settings import EMailSettingsForm
from reviewboard.admin.forms.general_settings import GeneralSettingsForm
from reviewboard.admin.forms.logging_settings import LoggingSettingsForm
from reviewboard.admin.forms.privacy_settings import PrivacySettingsForm
from reviewboard.admin.forms.search_settings import SearchSettingsForm
from reviewboard.admin.forms.storage_settings import StorageSettingsForm
from reviewboard.admin.forms.support_settings import SupportSettingsForm


urlpatterns = [
    url(r'^$', views.admin_dashboard_view, name='admin-dashboard'),

    url(r'^cache/$', views.cache_stats, name='admin-server-cache'),

    url(r'^db/', include(admin_site.urls)),

    url(r'^integrations/', include('reviewboard.integrations.urls')),

    url(r'^log/', include('djblets.log.urls')),

    url(r'^security/$', views.security, name='admin-security-checks'),

    url(r'^settings/', include([
        url(r'^$', RedirectView.as_view(url='general/', permanent=True),
            name='site-settings'),

        url(r'^general/$',
            views.site_settings,
            kwargs={
                'form_class': GeneralSettingsForm,
            },
            name='settings-general'),

        url(r'^authentication/$',
            views.site_settings,
            kwargs={
                'form_class': AuthenticationSettingsForm,
            },
            name='settings-authentication'),

        url(r'^avatars/$',
            views.site_settings,
            kwargs={
                'form_class': AvatarServicesForm,
            },
            name='settings-avatars'),

        url(r'^email/$',
            views.site_settings,
            kwargs={
                'form_class': EMailSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-email'),

        url(r'^diffs/$',
            views.site_settings,
            kwargs={
                'form_class': DiffSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-diffs'),

        url(r'^logging/$',
            views.site_settings,
            kwargs={
                'form_class': LoggingSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-logging'),

        url(r'^privacy/$',
            views.site_settings,
            kwargs={
                'form_class': PrivacySettingsForm,
                'template_name': 'admin/privacy_settings.html',
            },
            name='settings-privacy'),

        url(r'^ssh/$',
            views.ssh_settings,
            name='settings-ssh'),

        url(r'^storage/$',
            views.site_settings,
            kwargs={
                'form_class': StorageSettingsForm,
            },
            name='settings-storage'),

        url(r'^support/$',
            views.site_settings,
            kwargs={
                'form_class': SupportSettingsForm,
                'template_name': 'admin/settings.html',
            },
            name='settings-support'),

        url(r'^search/$',
            views.site_settings,
            kwargs={
                'form_class': SearchSettingsForm,
            },
            name='settings-search'),
    ])),

    url(r'^widget-activity/$', views.widget_activity),
]
