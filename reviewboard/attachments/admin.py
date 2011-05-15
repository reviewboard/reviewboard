from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import FileAttachmentComment


class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ('file', 'caption', 'review_request_id')
    list_display_links = ('file', 'caption')
    search_fields = ('caption',)

    def review_request_id(self, obj):
        return obj.review_request.get().id
    review_request_id.short_description = _('Review request ID')


class FileAttachmentCommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'file', 'review_request_id', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('caption', 'file')
    raw_id_fields = ('file', 'reply_to')

    def review_request_id(self, obj):
        return obj.review.get().review_request.id
    review_request_id.short_description = _('Review request ID')


admin.site.register(FileAttachment, FileAttachmentAdmin)
admin.site.register(FileAttachmentComment, FileAttachmentCommentAdmin)
