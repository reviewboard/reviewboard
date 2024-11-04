"""Unit tests for reviewboard.attachments.mimetypes.TextMimetype.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

import kgb

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.safestring import SafeText

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.testing import TestCase


class TextMimetypeTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.attachments.mimetypes.TextMimetype.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    fixtures = ['test_users']

    def setUp(self):
        uploaded_file = SimpleUploadedFile(
            'test.txt',
            b'<p>This is a test</p>',
            content_type='text/plain')

        review_request = self.create_review_request(publish=True)

        form = UploadFileForm(review_request, files={
            'path': uploaded_file,
        })
        self.assertTrue(form.is_valid())

        self.file_attachment = form.create()

    def test_get_thumbnail_uncached_is_safe_text(self):
        """Testing TextMimetype.get_thumbnail string type is SafeText
        without cached thumbnail
        """
        thumbnail = self.file_attachment.thumbnail

        self.assertIsInstance(thumbnail, SafeText)

    def test_get_thumbnail_cached_is_safe_text(self):
        """Testing TextMimetype.get_thumbnail string type is SafeText with
        cached thumbnail
        """
        # Django's in-memory cache won't mangle the string types, so we can't
        # rely on just calling thumbnail twice. We have to fake it, so that
        # that we simulate the real-world behavior of getting a raw string
        # back out of a real cache.
        self.spy_on(self.file_attachment.mimetype_handler._generate_thumbnail,
                    call_fake=lambda self: '<div>My thumbnail</div>')

        thumbnail = self.file_attachment.thumbnail

        self.assertIsInstance(thumbnail, SafeText)

    def test_get_raw_thumbnail_image_url(self) -> None:
        """Testing TextMimetype.test_get_raw_thumbnail_image_url"""
        mimetype_handler = self.file_attachment.mimetype_handler
        assert mimetype_handler

        message = (
            'TextMimetype does not support generating thumbnail images.'
        )

        with self.assertRaisesMessage(NotImplementedError, message):
            mimetype_handler.get_raw_thumbnail_image_url(width=300)
