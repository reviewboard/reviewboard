"""Unit tests for reviewboard.reviews.ui.image.ImageReviewUI."""
from __future__ import unicode_literals

from djblets.util.templatetags.djblets_images import crop_image

from reviewboard.admin.server import build_server_url
from reviewboard.reviews.ui.image import ImageReviewUI
from reviewboard.testing import TestCase


class ImageReviewUITests(TestCase):
    """Unit tests for reviewboard.reviews.ui.image.ImageReviewUI."""

    fixtures = ['test_users']

    def setUp(self):
        super(ImageReviewUITests, self).setUp()

        self.review_request = self.create_review_request()
        self.attachment = self.create_file_attachment(
            self.review_request)
        self.review = self.create_review(self.review_request)

    def test_get_comment_thumbnail(self):
        """Testing ImageReviewUI.get_comment_thumbnail for an image comment"""
        ui = ImageReviewUI(self.review_request, self.attachment)
        comment = self.create_file_attachment_comment(
            self.review,
            self.attachment,
            extra_fields={
                'x': 0,
                'y': 0,
                'width': 1,
                'height': 1,
            })
        thumbnail = ui.get_comment_thumbnail(comment)

        self.assertHTMLEqual(
            thumbnail,
            '<img class="modified-image" src="%s" width="1" height="1"'
            ' alt="%s" />'
            % (build_server_url(crop_image(self.attachment.file, 0, 0, 1, 1)),
               comment.text)
        )

    def test_get_comment_thumbnail_diff(self):
        """Testing ImageReviewUI.get_comment_thumbnail for an image diff
        comment
        """
        diff_attachment = self.create_file_attachment(self.review_request)

        ui = ImageReviewUI(self.review_request, self.attachment)
        ui.set_diff_against(diff_attachment)

        comment = self.create_file_attachment_comment(
            self.review,
            self.attachment,
            diff_attachment,
            extra_fields={
                'x': 0,
                'y': 0,
                'width': 1,
                'height': 1,
            })
        thumbnail = ui.get_comment_thumbnail(comment)

        self.assertHTMLEqual(
            thumbnail,
            '<div class="image-review-ui-diff-thumbnail">'
            '<img class="orig-image" src="%s" width="1" height="1" alt="%s" />'
            '<img class="modified-image" src="%s" width="1" height="1"'
            ' alt="%s" />'
            '</div>'
            % (build_server_url(crop_image(diff_attachment.file, 0, 0, 1, 1)),
               comment.text,
               build_server_url(crop_image(self.attachment.file, 0, 0, 1, 1)),
               comment.text)
        )
