from __future__ import unicode_literals

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.webapi.models import WebAPIToken


class WebAPITokenAdmin(ModelAdmin):
    list_display = ('user', 'local_site', 'time_added', 'last_updated')
    raw_id_fields = ('user',)


admin_site.register(WebAPIToken, WebAPITokenAdmin)
