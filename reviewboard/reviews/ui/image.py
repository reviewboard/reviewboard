"""A Review UI for image files."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from urllib.parse import urlparse

from django.utils.html import escape
from djblets.util.templatetags.djblets_images import crop_image

from reviewboard.admin.server import build_server_url
from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.ui.base import ReviewUI


if TYPE_CHECKING:
    from djblets.util.typing import JSONDict

    from reviewboard.reviews.models import (
        BaseComment,
        FileAttachmentComment)


class ImageReviewUI(ReviewUI):
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
        assert isinstance(self.obj, FileAttachment)

        return self.obj.get_absolute_url()

    def get_js_model_data(self) -> JSONDict:
        """Return data to pass to the JavaScript Model during instantiation.

        This data will be passed as attributes to the reviewable model when
        constructed.

        Returns:
            dict:
            The attributes to pass to the model.
        """
        assert isinstance(self.obj, FileAttachment)

        data = super(ImageReviewUI, self).get_js_model_data()
        data['imageURL'] = self.obj.file.url

        if self.diff_against_obj:
            assert isinstance(self.diff_against_obj, FileAttachment)
            data['diffAgainstImageURL'] = self.diff_against_obj.file.url

        return data

    def serialize_comments(
        self,
        comments: List[BaseComment],
    ) -> JSONDict:
        """Serialize the comments for the Review UI target.

        By default, this will return a list of serialized comments,
        but it can be overridden to return other list or dictionary-based
        representations, such as comments grouped by an identifier or region.
        These representations must be serializable into JSON.

        Args:
            comments (list of reviewboard.reviews.models.base_comment.
                      BaseComment):
                The list of objects to serialize. This will be the result of
                :py:meth:`get_comments`.

        Returns:
            dict:
            The serialized comment data.
        """
        result = {}
        serialized_comments = \
            super(ImageReviewUI, self).serialize_comments(comments)

        for serialized_comment in serialized_comments:
            try:
                position = '%(x)sx%(y)s+%(width)s+%(height)s' \
                           % serialized_comment
            except KeyError:
                # It's possible this comment was made before the review UI
                # was provided, meaning it has no data. If this is the case,
                # ignore this particular comment, since it doesn't have a
                # region.
                continue

            result.setdefault(position, []).append(serialized_comment)

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
