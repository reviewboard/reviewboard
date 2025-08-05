"""Tests for reviewboard.diffviewer.views.DiffFragmentView."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.core.cache import cache

from reviewboard.attachments.models import FileAttachment
from reviewboard.attachments.tests.base import BaseFileAttachmentTestCase
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class ReviewsDiffFragmentViewTests(TestCase):
    """Tests for reviewboard.diffviewer.views.DiffFragmentView."""

    fixtures = ['test_scmtools', 'test_users']

    def test_base_filediff_not_in_diffset(self):
        """Testing ReviewsDiffFragmentView.get with ?base-filediff-id= as a
        FileDiff outside the current diffset
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    create_with_history=True)
        review_request.target_people.add(review_request.submitter)

        diffset = self.create_diffset(review_request, draft=True)
        commit = self.create_diffcommit(diffset=diffset)
        diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        review_request.publish(user=review_request.submitter)

        filediff = commit.files.get()

        other_diffset = self.create_diffset(repository=repository)
        other_filediff = self.create_filediff(diffset=other_diffset)

        rsp = self.client.get(
            local_site_reverse(
                'view-diff-fragment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                    'filediff_id': filediff.pk,
                }),
            data={'base-filediff-id': other_filediff.pk})

        self.assertEqual(rsp.status_code, 404)

    def test_base_filediff_and_interfilediff(self):
        """Testing ReviewsDiffFragmentView.get with interfilediff and
        ?base-filediff-id
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    create_with_history=True)
        review_request.target_people.add(review_request.submitter)

        diffset = self.create_diffset(review_request, draft=True)
        diffset_commits = [
            self.create_diffcommit(diffset=diffset, commit_id='r1',
                                   parent_id='r0'),
            self.create_diffcommit(diffset=diffset, commit_id='r2',
                                   parent_id='r1'),
        ]

        filediff = diffset_commits[1].files.get()
        base_filediff = diffset_commits[0].files.get()

        diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)
        review_request.publish(user=review_request.submitter)

        interdiffset = self.create_diffset(review_request, draft=True)
        interdiffset_commit = self.create_diffcommit(
            diffset=interdiffset, commit_id='r1', parent_id='r0')

        interdiffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)
        review_request.publish(user=review_request.submitter)

        interfilediff = interdiffset_commit.files.get()

        rsp = self.client.get(
            local_site_reverse(
                'view-diff-fragment',
                kwargs={
                    'review_request_id': review_request.display_id,
                    'revision': diffset.revision,
                    'interdiff_revision': interdiffset.revision,
                    'filediff_id': filediff.pk,
                    'interfilediff_id': interfilediff.pk,
                }),
            data={'base-filediff-id': base_filediff.pk})

        self.assertEqual(rsp.status_code, 500)
        self.assertIn(
            b'Cannot generate an interdiff when base FileDiff ID is '
            b'specified.',
            rsp.content)

    def test_base_filediff_not_ancestor(self):
        """Testing ReviewsDiffFragmentView.get with ?base-filediff-id set to a
        FileDiff that is not an ancestor FileDiff
        """
        review_request = self.create_review_request(create_repository=True,
                                                    create_with_history=True)
        review_request.target_people.add(review_request.submitter)
        diffset = self.create_diffset(review_request, draft=True)
        commits = [
            self.create_diffcommit(diffset=diffset, commit_id='r1',
                                   parent_id='r0'),
            self.create_diffcommit(diffset=diffset, commit_id='r2',
                                   parent_id='r1'),
        ]

        base_filediff = commits[0].files.get()
        filediff = commits[1].files.get()

        diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)
        review_request.publish(user=review_request.submitter)

        rsp = self.client.get(
            local_site_reverse(
                'view-diff-fragment',
                kwargs={
                    'revision': diffset.revision,
                    'review_request_id': review_request.display_id,
                    'filediff_id': filediff.pk,
                }),
            data={'base-filediff-id': base_filediff.pk})

        self.assertEqual(rsp.status_code, 500)
        self.assertIn(
            b'The requested FileDiff (ID %d) is not a valid base FileDiff '
            b'for FileDiff %d.'
            % (base_filediff.pk, filediff.pk),
            rsp.content)


class ReviewsFileAttachmentDiffFragmentViewTests(BaseFileAttachmentTestCase):
    """Tests for inline diff file attachments in the diff viewer.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    def setUp(self):
        """Set up this test case."""
        super().setUp()

        # The diff viewer's caching breaks the result of these tests,
        # so be sure we clear before each one.
        cache.clear()

    def test_added_file(self):
        """Testing inline diff file attachments with newly added files"""
        # Set up the initial state.
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(submitter=user,
                                                    target_people=[user])
        filediff = self.make_filediff(
            is_new=True,
            diffset_history=review_request.diffset_history)

        # Create a diff file attachment to be displayed inline.
        diff_file_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            orig_filename='my-file',
            file=self.make_uploaded_file(),
            mimetype='image/png')
        review_request.file_attachments.add(diff_file_attachment)
        review_request.save()
        review_request.publish(user)

        # Load the diff viewer.
        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/diff/1/fragment/%s/'
                                   % (review_request.pk, filediff.pk))
        self.assertEqual(response.status_code, 200)

        # The file attachment should appear as the right-hand side
        # file attachment in the diff viewer.
        self.assertEqual(response.context['orig_diff_file_attachment'], None)
        self.assertEqual(response.context['modified_diff_file_attachment'],
                         diff_file_attachment)

    def test_modified_file(self):
        """Testing inline diff file attachments with modified files"""
        # Set up the initial state.
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(submitter=user)
        filediff = self.make_filediff(
            is_new=False,
            diffset_history=review_request.diffset_history)
        self.assertFalse(filediff.is_new)

        # Create diff file attachments to be displayed inline.
        uploaded_file = self.make_uploaded_file()

        orig_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            orig_filename='my-file',
            file=uploaded_file,
            mimetype='image/png',
            from_modified=False)
        modified_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            orig_filename='my-file',
            file=uploaded_file,
            mimetype='image/png')
        review_request.file_attachments.add(orig_attachment)
        review_request.file_attachments.add(modified_attachment)
        review_request.publish(user)

        # Load the diff viewer.
        self.client.login(username='doc', password='doc')
        response = self.client.get('/r/%d/diff/1/fragment/%s/'
                                   % (review_request.pk, filediff.pk))
        self.assertEqual(response.status_code, 200)

        # The file attachment should appear as the right-hand side
        # file attachment in the diff viewer.
        self.assertEqual(response.context['orig_diff_file_attachment'],
                         orig_attachment)
        self.assertEqual(response.context['modified_diff_file_attachment'],
                         modified_attachment)

    def test_etag_match(self) -> None:
        """Testing ETag generation for binary file fragment with comments"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(submitter=user)
        filediff = self.make_filediff(
            is_new=False,
            diffset_history=review_request.diffset_history)

        # Create file attachments for the binary file.
        uploaded_file = self.make_uploaded_file()
        orig_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            orig_filename='binary-file.png',
            file=uploaded_file,
            mimetype='image/png',
            from_modified=False)
        modified_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            orig_filename='binary-file.png',
            file=uploaded_file,
            mimetype='image/png')
        review_request.file_attachments.add(orig_attachment)
        review_request.file_attachments.add(modified_attachment)
        review_request.publish(user)

        # Create a review with file attachment comment.
        review = self.create_review(
            review_request=review_request,
            user=user,
            public=True)

        self.create_file_attachment_comment(
            review=review,
            file_attachment=modified_attachment,
            diff_against_file_attachment=orig_attachment)

        # Request the fragment.
        url = f'/r/{review_request.pk}/diff/1/fragment/{filediff.pk}/'

        self.client.login(username='doc', password='doc')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        etag = response.headers['ETag']

        # Fetch the fragment again with the same ETag. We should get a 304.
        response = self.client.get(url, headers={'If-None-Match': etag})
        self.assertEqual(response.status_code, 304)

    def test_etag_new_comments(self) -> None:
        """Testing ETag updates for binary file fragment with newly-added
        comments
        """
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(submitter=user)
        filediff = self.make_filediff(
            is_new=False,
            diffset_history=review_request.diffset_history)

        # Create file attachments for the binary file.
        uploaded_file = self.make_uploaded_file()
        orig_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            orig_filename='binary-file.png',
            file=uploaded_file,
            mimetype='image/png',
            from_modified=False)
        modified_attachment = FileAttachment.objects.create_from_filediff(
            filediff,
            orig_filename='binary-file.png',
            file=uploaded_file,
            mimetype='image/png')
        review_request.file_attachments.add(orig_attachment)
        review_request.file_attachments.add(modified_attachment)
        review_request.publish(user)

        # Create a review with file attachment comment.
        review = self.create_review(
            review_request=review_request,
            user=user)

        self.create_file_attachment_comment(
            review=review,
            file_attachment=modified_attachment,
            diff_against_file_attachment=orig_attachment)

        # Request the fragment.
        url = f'/r/{review_request.pk}/diff/1/fragment/{filediff.pk}/'

        self.client.login(username='doc', password='doc')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        etag = response.headers['ETag']

        # Create a new comment.
        self.create_file_attachment_comment(
            review=review,
            file_attachment=modified_attachment,
            diff_against_file_attachment=orig_attachment)

        # Fetch the fragment again with the same ETag. We should now get a 200
        # instead of a 304.
        response = self.client.get(url, headers={'If-None-Match': etag})
        self.assertEqual(response.status_code, 200)
