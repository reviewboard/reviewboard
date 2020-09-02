from __future__ import unicode_literals

from django.template.defaultfilters import truncatechars
from django.utils.translation import ugettext_lazy as _

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.changedescs.models import ChangeDescription


class ChangeDescriptionAdmin(ModelAdmin):
    """Admin definitions for the ChangeDescription model."""

    list_display = ('truncated_text', 'public', 'timestamp')
    list_filter = ('timestamp', 'public')
    readonly_fields = ('fields_changed',)

    def truncated_text(self, obj):
        """Return the text of the object, truncated to 60 characters."""
        return truncatechars(obj.text, 60)
    truncated_text.short_description = _('Change Description Text')


admin_site.register(ChangeDescription, ChangeDescriptionAdmin)
