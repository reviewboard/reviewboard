from django.contrib import admin

from reviewboard.diffviewer.models import FileDiff, DiffSet, DiffSetHistory


class FileDiffAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('diffset', 'status', 'binary',
                       ('source_file', 'source_revision'),
                       ('dest_file', 'dest_detail'),
                       'diff', 'parent_diff')
        }),
    )
    list_display = ('source_file', 'source_revision',
                    'dest_file', 'dest_detail')
    raw_id_fields = ('diffset',)
    readonly_fields = ('diff', 'parent_diff')


class FileDiffInline(admin.StackedInline):
    model = FileDiff
    extra = 0


class DiffSetAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'revision', 'timestamp')
    raw_id_fields = ('history',)
    inlines = (FileDiffInline,)
    ordering = ('-timestamp',)


class DiffSetInline(admin.StackedInline):
    model = DiffSet
    extra = 0


class DiffSetHistoryAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'timestamp')
    inlines = (DiffSetInline,)
    ordering = ('-timestamp',)


admin.site.register(FileDiff, FileDiffAdmin)
admin.site.register(DiffSet, DiffSetAdmin)
admin.site.register(DiffSetHistory, DiffSetHistoryAdmin)
