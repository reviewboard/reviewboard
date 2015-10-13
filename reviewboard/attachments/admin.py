from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.models import FileAttachment


class FileAttachmentAdmin(admin.ModelAdmin):
    """Admin definitions for the FileAttachment model."""

    list_display = ('file', 'caption', 'mimetype',
                    'review_request_id')
    list_display_links = ('file', 'caption')
    search_fields = ('caption', 'mimetype')
    raw_id_fields = ('added_in_filediff',)

    def review_request_id(self, obj):
        """Return the review request ID for this file attachment."""
        return obj.review_request.get().id

    review_request_id.short_description = _('Review request ID')


admin.site.register(FileAttachment, FileAttachmentAdmin)
