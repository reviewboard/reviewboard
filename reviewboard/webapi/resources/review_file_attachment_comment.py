from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.attachments.models import FileAttachment
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_file_attachment_comment import \
    BaseFileAttachmentCommentResource


class ReviewFileAttachmentCommentResource(BaseFileAttachmentCommentResource):
    """Provides information on file comments made on a review.

    If the review is a draft, then comments can be added, deleted, or
    changed on this list. However, if the review is already published,
    then no changes can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'

    def get_queryset(self, request, review_id, *args, **kwargs):
        q = super(ReviewFileAttachmentCommentResource, self).get_queryset(
            request, *args, **kwargs)
        return q.filter(review=review_id)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            PERMISSION_DENIED, NOT_LOGGED_IN)
    @webapi_request_fields(
        required=dict({
            'file_attachment_id': {
                'type': int,
                'description': 'The ID of the file attachment being '
                               'commented on.',
            },
        }, **BaseFileAttachmentCommentResource.REQUIRED_CREATE_FIELDS),
        optional=dict({
            'diff_against_file_attachment_id': {
                'type': int,
                'description': 'The ID of the file attachment that '
                               '``file_attachment_id`` is diffed against. The '
                               'comment applies to the diff between these two '
                               'attachments.',
            },
        }, **BaseFileAttachmentCommentResource.OPTIONAL_CREATE_FIELDS),
        allow_unknown=True
    )
    def create(self, request, file_attachment_id=None,
               diff_against_file_attachment_id=None, *args, **kwargs):
        """Creates a file comment on a review.

        This will create a new comment on a file as part of a review.
        The comment contains text only.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review.has_modify_permissions(request, review):
            return self._no_access_error(request.user)

        try:
            file_attachment = \
                FileAttachment.objects.get(pk=file_attachment_id,
                                           review_request=review_request)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'file_attachment_id': ['This is not a valid file '
                                           'attachment ID'],
                }
            }

        diff_against_file_attachment = None

        if diff_against_file_attachment_id:
            try:
                diff_against_file_attachment = FileAttachment.objects.get(
                    pk=diff_against_file_attachment_id,
                    review_request=review_request)
            except ObjectDoesNotExist:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'diff_against_file_attachment_id': [
                            'This is not a valid file attachment ID'
                        ],
                    }
                }

        new_comment = self.create_comment(
            review=review,
            file_attachment=file_attachment,
            diff_against_file_attachment=diff_against_file_attachment,
            fields=('file_attachment', 'diff_against_file_attachment'),
            **kwargs)
        review.file_attachment_comments.add(new_comment)

        return 201, {
            self.item_result_key: new_comment,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional=BaseFileAttachmentCommentResource.OPTIONAL_UPDATE_FIELDS,
        allow_unknown=True
    )
    def update(self, request, *args, **kwargs):
        """Updates a file comment.

        This can update the text or region of an existing comment. It
        can only be done for comments that are part of a draft review.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
            file_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        # Determine whether or not we're updating the issue status.
        if self.should_update_issue_status(file_comment, **kwargs):
            return self.update_issue_status(request, self, *args, **kwargs)

        if not resources.review.has_modify_permissions(request, review):
            return self._no_access_error(request.user)

        self.update_comment(file_comment, **kwargs)

        return 200, {
            self.item_result_key: file_comment,
        }

    @augment_method_from(BaseFileAttachmentCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes the comment.

        This will remove the comment from the review. This cannot be undone.

        Only comments on draft reviews can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @augment_method_from(BaseFileAttachmentCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of file comments made on a review."""
        pass


review_file_attachment_comment_resource = ReviewFileAttachmentCommentResource()
