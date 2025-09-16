"""Unit tests for reviewboard.attachments.mimetypes.ImageMimetype.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

import os

import kgb

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.mimetypes import logger as mimetypes_logger
from reviewboard.attachments.tests.base import BaseFileAttachmentTestCase


class ImageMimetypeTests(kgb.SpyAgency, BaseFileAttachmentTestCase):
    """Unit tests for reviewboard.attachments.mimetypes.ImageMimetype.

    Version Added:
        6.0
    """

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        image_file = self.make_uploaded_file()

        review_request = self.create_review_request(publish=True)

        form = UploadFileForm(review_request, files={
            'path': image_file,
        })
        self.assertTrue(form.is_valid())

        self.file_attachment = form.create()

    def test_get_thumbnail(self) -> None:
        """Testing ImageMimetype.get_thumbnail"""
        file = self.file_attachment.file
        storage = file.storage
        filename_base = os.path.splitext(file.name)[0]
        download_url = 'http://example.com/r/1/file/1/download/?thumbnail=1'

        self.assertHTMLEqual(
            self.file_attachment.thumbnail,
            f'<div class="file-thumbnail">'
            f'<img src="{download_url}&width=300"'
            f' srcset="{download_url}&width=300 1x,'
            f' {download_url}&width=600 2x, {download_url}&width=900 3x"'
            f'alt="" width="300" />'
            f'</div>')

        # These shouldn't exist until the URLs are accessed.
        self.assertFalse(storage.exists(f'{filename_base}_300.png'))
        self.assertFalse(storage.exists(f'{filename_base}_600.png'))
        self.assertFalse(storage.exists(f'{filename_base}_900.png'))

    def test_get_raw_thumbnail_image_url(self) -> None:
        """Testing ImageMimetype.get_raw_thumbnail_image_url"""
        file = self.file_attachment.file
        storage = file.storage
        filename_base = os.path.splitext(file.name)[0]

        mimetype_handler = self.file_attachment.mimetype_handler
        assert mimetype_handler

        filename = mimetype_handler.get_raw_thumbnail_image_url(width=300)
        self.assertTrue(filename)
        self.assertTrue(storage.exists(f'{filename_base}_300.png'))

    def test_generate_thumbnail_image_with_create_if_missing_false(
        self,
    ) -> None:
        """Testing ImageMimetype.get_raw_thumbnail_image_url with
        create_if_missing=False
        """
        file = self.file_attachment.file
        storage = file.storage
        filename_base = os.path.splitext(file.name)[0]

        mimetype_handler = self.file_attachment.mimetype_handler
        assert mimetype_handler

        filename = mimetype_handler.generate_thumbnail_image(
            width=300,
            create_if_missing=False)

        self.assertIsNone(filename)
        self.assertFalse(storage.exists(f'{filename_base}_300.png'))

    def test_delete_associated_files(self) -> None:
        """Testing ImageMimetype.delete_associated_files"""
        file = self.file_attachment.file
        storage = file.storage

        mimetype_handler = self.file_attachment.mimetype_handler
        assert mimetype_handler

        filename_base = os.path.splitext(file.name)[0]
        filename_300 = f'{filename_base}_300.png'
        filename_600 = f'{filename_base}_600.png'

        mimetype_handler.generate_thumbnail_image(width=300)
        mimetype_handler.generate_thumbnail_image(width=600)

        self.assertTrue(storage.exists(filename_300))
        self.assertTrue(storage.exists(filename_600))

        mimetype_handler.delete_associated_files()

        self.assertFalse(storage.exists(filename_300))
        self.assertFalse(storage.exists(filename_600))

        self.spy_on(storage.delete)
        self.spy_on(mimetypes_logger.warning)

        # A second call shouldn't do anything, outside of checking thumbnail
        # existence.
        mimetype_handler.delete_associated_files()

        self.assertSpyNotCalled(storage.delete)
