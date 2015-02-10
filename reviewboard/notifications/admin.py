from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.notifications.forms import WebHookTargetForm
from reviewboard.notifications.models import WebHookTarget


class WebHookTargetAdmin(admin.ModelAdmin):
    form = WebHookTargetForm

    list_display = ('url', 'enabled')
    filter_horizontal = ('repositories',)
    fieldsets = (
        (None, {
            'fields': (
                'enabled',
                'url',
                'events',
                'apply_to',
                'repositories',
            ),
        }),
        (_('Payload'), {
            'fields': (
                'encoding',
                'use_custom_content',
                'custom_content',
                'secret',
            ),
        }),
        (_('Advanced'), {
            'fields': (
                'local_site',
                'extra_data',
            ),
            'classes': ['collapse'],
        }),
    )


admin.site.register(WebHookTarget, WebHookTargetAdmin)
