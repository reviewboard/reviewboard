from django.contrib import admin

from reviewboard.changedescs.models import ChangeDescription


class ChangeDescriptionAdmin(admin.ModelAdmin):
    list_display = ('truncate_text', 'public', 'timestamp')
    list_filter = ('timestamp', 'public')


admin.site.register(ChangeDescription, ChangeDescriptionAdmin)
