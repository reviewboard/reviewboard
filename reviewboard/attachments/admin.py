from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import FileAttachmentComment


class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ('file', 'caption', 'mimetype',
                    'review_request_id')
    list_display_links = ('file_attachment', 'caption')
    search_fields = ('caption', 'mimetype')

    def review_request_id(self, obj):
        return obj.review_request.get().id
    review_request_id.short_description = _('Review request ID')


class FileAttachmentCommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'file_attachment', 'review_request_id', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('caption', 'file_attachment')
    raw_id_fields = ('file_attachment', 'reply_to')

    def review_request_id(self, obj):
        return obj.review.get().review_request.id
    review_request_id.short_description = _('Review request ID')


admin.site.register(FileAttachment, FileAttachmentAdmin)
admin.site.register(FileAttachmentComment, FileAttachmentCommentAdmin)
