from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_diff_comment import \
    BaseDiffCommentResource
from reviewboard.webapi.resources.review_diff_comment import \
    ReviewDiffCommentResource


class ReviewReplyDiffCommentResource(BaseDiffCommentResource):
    """Provides information on replies to diff comments made on a review reply.

    If the reply is a draft, then comments can be added, deleted, or
    changed on this list. However, if the reply is already published,
    then no changed can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'
    fields = dict({
        'reply_to': {
            'type': ReviewDiffCommentResource,
            'description': 'The comment being replied to.',
        },
    }, **BaseDiffCommentResource.fields)

    mimetype_list_resource_name = 'review-reply-diff-comments'
    mimetype_item_resource_name = 'review-reply-diff-comment'

    def get_queryset(self, request, review_id, reply_id, *args, **kwargs):
        q = super(ReviewReplyDiffCommentResource, self).get_queryset(
            request, *args, **kwargs)
        q = q.filter(review=reply_id, review__base_reply_to=review_id)
        return q

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required=BaseDiffCommentResource.REPLY_REQUIRED_CREATE_FIELDS,
        optional=BaseDiffCommentResource.REPLY_OPTIONAL_CREATE_FIELDS,
        allow_unknown=True
    )
    def create(self, request, reply_to_id, *args, **kwargs):
        """Creates a new reply to a diff comment on the parent review.

        This will create a new diff comment as part of this reply. The reply
        must be a draft reply.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            reply = resources.review_reply.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review_reply.has_modify_permissions(request, reply):
            return self._no_access_error(request.user)

        try:
            comment = resources.review_diff_comment.get_object(
                request, comment_id=reply_to_id, *args, **kwargs)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'reply_to_id': ['This is not a valid comment ID'],
                }
            }

        q = self._get_queryset(request, *args, **kwargs)
        q = q.filter(Q(reply_to=comment) & Q(review=reply))

        try:
            new_comment = q.get()

            # This already exists. Go ahead and update, but we're going to
            # redirect the user to the right place.
            is_new = False
        except self.model.DoesNotExist:
            new_comment = self.model(filediff=comment.filediff,
                                     interfilediff=comment.interfilediff,
                                     reply_to=comment,
                                     first_line=comment.first_line,
                                     num_lines=comment.num_lines)
            is_new = True

        self.update_comment(new_comment, is_reply=True, **kwargs)

        data = {
            self.item_result_key: new_comment,
        }

        if is_new:
            reply.comments.add(new_comment)
            reply.save()

            return 201, data
        else:
            return 303, data, {
                'Location': self.get_href(new_comment, request, *args,
                                          **kwargs)
            }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional=BaseDiffCommentResource.REPLY_OPTIONAL_UPDATE_FIELDS,
        allow_unknown=True
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply to a diff comment.

        This can only update the text in the comment. The comment being
        replied to cannot change.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            reply = resources.review_reply.get_object(request, *args, **kwargs)
            diff_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review_reply.has_modify_permissions(request, reply):
            return self._no_access_error(request.user)

        self.update_comment(diff_comment, is_reply=True, **kwargs)

        return 200, {
            self.item_result_key: diff_comment,
        }

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes a comment from a draft reply.

        This will remove the comment from the reply. This cannot be undone.

        Only comments on draft replies can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def get(self, *args, **kwargs):
        """Returns information on a reply to a comment.

        Much of the information will be identical to that of the comment
        being replied to. For example, the range of lines. This is because
        the reply to the comment is meant to cover the exact same code that
        the original comment covers.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseDiffCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of replies to comments made on a review reply.

        This list can be filtered down by using the ``?line=`` and
        ``?interdiff-revision=``.

        To filter for comments that start on a particular line in the file,
        using ``?line=``.

        To filter for comments that span revisions of diffs, you can specify
        the second revision in the range using ``?interdiff-revision=``.
        """
        pass


review_reply_diff_comment_resource = ReviewReplyDiffCommentResource()
