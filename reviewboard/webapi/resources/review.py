from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review import BaseReviewResource


class ReviewResource(BaseReviewResource):
    """Provides information on reviews made on a review request.

    Each review can contain zero or more comments on diffs, screenshots or
    file attachments. It may also have text preceding the comments (the
    ``body_top`` field), and text following the comments (``body_bottom``).

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
    ]

    list_child_resources = [
        resources.review_draft,
    ]

    @webapi_check_local_site
    @augment_method_from(BaseReviewResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of all public reviews on a review request."""
        pass

    def get_base_reply_to_field(self, *args, **kwargs):
        return {
            'base_reply_to__isnull': True,
        }


review_resource = ReviewResource()
