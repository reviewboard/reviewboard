"""Base support for file attachment unit tests.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.testing import TestCase


class BaseFileAttachmentTestCase(TestCase):
    """Base support for file attachment unit tests.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def make_uploaded_file(self):
        """Create a return a file to use for mocking in forms."""
        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'logo.png')

        with open(filename, 'rb') as fp:
            uploaded_file = SimpleUploadedFile(fp.name, fp.read(),
                                               content_type='image/png')

        return uploaded_file

    def make_filediff(self, is_new=False, diffset_history=None,
                      diffset_revision=1, source_filename='file1',
                      dest_filename='file2'):
        """Create and return a FileDiff with the given data."""
        if is_new:
            source_revision = PRE_CREATION
            dest_revision = ''
        else:
            source_revision = '1'
            dest_revision = '2'

        repository = self.create_repository()

        if not diffset_history:
            user = User.objects.get(username='doc')
            review_request = self.create_review_request(repository=repository,
                                                        submitter=user)
            diffset_history = review_request.diffset_history

        diffset = DiffSet.objects.create(name='test',
                                         revision=diffset_revision,
                                         repository=repository,
                                         history=diffset_history)
        filediff = FileDiff(source_file=source_filename,
                            source_revision=source_revision,
                            dest_file=dest_filename,
                            dest_detail=dest_revision,
                            diffset=diffset,
                            binary=True)
        filediff.save()

        return filediff
