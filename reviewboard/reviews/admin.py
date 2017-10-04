from __future__ import unicode_literals

from django.contrib import admin
from django.template.defaultfilters import truncatechars
from django.utils.translation import ugettext_lazy as _

from reviewboard.reviews.forms import DefaultReviewerForm, GroupForm
from reviewboard.reviews.models import (Comment,
                                        DefaultReviewer,
                                        FileAttachmentComment,
                                        GeneralComment,
                                        Group,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Screenshot,
                                        ScreenshotComment,
                                        StatusUpdate)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('truncated_text', 'review_request_id', 'first_line',
                    'num_lines', 'timestamp')
    search_fields = ['text']
    list_filter = ('timestamp',)
    raw_id_fields = ('filediff', 'interfilediff', 'reply_to')
    ordering = ['-timestamp']

    def review_request_id(self, obj):
        return obj.review.get().review_request.display_id
    review_request_id.short_description = _('Review request ID')

    def truncated_text(self, obj):
        return truncatechars(obj.text, 60)
    truncated_text.short_description = _('Comment Text')


class DefaultReviewerAdmin(admin.ModelAdmin):
    form = DefaultReviewerForm
    filter_horizontal = ('repository', 'groups', 'people',)
    list_display = ('name', 'file_regex')
    raw_id_fields = ('local_site',)
    fieldsets = (
        (_('General Information'), {
            'fields': ('name', 'file_regex', 'local_site'),
            'classes': ['wide'],
        }),
        (_('Reviewers'), {
            'fields': ('groups', 'people'),
        }),
        (_('Repositories'), {
            'description': _('<p>A default reviewer will cover all '
                             'repositories, unless assigned one or more '
                             'specific repositories below.</p>'),
            'fields': ('repository',),
        })
    )


class GroupAdmin(admin.ModelAdmin):
    form = GroupForm
    list_display = ('name', 'display_name', 'mailing_list', 'invite_only',
                    'visible')
    raw_id_fields = ('local_site',)
    fieldsets = (
        (_('General Information'), {
            'fields': ('name', 'display_name', 'mailing_list',
                       'email_list_only', 'visible'),
        }),
        (_('Access Control'), {
            'fields': ('invite_only', 'users', 'local_site',
                       'is_default_group'),
        }),
        (_('State'), {
            'fields': ('incoming_request_count', 'extra_data'),
            'classes': ('collapse',),
        }),
    )


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('review_request', 'user', 'public', 'ship_it',
                    'is_reply', 'timestamp')
    list_filter = ('public', 'timestamp')
    search_fields = ['review_request__summary']
    raw_id_fields = ('review_request', 'user', 'base_reply_to',
                     'body_top_reply_to', 'body_bottom_reply_to',
                     'comments', 'screenshot_comments',
                     'file_attachment_comments', 'general_comments',
                     'reviewed_diffset')
    fieldsets = (
        (_('General Information'), {
            'fields': ('user', 'review_request', 'public', 'ship_it',
                       'body_top_rich_text', 'body_top',
                       'body_bottom_rich_text', 'body_bottom'),
        }),
        (_('Related Objects'), {
            'fields': ('base_reply_to',
                       'body_top_reply_to',
                       'body_bottom_reply_to',
                       'comments',
                       'screenshot_comments',
                       'file_attachment_comments',
                       'general_comments'),
            'classes': ('collapse',)
        }),
        (_('State'), {
            'fields': ('email_message_id', 'time_emailed', 'extra_data'),
            'classes': ('collapse',)
        })
    )


class ReviewRequestAdmin(admin.ModelAdmin):
    list_display = ('summary', 'submitter', 'status', 'public', 'last_updated')
    list_filter = ('public', 'status', 'time_added', 'last_updated',
                   'repository')
    search_fields = ['summary']
    raw_id_fields = ('submitter', 'diffset_history', 'screenshots',
                     'inactive_screenshots', 'file_attachments',
                     'inactive_file_attachments', 'changedescs', 'local_site',
                     'depends_on', 'repository')
    filter_horizontal = ('target_people', 'target_groups')
    fieldsets = (
        (_('General Information'), {
            'fields': ('submitter', 'public', 'status',
                       'summary',
                       'description_rich_text',
                       'description',
                       'testing_done_rich_text',
                       'testing_done',
                       'bugs_closed', 'repository', 'branch',
                       'depends_on', 'commit_id', 'time_added')
        }),
        (_('Reviewers'), {
            'fields': ('target_people', 'target_groups'),
        }),
        (_('Related Objects'), {
            'fields': ('screenshots', 'inactive_screenshots',
                       'file_attachments', 'inactive_file_attachments',
                       'changedescs', 'diffset_history', 'local_site'),
            'classes': ['collapse'],
        }),
        (_('State'), {
            'description': _('<p>This is advanced state that should not be '
                             'modified unless something is wrong.</p>'),
            'fields': (
                'email_message_id',
                'time_emailed',
                'last_review_activity_timestamp',
                'shipit_count',
                'issue_open_count',
                'issue_resolved_count',
                'issue_dropped_count',
                'issue_verifying_count',
                'file_attachments_count',
                'inactive_file_attachments_count',
                'screenshots_count',
                'inactive_screenshots_count',
                'local_id',
                'extra_data',
            ),
            'classes': ['collapse'],
        }),
    )

    actions = [
        'close_submitted',
        'close_discarded',
        'reopen',
    ]

    def close_submitted(self, request, queryset):
        rows_updated = queryset.update(status=ReviewRequest.SUBMITTED)

        if rows_updated == 1:
            msg = '1 review request was closed as submitted.'
        else:
            msg = '%s review requests were closed as submitted.' % \
                  rows_updated

        self.message_user(request, msg)

    close_submitted.short_description = \
        _("Close selected review requests as submitted")

    def close_discarded(self, request, queryset):
        rows_updated = queryset.update(status=ReviewRequest.DISCARDED)

        if rows_updated == 1:
            msg = '1 review request was closed as discarded.'
        else:
            msg = '%s review requests were closed as discarded.' % \
                  rows_updated

        self.message_user(request, msg)

    close_discarded.short_description = \
        _("Close selected review requests as discarded")

    def reopen(self, request, queryset):
        rows_updated = queryset.update(status=ReviewRequest.PENDING_REVIEW)

        if rows_updated == 1:
            msg = '1 review request was reopened.'
        else:
            msg = '%s review requests were reopened.' % rows_updated

        self.message_user(request, msg)

    reopen.short_description = _("Reopen selected review requests")


class ReviewRequestDraftAdmin(admin.ModelAdmin):
    list_display = ('summary', 'submitter', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ['summary']
    raw_id_fields = ('review_request', 'diffset', 'screenshots',
                     'inactive_screenshots', 'changedesc')
    filter_horizontal = ('target_people', 'target_groups')
    fieldsets = (
        (_('General Information'), {
            'fields': ('review_request',
                       'summary',
                       'description_rich_text',
                       'description',
                       'testing_done_rich_text',
                       'testing_done',
                       'depends_on', 'bugs_closed', 'branch', 'commit_id'),
        }),
        (_('Reviewers'), {
            'fields': ('target_people', 'target_groups'),
        }),
        (_('Related Objects'), {
            'fields': ('screenshots', 'inactive_screenshots', 'changedesc',
                       'diffset'),
            'classes': ['collapse'],
        }),
        (_('State'), {
            'fields': (
                'file_attachments_count',
                'inactive_file_attachments_count',
                'screenshots_count',
                'inactive_screenshots_count',
                'extra_data',
            ),
        }),
    )


class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'caption', 'image', 'review_request_id')
    list_display_links = ('thumb', 'caption')
    search_fields = ('caption',)

    def review_request_id(self, obj):
        return obj.review_request.get().id
    review_request_id.short_description = _('Review request ID')


class ScreenshotCommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'screenshot', 'review_request_id', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ['text']
    raw_id_fields = ('screenshot', 'reply_to')

    def review_request_id(self, obj):
        return obj.review.get().review_request.id
    review_request_id.short_description = _('Review request ID')


class FileAttachmentCommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'file_attachment', 'review_request_id',
                    'timestamp')
    list_filter = ('timestamp',)
    search_fields = ['text']
    raw_id_fields = ('file_attachment', 'reply_to')

    def review_request_id(self, obj):
        return obj.review.get().review_request.id
    review_request_id.short_description = _('Review request ID')


class GeneralCommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'review_request_id', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ['text']
    raw_id_fields = ('reply_to',)

    def review_request_id(self, obj):
        return obj.review.get().review_request.id
    review_request_id.short_description = _('Review request ID')


class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ('review_request_id', 'summary', 'description')
    raw_id_fields = ('user', 'review_request', 'change_description', 'review')

    def review_request_id(self, obj):
        return obj.review_request.id
    review_request_id.short_description = _('Review request ID')


admin.site.register(Comment, CommentAdmin)
admin.site.register(DefaultReviewer, DefaultReviewerAdmin)
admin.site.register(FileAttachmentComment, FileAttachmentCommentAdmin)
admin.site.register(GeneralComment, GeneralCommentAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(ReviewRequest, ReviewRequestAdmin)
admin.site.register(ReviewRequestDraft, ReviewRequestDraftAdmin)
admin.site.register(Screenshot, ScreenshotAdmin)
admin.site.register(ScreenshotComment, ScreenshotCommentAdmin)
admin.site.register(StatusUpdate, StatusUpdateAdmin)
