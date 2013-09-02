from djblets.util.decorators import augment_method_from

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review import BaseReviewResource


class ReviewResource(BaseReviewResource):
    """Provides information on reviews."""
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
