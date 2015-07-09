from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.reviews.models import Screenshot
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_screenshot_comment import \
    BaseScreenshotCommentResource


class ReviewScreenshotCommentResource(BaseScreenshotCommentResource):
    """Provides information on screenshots comments made on a review.

    If the review is a draft, then comments can be added, deleted, or
    changed on this list. However, if the review is already published,
    then no changes can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    policy_id = 'review_screenshot_comment'
    model_parent_key = 'review'

    def get_queryset(self, request, review_id, *args, **kwargs):
        q = super(ReviewScreenshotCommentResource, self).get_queryset(
            request, *args, **kwargs)
        return q.filter(review=review_id)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_request_fields(
        required=dict({
            'screenshot_id': {
                'type': int,
                'description': 'The ID of the screenshot being commented on.',
            },
            'x': {
                'type': int,
                'description': 'The X location for the comment.',
            },
            'y': {
                'type': int,
                'description': 'The Y location for the comment.',
            },
            'w': {
                'type': int,
                'description': 'The width of the comment region.',
            },
            'h': {
                'type': int,
                'description': 'The height of the comment region.',
            },
        }, **BaseScreenshotCommentResource.REQUIRED_CREATE_FIELDS),
        optional=BaseScreenshotCommentResource.OPTIONAL_CREATE_FIELDS,
        allow_unknown=True,
    )
    def create(self, request, screenshot_id, *args, **kwargs):
        """Creates a screenshot comment on a review.

        This will create a new comment on a screenshot as part of a review.
        The comment contains text and dimensions for the area being commented
        on.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review.has_modify_permissions(request, review):
            return self.get_no_access_error(request)

        try:
            screenshot = Screenshot.objects.get(pk=screenshot_id,
                                                review_request=review_request)
        except ObjectDoesNotExist:
            return INVALID_FORM_DATA, {
                'fields': {
                    'screenshot_id': ['This is not a valid screenshot ID'],
                }
            }

        new_comment = self.create_comment(
            review=review,
            screenshot=screenshot,
            fields=('screenshot', 'x', 'y', 'w', 'h'),
            **kwargs)
        review.screenshot_comments.add(new_comment)

        return 201, {
            self.item_result_key: new_comment,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional=dict({
            'x': {
                'type': int,
                'description': 'The X location for the comment.',
            },
            'y': {
                'type': int,
                'description': 'The Y location for the comment.',
            },
            'w': {
                'type': int,
                'description': 'The width of the comment region.',
            },
            'h': {
                'type': int,
                'description': 'The height of the comment region.',
            },
        }, **BaseScreenshotCommentResource.OPTIONAL_UPDATE_FIELDS),
        allow_unknown=True
    )
    def update(self, request, *args, **kwargs):
        """Updates a screenshot comment.

        This can update the text or region of an existing comment. It
        can only be done for comments that are part of a draft review.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
            screenshot_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        # Determine whether or not we're updating the issue status.
        if self.should_update_issue_status(screenshot_comment, **kwargs):
            return self.update_issue_status(request, self, *args, **kwargs)

        if not resources.review.has_modify_permissions(request, review):
            return self.get_no_access_error(request)

        self.update_comment(screenshot_comment, ('x', 'y', 'w', 'h'), **kwargs)

        return 200, {
            self.item_result_key: screenshot_comment,
        }

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes the comment.

        This will remove the comment from the review. This cannot be undone.

        Only comments on draft reviews can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of screenshot comments made on a review."""
        pass


review_screenshot_comment_resource = ReviewScreenshotCommentResource()
