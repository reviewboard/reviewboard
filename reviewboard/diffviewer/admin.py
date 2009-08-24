from django.contrib import admin

from reviewboard.diffviewer.models import FileDiff, DiffSet, DiffSetHistory


class FileDiffAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('diffset', ('source_file', 'source_revision'),
                       ('dest_file', 'dest_detail'),
                       'binary', 'diff', 'parent_diff')
        }),
    )
    list_display = ('source_file', 'source_revision',
                    'dest_file', 'dest_detail')
    raw_id_fields = ('diffset',)


class DiffSetAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'revision', 'timestamp')
    raw_id_fields = ('history',)


admin.site.register(FileDiff, FileDiffAdmin)
admin.site.register(DiffSet, DiffSetAdmin)
admin.site.register(DiffSetHistory)
