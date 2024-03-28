"""Admin definitions for change descriptions."""

from __future__ import annotations

from django.contrib import admin
from django.template.defaultfilters import truncatechars
from django.utils.translation import gettext_lazy as _, gettext

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.changedescs.models import ChangeDescription


class ChangeDescriptionAdmin(ModelAdmin):
    """Admin definitions for the ChangeDescription model."""

    list_display = ('truncated_text', 'public', 'timestamp')
    list_filter = ('timestamp', 'public')
    readonly_fields = ('fields_changed',)

    @admin.display(description=_('Change Description Text'))
    def truncated_text(
        self,
        obj: ChangeDescription,
    ) -> str:
        """Return the text of the object, truncated to 60 characters.

        Args:
            obj (reviewboard.changedescs.models.ChangeDescription):
                The change description.

        Returns:
            str:
            The text to show for the object.
        """
        text = obj.text

        if text:
            return truncatechars(obj.text, 60)
        else:
            return gettext('[empty description text]')


admin_site.register(ChangeDescription, ChangeDescriptionAdmin)
