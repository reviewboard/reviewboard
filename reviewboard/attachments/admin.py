"""Admin definitions for the FileAttachment model."""

from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.attachments.models import FileAttachment


class FileAttachmentAdmin(ModelAdmin):
    """Admin definitions for the FileAttachment model."""

    list_display = ('filename', 'caption', 'mimetype', 'review_request_id',
                    'download')
    list_display_links = ('filename', 'caption')
    search_fields = ('caption', 'mimetype')
    raw_id_fields = ('added_in_filediff', 'local_site', 'user')

    def filename(
        self,
        obj: FileAttachment,
    ) -> str:
        """Return the name of the file.

        Args:
            obj (reviewboard.attachments.models.FileAttachment):
                The file attachment.

        Returns:
            str:
            The name of the file.
        """
        if obj.filename:
            return obj.filename[:80]
        else:
            return '(unnamed)'

    @admin.display(description=_('Review Request ID'))
    def review_request_id(
        self,
        obj: FileAttachment,
    ) -> int:
        """Return the review request ID for this file attachment.

        Args:
            obj (reviewboard.attachments.models.FileAttachment):
                The file attachment.

        Returns:
            int:
            The ID of the linked review request.
        """
        return obj.get_review_request().id

    def download(
        self,
        obj: FileAttachment,
    ) -> str:
        """Return a link to download the file.

        Args:
            obj (reviewboard.attachments.models.FileAttachment):
                The file attachment.

        Returns:
            str:
            A link to download the file
        """
        return format_html(
            '<a href="{}"><span class="rb-icon rb-icon-download"></span></a>',
            obj.file)


admin_site.register(FileAttachment, FileAttachmentAdmin)
