"""Django model administration for OAuth2 applications."""

from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.oauth.forms import ApplicationForm
from reviewboard.oauth.models import Application


class ApplicationAdmin(admin.ModelAdmin):
    """The model admin for the OAuth application model.

    The default model admin provided by django-oauth-toolkit does not provide
    help text for the majority of the fields, so this admin uses a custom form
    which does provide the help text.
    """

    form = ApplicationForm
    raw_id_fields = ('local_site',)

    fieldsets = (
        (_('General Settings'), {
            'fields': ('name',
                       'user',
                       'redirect_uris'),
        }),

        (_('Client Settings'), {
            'fields': ('client_id',
                       'client_secret',
                       'client_type'),
        }),

        (_('Authorization Settings'), {
            'fields': ('authorization_grant_type',
                       'skip_authorization'),
        }),

        (_('Internal State'), {
            'description': _(
                '<p>This is advanced state that should not be modified unless '
                'something is wrong.</p>'
            ),
            'fields': ('local_site', 'extra_data'),
            'classes': ('collapse',),
        }),
    )


# Override the default provided ModelAdmin class from oauth2_provider.
admin.site.unregister(Application)
admin.site.register(Application, ApplicationAdmin)
