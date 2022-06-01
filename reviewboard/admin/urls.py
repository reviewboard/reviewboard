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

from django.urls import include, path
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
    path('', views.admin_dashboard_view, name='admin-dashboard'),

    path('cache/', views.cache_stats, name='admin-server-cache'),

    path('db/', admin_site.urls),

    path('integrations/', include('reviewboard.integrations.urls')),

    path('log/', include('djblets.log.urls')),

    path('security/', views.security, name='admin-security-checks'),

    path('settings/', include([
        path('', RedirectView.as_view(url='general/', permanent=True),
             name='site-settings'),

        path('general/',
             views.site_settings,
             kwargs={
                 'form_class': GeneralSettingsForm,
             },
             name='settings-general'),

        path('authentication/',
             views.site_settings,
             kwargs={
                 'form_class': AuthenticationSettingsForm,
             },
             name='settings-authentication'),

        path('avatars/',
             views.site_settings,
             kwargs={
                 'form_class': AvatarServicesForm,
             },
             name='settings-avatars'),

        path('email/',
             views.site_settings,
             kwargs={
                 'form_class': EMailSettingsForm,
             },
             name='settings-email'),

        path('diffs/',
             views.site_settings,
             kwargs={
                 'form_class': DiffSettingsForm,
             },
             name='settings-diffs'),

        path('logging/',
             views.site_settings,
             kwargs={
                 'form_class': LoggingSettingsForm,
             },
             name='settings-logging'),

        path('privacy/',
             views.site_settings,
             kwargs={
                 'form_class': PrivacySettingsForm,
                 'template_name': 'admin/privacy_settings.html',
             },
             name='settings-privacy'),

        path('ssh/',
             views.ssh_settings,
             name='settings-ssh'),

        path('storage/',
             views.site_settings,
             kwargs={
                 'form_class': StorageSettingsForm,
             },
             name='settings-storage'),

        path('support/',
             views.site_settings,
             kwargs={
                 'form_class': SupportSettingsForm,
             },
             name='settings-support'),

        path('search/',
             views.site_settings,
             kwargs={
                 'form_class': SearchSettingsForm,
             },
             name='settings-search'),
    ])),

    path('widget-activity/', views.widget_activity),
]
