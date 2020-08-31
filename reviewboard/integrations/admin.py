"""Administration UI support for integration configurations."""

from __future__ import unicode_literals

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.integrations.models import IntegrationConfig


class IntegrationConfigAdmin(ModelAdmin):
    list_display = ('integration_id', 'name', 'enabled', 'last_updated')


admin_site.register(IntegrationConfig, IntegrationConfigAdmin)
