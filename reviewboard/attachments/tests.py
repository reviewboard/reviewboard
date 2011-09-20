import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.reviews.models import ReviewRequest


class FileAttachmentTests(TestCase):
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def test_upload_file(self):
        """Testing uploading a file attachment."""
        filename = os.path.join(settings.HTDOCS_ROOT,
                                'media', 'rb', 'images', 'trophy.png')
        f = open(filename, 'r')
        file = SimpleUploadedFile(f.name, f.read(), content_type='image/png')
        f.close()

        form = UploadFileForm(files={
            'path': file,
        })
        form.is_valid()
        print form.errors
        self.assertTrue(form.is_valid())

        review_request = ReviewRequest.objects.get(pk=1)
        file_attachment = form.create(file, review_request)
        self.assertEqual(os.path.basename(file_attachment.file.name),
                         'trophy.png')
        self.assertEqual(file_attachment.mimetype, 'image/png')
