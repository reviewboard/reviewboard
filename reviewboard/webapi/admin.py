from __future__ import unicode_literals

from django.contrib import admin

from reviewboard.webapi.models import WebAPIToken


class WebAPITokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'local_site', 'time_added', 'last_updated')
    raw_id_fields = ('user',)


admin.site.register(WebAPIToken, WebAPITokenAdmin)
