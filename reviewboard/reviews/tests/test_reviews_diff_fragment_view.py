"""Tests for reviewboard.diffviewer.views.DiffFragmentView."""

from __future__ import unicode_literals

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
        review_request.target_people = [review_request.submitter]

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
        review_request.target_people = [review_request.submitter]

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
        review_request.target_people = [review_request.submitter]
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
