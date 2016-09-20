from __future__ import unicode_literals

from django.utils.html import escape
from django.utils.six.moves.urllib.parse import urlparse
from djblets.util.templatetags.djblets_images import crop_image

from reviewboard.admin.server import build_server_url
from reviewboard.reviews.ui.base import FileAttachmentReviewUI


class ImageReviewUI(FileAttachmentReviewUI):
    name = 'Image'
    supported_mimetypes = ['image/*']

    allow_inline = True
    supports_diffing = True

    js_model_class = 'RB.ImageReviewable'
    js_view_class = 'RB.ImageReviewableView'

    def get_js_model_data(self):
        data = super(ImageReviewUI, self).get_js_model_data()
        data['imageURL'] = self.obj.file.url

        if self.diff_against_obj:
            data['diffAgainstImageURL'] = self.diff_against_obj.file.url

        return data

    def serialize_comments(self, comments):
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

    def get_comment_thumbnail(self, comment):
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
