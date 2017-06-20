from __future__ import unicode_literals

from django.utils import six
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_response_errors
from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard.reviews.errors import RevokeShipItError
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.errors import REVOKE_SHIP_IT_ERROR
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review import BaseReviewResource


class ReviewResource(BaseReviewResource):
    """Provides information on reviews made on a review request.

    Each review can contain zero or more comments on diffs, screenshots,
    file attachments or general comments not tied to any code or file.
    It may also have text preceding the comments (the ``body_top`` field),
    and text following the comments (``body_bottom``).

    A review may have replies made. Replies are flat, not threaded. Like a
    review, there may be body text and there may be comments (which are replies
    to comments on the parent review).

    If the ``ship_it`` field is true, then the reviewer has given their
    approval of the change, once all issues raised on comments have been
    addressed.
    """
    uri_object_key = 'review_id'
    model_parent_key = 'review_request'

    item_child_resources = [
        resources.review_diff_comment,
        resources.review_reply,
        resources.review_screenshot_comment,
        resources.review_file_attachment_comment,
        resources.review_general_comment,
    ]

    list_child_resources = [
        resources.review_draft,
    ]

    @webapi_check_local_site
    @augment_method_from(BaseReviewResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of all public reviews on a review request."""
        pass

    @webapi_response_errors(INVALID_FORM_DATA, REVOKE_SHIP_IT_ERROR)
    @augment_method_from(BaseReviewResource)
    def update(self, *args, **kwargs):
        pass

    def get_base_reply_to_field(self, *args, **kwargs):
        return {
            'base_reply_to__isnull': True,
        }

    def update_review(self, request, review, ship_it=None, *args, **kwargs):
        """Common function to update fields on a draft review.

        If the review is public and the caller has requested to set the Ship It
        state to False, this will attempt to revoke the Ship It, reporting any
        errors. Any other updates are handled by
        :py:meth:`BaseReviewResource.update_review
        <reviewboard.webapi.resources.base_review.BaseReviewResource.update_review>.

        Args:
            request (django.http.HttpRequest):
                The parent HTTP request.

            review (reviewboard.reviews.models.review.Review):
                The review being updated.

            ship_it (bool, optional):
                The updated Ship It state, if any.

            *args (tuple):
                Positional arguments to pass to the parent method.

            **kwargs (dict):
                Keyword arguments to pass to the parent method.

        Returns:
            object:
            The API payload or error to send.
        """
        # Before checking for modify permissions, we're going to check for
        # a special ability to revoke Ship Its. This is considered different
        # than modifying a review, as modification requires an unpublished
        # review.
        if review.public:
            if ship_it is False:
                if not review.can_user_revoke_ship_it(request.user):
                    return self.get_no_access_error(request)

                if not review.ship_it:
                    return INVALID_FORM_DATA, {
                        'fields': {
                            'ship_it': 'This review is not marked Ship It!',
                        },
                    }

                try:
                    review.revoke_ship_it(request.user)
                except RevokeShipItError as e:
                    return REVOKE_SHIP_IT_ERROR.with_message(
                        six.text_type(e))

                return 200, {
                    self.item_result_key: review,
                }
            elif ship_it is True:
                return INVALID_FORM_DATA, {
                    'fields': {
                        'ship_it': ('Published reviews cannot be updated with '
                                    'ship_it=true'),
                    }
                }

        return super(ReviewResource, self).update_review(
            request, review, ship_it=ship_it, *args, **kwargs)

review_resource = ReviewResource()
