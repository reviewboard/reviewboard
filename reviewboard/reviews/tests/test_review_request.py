from __future__ import unicode_literals

import os

from django.contrib.auth.models import User
from django.utils import six
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.accounts.models import Profile
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.reviews.errors import PublishError
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.scmtools.core import ChangeSet, Commit
from reviewboard.testing import TestCase


class ReviewRequestTests(SpyAgency, TestCase):
    """Tests for ReviewRequest."""
    fixtures = ['test_users']

    def test_public_with_discard_reopen_submitted(self):
        """Testing ReviewRequest.public when discarded, reopened, submitted."""
        review_request = self.create_review_request(publish=True)
        self.assertTrue(review_request.public)

        review_request.close(ReviewRequest.DISCARDED)
        self.assertTrue(review_request.public)

        review_request.reopen()
        self.assertFalse(review_request.public)

        review_request.publish(review_request.submitter)

        review_request.close(ReviewRequest.SUBMITTED)
        self.assertTrue(review_request.public)

    def test_close_removes_commit_id(self):
        """Testing ReviewRequest.close with discarded removes commit ID"""
        review_request = self.create_review_request(publish=True,
                                                    commit_id='123')
        self.assertEqual(review_request.commit_id, '123')
        review_request.close(ReviewRequest.DISCARDED)

        self.assertIsNone(review_request.commit_id)

    def test_changenum_against_changenum_and_commit_id(self):
        """Testing create ReviewRequest with changenum against both changenum
         and commit_id"""
        changenum = 123
        review_request = self.create_review_request(publish=True,
                                                    changenum=changenum)
        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.changenum, changenum)
        self.assertIsNone(review_request.commit_id)

    @add_fixtures(['test_scmtools'])
    def test_changeset_update_commit_id(self):
        """Testing ReviewRequest.changeset_is_pending update commit ID
        behavior
        """
        current_commit_id = '123'
        new_commit_id = '124'
        review_request = self.create_review_request(
            publish=True,
            commit_id=current_commit_id,
            create_repository=True)
        draft = ReviewRequestDraft.create(review_request)
        self.assertEqual(review_request.commit_id, current_commit_id)
        self.assertEqual(draft.commit_id, current_commit_id)

        def _get_fake_changeset(scmtool, commit_id, allow_empty=True):
            self.assertEqual(commit_id, current_commit_id)

            changeset = ChangeSet()
            changeset.pending = False
            changeset.changenum = int(new_commit_id)
            return changeset

        scmtool = review_request.repository.get_scmtool()
        scmtool.supports_pending_changesets = True
        self.spy_on(scmtool.get_changeset,
                    call_fake=_get_fake_changeset)

        self.spy_on(review_request.repository.get_scmtool,
                    call_fake=lambda x: scmtool)

        is_pending, new_commit_id = \
            review_request.changeset_is_pending(current_commit_id)
        self.assertEqual(is_pending, False)
        self.assertEqual(new_commit_id, new_commit_id)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertEqual(review_request.commit_id, new_commit_id)

        draft = review_request.get_draft()
        self.assertEqual(draft.commit_id, new_commit_id)

    def test_unicode_summary_and_str(self):
        """Testing ReviewRequest.__str__ with unicode summaries."""
        review_request = self.create_review_request(
            summary='\u203e\u203e', publish=True)
        self.assertEqual(six.text_type(review_request), '\u203e\u203e')

    def test_discard_unpublished_private(self):
        """Testing ReviewRequest.close with private requests on discard
        to ensure changes from draft are copied over
        """
        review_request = self.create_review_request(
            publish=False,
            public=False)

        self.assertFalse(review_request.public)
        self.assertNotEqual(review_request.status, ReviewRequest.DISCARDED)

        draft = ReviewRequestDraft.create(review_request)

        summary = 'Test summary'
        description = 'Test description'
        testing_done = 'Test testing done'

        draft.summary = summary
        draft.description = description
        draft.testing_done = testing_done
        draft.save()

        review_request.close(ReviewRequest.DISCARDED)

        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)
        self.assertEqual(review_request.testing_done, testing_done)

    def test_discard_unpublished_public(self):
        """Testing ReviewRequest.close with public requests on discard
        to ensure changes from draft are not copied over
        """
        review_request = self.create_review_request(
            publish=False,
            public=True)

        self.assertTrue(review_request.public)
        self.assertNotEqual(review_request.status, ReviewRequest.DISCARDED)

        draft = ReviewRequestDraft.create(review_request)

        summary = 'Test summary'
        description = 'Test description'
        testing_done = 'Test testing done'

        draft.summary = summary
        draft.description = description
        draft.testing_done = testing_done
        draft.save()

        review_request.close(ReviewRequest.DISCARDED)

        self.assertNotEqual(review_request.summary, summary)
        self.assertNotEqual(review_request.description, description)
        self.assertNotEqual(review_request.testing_done, testing_done)

    def test_publish_changedesc_none(self):
        """Testing ReviewRequest.publish on a new request to ensure there are
        no change descriptions
        """
        review_request = self.create_review_request(publish=True)

        review_request.publish(review_request.submitter)

        with self.assertRaises(ChangeDescription.DoesNotExist):
            review_request.changedescs.filter(public=True).latest()

    def test_submit_nonpublic(self):
        """ Testing ReviewRequest.close with non-public requests to ensure state
        transitions to SUBMITTED from non-public review request is not allowed
        """
        review_request = self.create_review_request(public=False)

        with self.assertRaises(PublishError):
            review_request.close(ReviewRequest.SUBMITTED)

    def test_submit_public(self):
        """ Testing ReviewRequest.close with public requests to ensure
        public requests can be transferred to SUBMITTED
        """
        review_request = self.create_review_request(public=True)

        review_request.close(ReviewRequest.SUBMITTED)


class PostCommitTests(SpyAgency, TestCase):
    fixtures = ['test_users', 'test_scmtools']

    def setUp(self):
        super(PostCommitTests, self).setUp()

        self.user = User.objects.create(username='testuser', password='')
        self.profile, is_new = Profile.objects.get_or_create(user=self.user)
        self.profile.save()

        self.testdata_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            '..', 'scmtools', 'testdata')

        self.repository = self.create_repository(tool_name='Test')

    def test_update_from_committed_change(self):
        """Testing post-commit update"""
        commit_id = '4'

        def get_change(repository, commit_to_get):
            self.assertEqual(commit_id, commit_to_get)

            commit = Commit()
            commit.message = \
                'This is my commit message\n\nWith a summary line too.'
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')
            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        def get_file_exists(repository, path, revision, base_commit_id=None,
                            request=None):
            return (path, revision) in [('/readme', 'd6613f5')]

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists, call_fake=get_file_exists)

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.update_from_commit_id(commit_id)

        self.assertEqual(review_request.summary, 'This is my commit message')
        self.assertEqual(review_request.description,
                         'With a summary line too.')

        self.assertEqual(review_request.diffset_history.diffsets.count(), 1)

        diffset = review_request.diffset_history.diffsets.get()
        self.assertEqual(diffset.files.count(), 1)

        fileDiff = diffset.files.get()
        self.assertEqual(fileDiff.source_file, 'readme')
        self.assertEqual(fileDiff.source_revision, 'd6613f5')

    def test_update_from_committed_change_with_rich_text_reset(self):
        """Testing post-commit update from commit resets rich text"""
        def get_change(repository, commit_to_get):
            commit = Commit()
            commit.message = '* This is a summary\n\n* This is a description.'
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')

            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        def get_file_exists(repository, path, revision, base_commit_id=None,
                            request=None):
            return (path, revision) in [('/readme', 'd6613f5')]

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists, call_fake=get_file_exists)

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.description_rich_text = True
        review_request.update_from_commit_id('4')

        self.assertEqual(review_request.summary, '* This is a summary')
        self.assertEqual(review_request.description,
                         '* This is a description.')
        self.assertFalse(review_request.description_rich_text)

    def test_update_from_pending_change_with_rich_text_reset(self):
        """Testing post-commit update from changeset resets rich text"""
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.description_rich_text = True
        review_request.testing_done_rich_text = True

        changeset = ChangeSet()
        changeset.changenum = 4
        changeset.summary = '* This is a summary'
        changeset.description = '* This is a description.'
        changeset.testing_done = '* This is some testing.'
        review_request.update_from_pending_change(4, changeset)

        self.assertEqual(review_request.summary, '* This is a summary')
        self.assertEqual(review_request.description,
                         '* This is a description.')
        self.assertFalse(review_request.description_rich_text)
        self.assertEqual(review_request.testing_done,
                         '* This is some testing.')
        self.assertFalse(review_request.testing_done_rich_text)

    def test_update_from_committed_change_without_repository_support(self):
        """Testing post-commit update failure conditions"""
        self.spy_on(self.repository.__class__.supports_post_commit.fget,
                    call_fake=lambda self: False)
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)

        self.assertRaises(NotImplementedError,
                          lambda: review_request.update_from_commit_id('4'))
