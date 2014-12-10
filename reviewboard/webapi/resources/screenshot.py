from __future__ import unicode_literals

from djblets.util.decorators import augment_method_from

from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_screenshot import BaseScreenshotResource


class ScreenshotResource(BaseScreenshotResource):
    """A resource representing a screenshot on a review request."""
    model_parent_key = 'review_request'

    item_child_resources = [
        resources.screenshot_comment,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get_parent_object(self, obj):
        return obj.get_review_request()

    @augment_method_from(BaseScreenshotResource)
    def get_list(self, *args, **kwargs):
        """Returns a list of screenshots on the review request.

        Each screenshot in this list is an uploaded screenshot that is
        shown on the review request.
        """
        pass

    @augment_method_from(BaseScreenshotResource)
    def create(self, request, *args, **kwargs):
        """Creates a new screenshot from an uploaded file.

        This accepts any standard image format (PNG, GIF, JPEG) and associates
        it with a draft of a review request.

        Creating a new screenshot will automatically create a new review
        request draft, if one doesn't already exist. This screenshot will
        be part of that draft, and will be shown on the review request
        when it's next published.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The screenshot's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.png"

            <PNG content here>
            -- SoMe BoUnDaRy --
        """
        pass

    @augment_method_from(BaseScreenshotResource)
    def update(self, request, caption=None, *args, **kwargs):
        """Updates the screenshot's data.

        This allows updating the screenshot. The caption, currently,
        is the only thing that can be updated.

        Updating a screenshot will automatically create a new review request
        draft, if one doesn't already exist. The updates won't be public
        until the review request draft is published.
        """
        pass

    @augment_method_from(BaseScreenshotResource)
    def delete(self, *args, **kwargs):
        """Deletes the screenshot.

        This will remove the screenshot from the draft review request.
        This cannot be undone.

        Deleting a screenshot will automatically create a new review request
        draft, if one doesn't already exist. The screenshot won't be actually
        removed until the review request draft is published.

        This can be used to remove old screenshots that were previously
        shown, as well as newly added screenshots that were part of the
        draft.

        Instead of a payload response on success, this will return :http:`204`.
        """
        pass


screenshot_resource = ScreenshotResource()
