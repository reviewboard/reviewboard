from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from

from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources.base_screenshot_comment import \
    BaseScreenshotCommentResource


class ScreenshotCommentResource(BaseScreenshotCommentResource):
    """Provides information on screenshots comments made on a review request.

    The list of comments cannot be modified from this resource. It's meant
    purely as a way to see existing comments that were made on a diff. These
    comments will span all public reviews.

    If the ``text_type`` field is set to ``markdown``, then the ``text``
    field should be interpreted by the client as Markdown text.

    The returned text in the payload can be provided in a different format
    by passing ``?force-text-type=`` in the request. This accepts all the
    possible values listed in the ``text_type`` field below.
    """
    model_parent_key = 'screenshot'
    uri_object_key = None

    def get_queryset(self, request, screenshot_id, *args, **kwargs):
        q = super(ScreenshotCommentResource, self).get_queryset(
            request, *args, **kwargs)
        q = q.filter(screenshot=screenshot_id)
        return q

    @webapi_check_local_site
    @augment_method_from(BaseScreenshotCommentResource)
    def get_list(self, *args, **kwargs):
        """Returns the list of screenshot comments on a screenshot.

        This list of comments will cover all comments made on this
        screenshot from all reviews.
        """
        pass


screenshot_comment_resource = ScreenshotCommentResource()
