"""Administration UI support for integration configurations."""

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.integrations.models import IntegrationConfig


class IntegrationConfigAdmin(ModelAdmin):
    list_display = ('integration_id', 'name', 'enabled', 'last_updated')
    raw_id_fields = ('local_site',)


admin_site.register(IntegrationConfig, IntegrationConfigAdmin)
