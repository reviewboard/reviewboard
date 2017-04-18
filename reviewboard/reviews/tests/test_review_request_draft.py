from __future__ import unicode_literals

import os

from django.contrib.auth.models import User
from kgb import SpyAgency

from reviewboard.accounts.models import Profile
from reviewboard.reviews.fields import (BaseEditableField,
                                        BaseTextAreaField,
                                        get_review_request_fieldset)
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.scmtools.core import ChangeSet, Commit
from reviewboard.testing import TestCase


class ReviewRequestDraftTests(TestCase):
    """Unit tests for reviewboard.reviews.models.ReviewRequestDraft."""

    fixtures = ['test_users', 'test_scmtools']

    def test_draft_changes(self):
        """Testing recording of draft changes"""
        draft = self._get_draft()
        review_request = draft.review_request

        old_summary = review_request.summary
        old_description = review_request.description
        old_testing_done = review_request.testing_done
        old_branch = review_request.branch
        old_bugs = review_request.get_bug_list()

        draft.summary = 'New summary'
        draft.description = 'New description'
        draft.testing_done = 'New testing done'
        draft.branch = 'New branch'
        draft.bugs_closed = '12, 34, 56'

        new_bugs = draft.get_bug_list()

        changes = draft.publish()
        fields = changes.fields_changed

        self.assertIn('summary', fields)
        self.assertIn('description', fields)
        self.assertIn('testing_done', fields)
        self.assertIn('branch', fields)
        self.assertIn('bugs_closed', fields)

        old_bugs_norm = set([(bug,) for bug in old_bugs])
        new_bugs_norm = set([(bug,) for bug in new_bugs])

        self.assertEqual(fields['summary']['old'][0], old_summary)
        self.assertEqual(fields['summary']['new'][0], draft.summary)
        self.assertEqual(fields['description']['old'][0], old_description)
        self.assertEqual(fields['description']['new'][0], draft.description)
        self.assertEqual(fields['testing_done']['old'][0], old_testing_done)
        self.assertEqual(fields['testing_done']['new'][0], draft.testing_done)
        self.assertEqual(fields['branch']['old'][0], old_branch)
        self.assertEqual(fields['branch']['new'][0], draft.branch)
        self.assertEqual(set(fields['bugs_closed']['old']), old_bugs_norm)
        self.assertEqual(set(fields['bugs_closed']['new']), new_bugs_norm)
        self.assertEqual(set(fields['bugs_closed']['removed']), old_bugs_norm)
        self.assertEqual(set(fields['bugs_closed']['added']), new_bugs_norm)

    def test_draft_changes_with_custom_fields(self):
        """Testing ReviewRequestDraft.publish with custom fields propagating
        from draft to review request
        """
        class RichField(BaseTextAreaField):
            field_id = 'rich_field'

        class SpecialRichField(BaseTextAreaField):
            # Exercise special case field name 'text'
            field_id = 'text'

        class BasicField(BaseEditableField):
            field_id = 'basic_field'

        fieldset = get_review_request_fieldset('main')
        fieldset.add_field(RichField)
        fieldset.add_field(SpecialRichField)
        fieldset.add_field(BasicField)

        try:
            draft = self._get_draft()
            review_request = draft.review_request

            draft.description = 'New description'
            draft.extra_data['rich_field'] = '**Rich custom text**'
            draft.extra_data['rich_field_text_type'] = 'markdown'
            draft.extra_data['text'] = 'Nothing special'
            draft.extra_data['text_type'] = 'plain'
            draft.extra_data['basic_field'] = 'Basic text'

            draft.publish()

            self.assertNotIn('description_text_type',
                             review_request.extra_data)
            self.assertIn('rich_field', review_request.extra_data)
            self.assertIn('rich_field_text_type', review_request.extra_data)
            self.assertIn('text', review_request.extra_data)
            self.assertIn('text_type', review_request.extra_data)
            self.assertIn('basic_field', review_request.extra_data)
            self.assertNotIn('basic_field_text_type',
                             review_request.extra_data)

            self.assertEqual(review_request.description, draft.description)
            self.assertEqual(review_request.extra_data['rich_field'],
                             draft.extra_data['rich_field'])
            self.assertEqual(review_request.extra_data['rich_field_text_type'],
                             draft.extra_data['rich_field_text_type'])
            self.assertEqual(review_request.extra_data['text'],
                             draft.extra_data['text'])
            self.assertEqual(review_request.extra_data['text_type'],
                             draft.extra_data['text_type'])
            self.assertEqual(review_request.extra_data['basic_field'],
                             draft.extra_data['basic_field'])
        finally:
            fieldset.remove_field(RichField)
            fieldset.remove_field(SpecialRichField)
            fieldset.remove_field(BasicField)

    def _get_draft(self):
        """Convenience function for getting a new draft to work with."""
        review_request = self.create_review_request(publish=True)
        return ReviewRequestDraft.create(review_request)


class PostCommitTests(SpyAgency, TestCase):
    """Unit tests for post-commit support in ReviewRequestDraft."""

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
        """Testing ReviewRequestDraft.update_from_commit_id with committed
        change
        """
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

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists)

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        draft = ReviewRequestDraft.create(review_request)
        draft.update_from_commit_id(commit_id)

        self.assertFalse(self.repository.get_file_exists.called)
        self.assertEqual(review_request.summary, '')
        self.assertEqual(review_request.description, '')
        self.assertEqual(draft.summary, 'This is my commit message')
        self.assertEqual(draft.description, 'With a summary line too.')

        self.assertEqual(review_request.diffset_history.diffsets.count(), 0)
        self.assertIsNotNone(draft.diffset)

        self.assertEqual(draft.diffset.files.count(), 1)

        filediff = draft.diffset.files.get()
        self.assertEqual(filediff.source_file, 'readme')
        self.assertEqual(filediff.source_revision, 'd6613f5')

    def test_update_from_committed_change_with_rich_text_reset(self):
        """Testing ReviewRequestDraft.update_from_commit_id resets rich text
        fields
        """
        def get_change(repository, commit_to_get):
            commit = Commit()
            commit.message = '* This is a summary\n\n* This is a description.'
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')

            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        self.spy_on(self.repository.get_change, call_fake=get_change)
        self.spy_on(self.repository.get_file_exists)

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        draft = ReviewRequestDraft.create(review_request)

        draft.description_rich_text = True
        draft.update_from_commit_id('4')

        self.assertFalse(self.repository.get_file_exists.called)
        self.assertEqual(draft.summary, '* This is a summary')
        self.assertEqual(draft.description, '* This is a description.')
        self.assertFalse(draft.description_rich_text)
        self.assertFalse(review_request.description_rich_text)

    def test_update_from_pending_change_with_rich_text_reset(self):
        """Testing ReviewRequestDraft.update_from_pending_change resets rich
        text fields
        """
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        draft = ReviewRequestDraft.create(review_request)

        draft.description_rich_text = True
        draft.testing_done_rich_text = True

        changeset = ChangeSet()
        changeset.changenum = 4
        changeset.summary = '* This is a summary'
        changeset.description = '* This is a description.'
        changeset.testing_done = '* This is some testing.'
        draft.update_from_pending_change(4, changeset)

        self.assertEqual(draft.summary, '* This is a summary')
        self.assertEqual(draft.description, '* This is a description.')
        self.assertFalse(draft.description_rich_text)
        self.assertEqual(draft.testing_done, '* This is some testing.')
        self.assertFalse(draft.testing_done_rich_text)

    def test_update_from_committed_change_without_repository_support(self):
        """Testing ReviewRequestDraft.update_from_commit_id without
        supports_post_commmit for repository
        """
        self.spy_on(self.repository.__class__.supports_post_commit.fget,
                    call_fake=lambda self: False)
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        draft = ReviewRequestDraft.create(review_request)

        with self.assertRaises(NotImplementedError):
            draft.update_from_commit_id('4')
