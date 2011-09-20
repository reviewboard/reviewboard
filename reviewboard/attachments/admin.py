from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.models import FileAttachment


class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ('file', 'caption', 'mimetype',
                    'review_request_id')
    list_display_links = ('file', 'caption')
    search_fields = ('caption', 'mimetype')

    def review_request_id(self, obj):
        return obj.review_request.get().id
    review_request_id.short_description = _('Review request ID')


admin.site.register(FileAttachment, FileAttachmentAdmin)
