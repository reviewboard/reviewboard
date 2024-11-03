"""Unit tests for reviewboard.attachments.managers.FileAttachmentManager.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

from django.contrib.auth.models import User

from reviewboard.attachments.models import FileAttachment
from reviewboard.attachments.tests.base import BaseFileAttachmentTestCase


class FileAttachmentManagerTests(BaseFileAttachmentTestCase):
    """Unit tests for reviewboard.attachments.managers.FileAttachmentManager.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def test_create_from_filediff_sets_relation_counter(self):
        """Testing FileAttachmentManager.create_from_filediff sets
        ReviewRequest.file_attachment_count counter
        """
        user = User.objects.get(username='doc')
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository,
                                                    submitter=user)
        diffset_history = review_request.diffset_history

        filediff = self.make_filediff(diffset_history=diffset_history)

        self.assertEqual(review_request.file_attachments_count, 0)

        FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')

        review_request.refresh_from_db()
        self.assertEqual(review_request.file_attachments_count, 1)

    def test_create_from_filediff_with_new_and_modified_true(self):
        """Testing FileAttachmentManager.create_from_filediff
        with new FileDiff and modified=True
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')
        self.assertEqual(file_attachment.repository_id, None)
        self.assertEqual(file_attachment.repo_path, None)
        self.assertEqual(file_attachment.repo_revision, None)
        self.assertEqual(file_attachment.added_in_filediff, filediff)

    def test_create_from_filediff_with_new_and_modified_false(self):
        """Testing FileAttachmentManager.create_from_filediff
        with new FileDiff and modified=False
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        self.assertRaises(
            AssertionError,
            FileAttachment.objects.create_from_filediff,
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png',
            from_modified=False)

    def test_create_from_filediff_with_existing_and_modified_true(self):
        """Testing FileAttachmentManager.create_from_filediff
        with existing FileDiff and modified=True
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')
        self.assertIsNone(file_attachment.repository_id)
        self.assertIsNone(file_attachment.repo_path)
        self.assertIsNone(file_attachment.repo_revision)
        self.assertEqual(file_attachment.added_in_filediff, filediff)

    def test_create_from_filediff_with_existing_and_modified_false(self):
        """Testing FileAttachmentManager.create_from_filediff
        with existing FileDiff and modified=False
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png',
            from_modified=False)
        self.assertEqual(file_attachment.repository, filediff.get_repository())
        self.assertEqual(file_attachment.repo_path, filediff.source_file)
        self.assertEqual(file_attachment.repo_revision,
                         filediff.source_revision)
        self.assertEqual(file_attachment.added_in_filediff_id, None)

    def test_get_for_filediff_with_new_and_modified_true(self):
        """Testing FileAttachmentManager.get_for_filediff
        with new FileDiff and modified=True
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=True),
            file_attachment)

    def test_get_for_filediff_with_new_and_modified_false(self):
        """Testing FileAttachmentManager.get_for_filediff
        with new FileDiff and modified=False
        """
        filediff = self.make_filediff(is_new=True)
        self.assertTrue(filediff.is_new)

        FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=False),
            None)

    def test_get_for_filediff_with_existing_and_modified_true(self):
        """Testing FileAttachmentManager.get_for_filediff
        with existing FileDiff and modified=True
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png')

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=True),
            file_attachment)

    def test_get_for_filediff_with_existing_and_modified_false(self):
        """Testing FileAttachmentManager.get_for_filediff
        with existing FileDiff and modified=False
        """
        filediff = self.make_filediff()
        self.assertFalse(filediff.is_new)

        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            file=self.make_uploaded_file(),
            mimetype='image/png',
            from_modified=False)

        self.assertEqual(
            FileAttachment.objects.get_for_filediff(filediff, modified=False),
            file_attachment)
