from __future__ import unicode_literals

from django.contrib import admin

from reviewboard.hostingsvcs.models import HostingServiceAccount


class HostingServiceAccountAdmin(admin.ModelAdmin):
    list_display = ('username', 'service_name', 'visible', 'local_site')
    raw_id_fields = ('local_site',)


admin.site.register(HostingServiceAccount, HostingServiceAccountAdmin)
