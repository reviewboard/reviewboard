from __future__ import unicode_literals

from django.contrib import admin

from reviewboard.notifications.models import WebHookTarget


class WebHookTargetAdmin(admin.ModelAdmin):
    list_display = ('url', 'enabled')


admin.site.register(WebHookTarget, WebHookTargetAdmin)
