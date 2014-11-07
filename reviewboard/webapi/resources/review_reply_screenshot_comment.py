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
from reviewboard.webapi.resources.base_screenshot_comment import \
    BaseScreenshotCommentResource
from reviewboard.webapi.resources.review_screenshot_comment import \
    ReviewScreenshotCommentResource


class ReviewReplyScreenshotCommentResource(BaseScreenshotCommentResource):
    """Provides information on replies to screenshot comments made on a
    review reply.

    If the reply is a draft, then comments can be added, deleted, or
    changed on this list. However, if the reply is already published,
    then no changed can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model_parent_key = 'review'
    fields = dict({
        'reply_to': {
            'type': ReviewScreenshotCommentResource,
            'description': 'The comment being replied to.',
        },
    }, **BaseScreenshotCommentResource.fields)

    mimetype_list_resource_name = 'review-reply-screenshot-comments'
    mimetype_item_resource_name = 'review-reply-screenshot-comment'

    def get_queryset(self, request, review_id, reply_id, *args, **kwargs):
        q = super(ReviewReplyScreenshotCommentResource, self).get_queryset(
            request, *args, **kwargs)
        q = q.filter(review=reply_id, review__base_reply_to=review_id)
        return q

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        required=BaseScreenshotCommentResource.REPLY_REQUIRED_CREATE_FIELDS,
        optional=BaseScreenshotCommentResource.REPLY_OPTIONAL_CREATE_FIELDS,
        allow_unknown=True
    )
    def create(self, request, reply_to_id, *args, **kwargs):
        """Creates a reply to a screenshot comment on a review.

        This will create a reply to a screenshot comment on a review.
        The new comment will contain the same dimensions of the comment
        being replied to, but may contain new text.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            reply = resources.review_reply.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review_reply.has_modify_permissions(request, reply):
            return self._no_access_error(request.user)

        try:
            comment = resources.review_screenshot_comment.get_object(
                request,
                comment_id=reply_to_id,
                *args, **kwargs)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'reply_to_id': ['This is not a valid screenshot '
                                    'comment ID'],
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
            new_comment = self.model(screenshot=comment.screenshot,
                                     reply_to=comment,
                                     x=comment.x,
                                     y=comment.y,
                                     w=comment.w,
                                     h=comment.h)
            is_new = True

        self.update_comment(new_comment, is_reply=True, **kwargs)

        data = {
            self.item_result_key: new_comment,
        }

        if is_new:
            reply.screenshot_comments.add(new_comment)
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
        optional=BaseScreenshotCommentResource.REPLY_OPTIONAL_UPDATE_FIELDS,
        allow_unknown=True
    )
    def update(self, request, *args, **kwargs):
        """Updates a reply to a screenshot comment.

        This can only update the text in the comment. The comment being
        replied to cannot change.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            reply = resources.review_reply.get_object(request, *args, **kwargs)
            screenshot_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review_reply.has_modify_permissions(request, reply):
            return self._no_access_error(request.user)

        self.update_comment(screenshot_comment, is_reply=True, **kwargs)

        return 200, {
            self.item_result_key: screenshot_comment,
        }

    @augment_method_from(BaseScreenshotCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes a screenshot comment from a draft reply.

        This will remove the comment from the reply. This cannot be undone.

        Only comments on draft replies can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response, this will return :http:`204`.
        """
        pass

    @augment_method_from(BaseScreenshotCommentResource)
    def get(self, *args, **kwargs):
        """Returns information on a reply to a screenshot comment.

        Much of the information will be identical to that of the comment
        being replied to. For example, the region on the screenshot.
        This is because the reply to the comment is meant to cover the
        exact same section of the screenshot that the original comment covers.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of replies to screenshot comments made on a
        review reply.
        """
        pass


review_reply_screenshot_comment_resource = \
    ReviewReplyScreenshotCommentResource()
