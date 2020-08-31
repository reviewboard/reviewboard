from __future__ import unicode_literals

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import DiffLexer

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.diffviewer.models import (DiffCommit, DiffSet, DiffSetHistory,
                                           FileDiff)


class _FileDiffCommon(object):
    """Common attributes for FileDiffAdmin and FileDiffInline."""

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
    raw_id_fields = (
        'commit',
        'diff_hash',
        'diffset',
        'legacy_diff_hash',
        'legacy_parent_diff_hash',
        'parent_diff_hash',
    )
    readonly_fields = ('diff', 'parent_diff')

    def diff(self, filediff):
        return self._style_diff(filediff.diff)
    diff.short_description = _('Diff')

    def parent_diff(self, filediff):
        return self._style_diff(filediff.parent_diff)
    parent_diff.short_description = _('Parent diff')

    def _style_diff(self, diff):
        """Return a syntax-highlighted version of the diff.

        Args:
            diff (bytes):
                The raw diff content.

        Returns:
            django.utils.safestring.SafeText:
            The syntax-highlighted HTML.
        """
        # NOTE: Django wraps the contents in a <p>, but browsers will
        #       be sad about that, because it contains a <pre>. Chrome,
        #       for instance, will move it out into its own node. Be
        #       consistent and just make that happen for them.
        return format_html(
            '</p>{0}<p>',
            mark_safe(highlight(diff, DiffLexer(), HtmlFormatter())))


class FileDiffAdmin(_FileDiffCommon, ModelAdmin):
    """Administration UI information for FileDiff."""

    list_display = ('source_file', 'source_revision',
                    'dest_file', 'dest_detail')


class FileDiffInline(_FileDiffCommon, admin.StackedInline):
    """Inline relation information for FileDiff."""

    model = FileDiff
    extra = 0


class _DiffCommitCommon(object):
    """Common attributes for DiffCommitAdmin and DiffCommitInline."""

    raw_id_fields = ('diffset',)


class DiffCommitAdmin(_DiffCommitCommon, ModelAdmin):
    """Administration UI information for DiffCommit."""

    list_display = ('__str__',)
    inlines = (FileDiffInline,)


class DiffCommitInline(_DiffCommitCommon, admin.StackedInline):
    """Inline relation information for DiffCommit."""

    model = DiffCommit
    extra = 0
    inlines = (FileDiffInline,)


class _DiffSetCommon(object):
    """Common attributes for DiffSetAdmin and DiffSetInline."""

    raw_id_fields = ('history',)
    ordering = ('-timestamp',)


class DiffSetAdmin(_DiffSetCommon, ModelAdmin):
    """Administration UI information for DiffSet."""

    list_display = ('__str__', 'revision', 'timestamp')
    inlines = (DiffCommitInline, FileDiffInline)


class DiffSetInline(_DiffSetCommon, admin.StackedInline):
    """Inline relation information for DiffSet."""

    model = DiffSet
    extra = 0


class DiffSetHistoryAdmin(ModelAdmin):
    list_display = ('__str__', 'timestamp')
    inlines = (DiffSetInline,)
    ordering = ('-timestamp',)


admin_site.register(DiffCommit, DiffCommitAdmin)
admin_site.register(DiffSet, DiffSetAdmin)
admin_site.register(DiffSetHistory, DiffSetHistoryAdmin)
admin_site.register(FileDiff, FileDiffAdmin)
