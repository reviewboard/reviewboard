from django.contrib import admin

from reviewboard.changedescs.models import ChangeDescription


class ChangeDescriptionAdmin(admin.ModelAdmin):
    list_display = ('truncate_text', 'public', 'timestamp')
    list_filter = ('timestamp', 'public')
    readonly_fields = ('fields_changed',)


admin.site.register(ChangeDescription, ChangeDescriptionAdmin)
