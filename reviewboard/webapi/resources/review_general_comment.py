from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review_general_comment import \
    BaseReviewGeneralCommentResource


class ReviewGeneralCommentResource(BaseReviewGeneralCommentResource):
    """Provides information on general comments made on a review.

    If the review is a draft, then comments can be added, deleted, or
    changed on this list. However, if the review is already published,
    then no changes can be made.
    """
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    policy_id = 'review_general_comment'
    model_parent_key = 'review'

    def get_queryset(self, request, review_id, *args, **kwargs):
        q = super(ReviewGeneralCommentResource, self).get_queryset(
            request, *args, **kwargs)
        return q.filter(review=review_id)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, INVALID_FORM_DATA,
                            PERMISSION_DENIED, NOT_LOGGED_IN)
    @webapi_request_fields(
        required=BaseReviewGeneralCommentResource.REQUIRED_CREATE_FIELDS,
        optional=BaseReviewGeneralCommentResource.OPTIONAL_CREATE_FIELDS,
        allow_unknown=True
    )
    def create(self, request, *args, **kwargs):
        """Creates a general comment on a review.

        This will create a new comment on a review. The comment contains text
        only.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            review = resources.review.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not resources.review.has_modify_permissions(request, review):
            return self.get_no_access_error(request.user)

        return self.create_comment(fields=(),
                                   review=review,
                                   comments_m2m=review.general_comments,
                                   **kwargs)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional=BaseReviewGeneralCommentResource.OPTIONAL_UPDATE_FIELDS,
        allow_unknown=True
    )
    def update(self, request, *args, **kwargs):
        """Updates a general comment.

        This can update the text or region of an existing comment. It
        can only be done for comments that are part of a draft review.

        Extra data can be stored later lookup. See
        :ref:`webapi2.0-extra-data` for more information.
        """
        try:
            resources.review_request.get_object(request, *args, **kwargs)
            review = resources.review.get_object(request, *args, **kwargs)
            general_comment = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        return self.update_comment(request=request,
                                   review=review,
                                   comment=general_comment,
                                   **kwargs)

    @webapi_check_local_site
    @augment_method_from(BaseReviewGeneralCommentResource)
    def delete(self, *args, **kwargs):
        """Deletes the comment.

        This will remove the comment from the review. This cannot be undone.

        Only comments on draft reviews can be deleted. Attempting to delete
        a published comment will return a Permission Denied error.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @augment_method_from(BaseReviewGeneralCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of general comments made on a review."""
        pass


review_general_comment_resource = ReviewGeneralCommentResource()
