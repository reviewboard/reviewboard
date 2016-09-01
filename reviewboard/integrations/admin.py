"""Administration UI support for integration configurations."""

from __future__ import unicode_literals

from django.contrib import admin

from reviewboard.integrations.models import IntegrationConfig


class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ('integration_id', 'name', 'enabled', 'last_updated')


admin.site.register(IntegrationConfig, IntegrationConfigAdmin)
