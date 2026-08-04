"""Base support for file attachment unit tests.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from reviewboard.diffviewer.models import DiffSetHistory
    from reviewboard.scmtools.core import Revision


class BaseFileAttachmentTestCase(TestCase):
    """Base support for file attachment unit tests.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    DEFINED_LOCAL_SITE_KEY = FileAttachment.DEFINED_LOCAL_SITE_KEY

    def make_uploaded_file(self) -> SimpleUploadedFile:
        """Create a return a file to use for mocking in forms."""
        filename = os.path.join(settings.STATIC_ROOT,
                                'rb', 'images', 'logo.png')

        with open(filename, 'rb') as fp:
            uploaded_file = SimpleUploadedFile(fp.name, fp.read(),
                                               content_type='image/png')

        return uploaded_file

    def make_filediff(
        self,
        *,
        is_new: bool = False,
        diffset_history: (DiffSetHistory | None) = None,
        diffset_revision: int = 1,
        source_filename: str = 'file1',
        dest_filename: str = 'file2',
        with_local_site: bool = False,
    ) -> FileDiff:
        """Create and return a FileDiff with the given data.

        Version Changed:
            8.1:
            Made arguments keyword only and added ``with_local_site``.

        Args:
            is_new (bool, optional):
                Whether the FileDiff is new.

            diffset_history (reviewboard.diffviewer.models.DiffSetHistory,
                             optional):
                The optional diffset history to set.

            diffset_revision (int, optional)):
                The revision of the diffset.

            source_filename (str, optional)):
                The name of the source file.

            dest_filename (str, optional)):
                The name of the destination file.

            with_local_site (bool, optional):
                Whether to create the repository using a Local Site. This
                will choose one based on :py:attr:`local_site_name`.

                Version Added:
                    8.1
        """
        source_revision: Revision | str
        dest_revision: Revision | str

        if is_new:
            source_revision = PRE_CREATION
            dest_revision = ''
        else:
            source_revision = '1'
            dest_revision = '2'

        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        repository = self.create_repository(local_site=local_site)

        if not diffset_history:
            user = User.objects.get(username='doc')
            review_request = self.create_review_request(repository=repository,
                                                        submitter=user,
                                                        local_site=local_site)
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
