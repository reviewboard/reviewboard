from __future__ import unicode_literals

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.hostingsvcs.models import HostingServiceAccount


class HostingServiceAccountAdmin(ModelAdmin):
    list_display = ('username', 'service_name', 'visible', 'local_site')
    raw_id_fields = ('local_site',)


admin_site.register(HostingServiceAccount, HostingServiceAccountAdmin)
