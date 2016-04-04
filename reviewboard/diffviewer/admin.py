from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import DiffLexer

from reviewboard.diffviewer.models import FileDiff, DiffSet, DiffSetHistory


class FileDiffAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('diffset', 'status', 'binary',
                       ('source_file', 'source_revision'),
                       ('dest_file', 'dest_detail'),
                       'diff', 'parent_diff')
        }),
        (_('Internal State'), {
            'description': _('<p>This is advanced state that should not be '
                             'modified unless something is wrong.</p>'),
            'fields': ('extra_data',),
            'classes': ['collapse'],
        }),
    )
    list_display = ('source_file', 'source_revision',
                    'dest_file', 'dest_detail')
    raw_id_fields = ('diffset', 'diff_hash', 'parent_diff_hash')
    readonly_fields = ('diff', 'parent_diff')

    def diff(self, filediff):
        return self._style_diff(filediff.diff)
    diff.label = _('Diff')
    diff.allow_tags = True

    def parent_diff(self, filediff):
        return self._style_diff(filediff.parent_diff)
    parent_diff.label = _('Parent diff')
    parent_diff.allow_tags = True

    def _style_diff(self, diff):
        # NOTE: Django wraps the contents in a <p>, but browsers will
        #       be sad about that, because it contains a <pre>. Chrome,
        #       for instance, will move it out into its own node. Be
        #       consistent and just make that happen for them.
        return '</p>%s<p>' % highlight(diff, DiffLexer(), HtmlFormatter())


class FileDiffInline(admin.StackedInline):
    model = FileDiff
    extra = 0
    raw_id_fields = ('diff_hash', 'legacy_diff_hash', 'parent_diff_hash',
                     'legacy_parent_diff_hash')


class DiffSetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'revision', 'timestamp')
    raw_id_fields = ('history',)
    inlines = (FileDiffInline,)
    ordering = ('-timestamp',)


class DiffSetInline(admin.StackedInline):
    model = DiffSet
    extra = 0


class DiffSetHistoryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'timestamp')
    inlines = (DiffSetInline,)
    ordering = ('-timestamp',)


admin.site.register(FileDiff, FileDiffAdmin)
admin.site.register(DiffSet, DiffSetAdmin)
admin.site.register(DiffSetHistory, DiffSetHistoryAdmin)
