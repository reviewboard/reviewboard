"""A Review UI for image files."""

from __future__ import annotations

from typing import Optional, Sequence, TYPE_CHECKING
from urllib.parse import urlparse

from django.utils.html import escape
from djblets.util.templatetags.djblets_images import crop_image

from reviewboard.admin.server import build_server_url
from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.reviews.ui.base import (ReviewUI,
                                         SerializedComment,
                                         SerializedCommentBlocks)


if TYPE_CHECKING:
    from djblets.util.typing import JSONDict


class SerializedRegionComment(SerializedComment):
    """Serialized data for an image comment.

    This must be kept in sync with the definitions in
    :file:`reviewboard/static/rb/js/reviews/models/commentData.ts`.

    Version Added:
        7.0
    """

    #: The X position of the comment block, in pixels.
    x: int

    #: The Y position of the comment block, in pixels.
    y: int

    #: The width of the comment block, in pixels.
    width: int

    #: The height of the comment block, in pixels.
    height: int


class ImageReviewUI(ReviewUI[
    FileAttachment,
    FileAttachmentComment,
    SerializedRegionComment
]):
    """A Review UI for image files."""

    name = 'Image'
    supported_mimetypes = ['image/*']

    allow_inline = True
    supports_diffing = True
    supports_file_attachments = True

    js_model_class: str = 'RB.ImageReviewable'
    js_view_class: str = 'RB.ImageReviewableView'

    def get_page_cover_image_url(self):
        """Return the URL to an image used to depict this on other sites.

        The returned image URL will be used for services like Facebook, Slack,
        Twitter, etc. when linking to this file attachment.

        Returns:
            str:
            The absolute URL to an image used to depict this file attachment.
        """
        return self.obj.get_absolute_url()

    def get_js_model_data(self) -> JSONDict:
        """Return data to pass to the JavaScript Model during instantiation.

        This data will be passed as attributes to the reviewable model when
        constructed.

        Returns:
            dict:
            The attributes to pass to the model.
        """
        data = super(ImageReviewUI, self).get_js_model_data()
        data['imageURL'] = self.obj.get_absolute_url()

        if self.diff_against_obj:
            assert isinstance(self.diff_against_obj, FileAttachment)
            data['diffAgainstImageURL'] = \
                self.diff_against_obj.get_absolute_url()

        return data

    def serialize_comments(
        self,
        comments: Sequence[FileAttachmentComment],
    ) -> SerializedCommentBlocks[SerializedRegionComment]:
        """Serialize the comments for the file attachment.

        Args:
            comments (list of
                      reviewboard.reviews.models.FileAttachmentComment):
                The list of objects to serialize. This will be the result of
                :py:meth:`get_comments`.

        Returns:
            SerializedCommentBlocks:
            The serialized comment data.
        """
        result: SerializedCommentBlocks[SerializedRegionComment] = {}

        for comment in self.flat_serialized_comments(comments):
            try:
                position = (
                    f'{comment["x"]}x{comment["y"]}+'
                    f'{comment["width"]}+{comment["height"]}')
            except KeyError:
                # It's possible this comment was made before the review UI
                # was provided, meaning it has no data. If this is the case,
                # ignore this particular comment, since it doesn't have a
                # region.
                continue

            result.setdefault(position, []).append(comment)

        return result

    def get_comment_thumbnail(
        self,
        comment: FileAttachmentComment,
    ) -> Optional[str]:
        """Generate and return a thumbnail representing this comment.

        This will find the appropriate lines the comment applies to and
        return it as HTML suited for rendering in reviews.

        Args:
            comment (reviewboard.reviews.models.FileAttachmentComment):
                The comment to render the thumbnail for.

        Returns:
            str:
            The rendered comment thumbnail.
        """
        try:
            x = int(comment.extra_data['x'])
            y = int(comment.extra_data['y'])
            width = int(comment.extra_data['width'])
            height = int(comment.extra_data['height'])
        except (KeyError, ValueError):
            # This may be a comment from before we had review UIs. Or,
            # corrupted data. Either way, don't display anything.
            return None

        image_url = crop_image(comment.file_attachment.file,
                               x, y, width, height)

        if not urlparse(image_url).netloc:
            image_url = build_server_url(image_url)

        image_html = (
            '<img class="modified-image" src="%s" width="%s" height="%s" '
            'alt="%s" />'
            % (image_url, width, height, escape(comment.text)))

        if comment.diff_against_file_attachment_id:
            diff_against_image_url = crop_image(
                comment.diff_against_file_attachment.file,
                x, y, width, height)

            if not urlparse(diff_against_image_url).netloc:
                diff_against_image_url = build_server_url(
                    diff_against_image_url)

            diff_against_image_html = (
                '<img class="orig-image" src="%s" width="%s" '
                'height="%s" alt="%s" />'
                % (diff_against_image_url, width, height,
                   escape(comment.text)))

            return ('<div class="image-review-ui-diff-thumbnail">%s%s</div>'
                    % (diff_against_image_html, image_html))
        else:
            return image_html
