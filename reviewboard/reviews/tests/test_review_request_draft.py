from __future__ import unicode_literals

import os

from django.contrib.auth.models import User
from kgb import SpyAgency

from reviewboard.accounts.models import Profile
from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.errors import PublishError
from reviewboard.reviews.fields import (BaseEditableField,
                                        BaseTextAreaField,
                                        get_review_request_fieldset)
from reviewboard.reviews.models import (ReviewRequest, ReviewRequestDraft,
                                        Screenshot)
from reviewboard.scmtools.core import ChangeSet, Commit
from reviewboard.testing import TestCase


class ReviewRequestDraftTests(TestCase):
    """Unit tests for reviewboard.reviews.models.ReviewRequestDraft."""

    fixtures = ['test_users', 'test_scmtools']

    def test_publish_records_fields(self):
        """Testing ReviewRequestDraft.publish records changes"""
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
        draft.target_people.add(review_request.submitter)

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

    def test_publish_with_add_first_file_attachment(self):
        """Testing ReviewRequestDraft.publish with adding first file
        attachment
        """
        draft = self._get_draft()
        draft.target_people = [User.objects.create_user(username='testuser')]
        review_request = draft.review_request
        self.assertEqual(draft.file_attachments_count, 0)
        self.assertEqual(draft.inactive_file_attachments_count, 0)
        self.assertEqual(review_request.file_attachments_count, 0)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

        attachment = self.create_file_attachment(review_request,
                                                 draft=draft,
                                                 caption='',
                                                 draft_caption='Test Caption')
        self.assertEqual(draft.file_attachments_count, 1)
        self.assertEqual(draft.inactive_file_attachments_count, 0)
        self.assertEqual(review_request.file_attachments_count, 0)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

        changes = draft.publish()

        attachment = FileAttachment.objects.get(pk=attachment.pk)
        self.assertEqual(attachment.caption, 'Test Caption')

        fields = changes.fields_changed

        self.assertEqual(fields['files'], {
            'new': [
                (attachment.display_name,
                 attachment.get_absolute_url(),
                 attachment.pk)
            ],
            'added': [
                (attachment.display_name,
                 attachment.get_absolute_url(),
                 attachment.pk)
            ],
            'old': [],
            'removed': [],
        })
        self.assertEqual(review_request.file_attachments_count, 1)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

    def test_publish_with_add_another_file_attachment(self):
        """Testing ReviewRequestDraft.publish with adding another file
        attachment
        """
        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(target_people=[user])
        attachment1 = self.create_file_attachment(review_request,
                                                  caption='File 1')
        review_request.publish(review_request.submitter)

        draft = ReviewRequestDraft.create(review_request)
        self.assertEqual(draft.file_attachments_count, 1)
        self.assertEqual(draft.inactive_file_attachments_count, 0)
        self.assertEqual(review_request.file_attachments_count, 1)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

        attachment2 = self.create_file_attachment(review_request,
                                                  caption='File 2',
                                                  draft_caption='New File 2',
                                                  draft=draft)
        self.assertEqual(draft.file_attachments_count, 2)
        self.assertEqual(draft.inactive_file_attachments_count, 0)
        self.assertEqual(review_request.file_attachments_count, 1)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

        changes = draft.publish()

        attachment1 = FileAttachment.objects.get(pk=attachment1.pk)
        self.assertEqual(attachment1.caption, 'File 1')

        attachment2 = FileAttachment.objects.get(pk=attachment2.pk)
        self.assertEqual(attachment2.caption, 'New File 2')

        fields = changes.fields_changed

        self.assertEqual(fields['files'], {
            'new': [
                (attachment1.display_name,
                 attachment1.get_absolute_url(),
                 attachment1.pk),
                (attachment2.display_name,
                 attachment2.get_absolute_url(),
                 attachment2.pk),
            ],
            'added': [
                (attachment2.display_name,
                 attachment2.get_absolute_url(),
                 attachment2.pk),
            ],
            'old': [
                (attachment1.display_name,
                 attachment1.get_absolute_url(),
                 attachment1.pk),
            ],
            'removed': [],
        })
        self.assertEqual(review_request.file_attachments_count, 2)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

    def test_publish_with_delete_file_attachment(self):
        """Testing ReviewRequestDraft.publish with deleting a file attachment
        """
        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(target_people=[user])
        attachment = self.create_file_attachment(review_request,
                                                 caption='File 1')
        review_request.publish(review_request.submitter)

        draft = ReviewRequestDraft.create(review_request)
        self.assertEqual(draft.file_attachments_count, 1)
        self.assertEqual(draft.inactive_file_attachments_count, 0)
        self.assertEqual(review_request.file_attachments_count, 1)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

        draft.file_attachments.remove(attachment)
        draft.inactive_file_attachments.add(attachment)

        self.assertEqual(draft.file_attachments_count, 0)
        self.assertEqual(draft.inactive_file_attachments_count, 1)
        self.assertEqual(review_request.file_attachments_count, 1)
        self.assertEqual(review_request.inactive_file_attachments_count, 0)

        changes = draft.publish()
        fields = changes.fields_changed

        self.assertEqual(fields['files'], {
            'new': [],
            'added': [],
            'old': [
                (attachment.display_name,
                 attachment.get_absolute_url(),
                 attachment.pk),
            ],
            'removed': [
                (attachment.display_name,
                 attachment.get_absolute_url(),
                 attachment.pk),
            ],
        })
        self.assertEqual(review_request.file_attachments_count, 0)
        self.assertEqual(review_request.inactive_file_attachments_count, 1)

    def test_publish_with_add_first_screenshot(self):
        """Testing ReviewRequestDraft.publish with adding first screenshot"""
        draft = self._get_draft()
        draft.target_people = [User.objects.create_user(username='testuser')]
        review_request = draft.review_request

        self.assertEqual(draft.screenshots_count, 0)
        self.assertEqual(draft.inactive_screenshots_count, 0)
        self.assertEqual(review_request.screenshots_count, 0)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

        screenshot = self.create_screenshot(review_request,
                                            draft=draft,
                                            caption='',
                                            draft_caption='New Caption')
        self.assertEqual(draft.screenshots_count, 1)
        self.assertEqual(draft.inactive_screenshots_count, 0)
        self.assertEqual(review_request.screenshots_count, 0)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

        changes = draft.publish()

        screenshot = Screenshot.objects.get(pk=screenshot.pk)
        self.assertEqual(screenshot.caption, 'New Caption')

        fields = changes.fields_changed

        self.assertEqual(fields['screenshots'], {
            'new': [
                (screenshot.caption,
                 screenshot.get_absolute_url(),
                 screenshot.pk)
            ],
            'added': [
                (screenshot.caption,
                 screenshot.get_absolute_url(),
                 screenshot.pk)
            ],
            'old': [],
            'removed': [],
        })
        self.assertEqual(review_request.screenshots_count, 1)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

    def test_publish_with_add_another_screenshot(self):
        """Testing ReviewRequestDraft.publish with adding another screenshot"""
        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(target_people=[user])
        screenshot1 = self.create_screenshot(review_request,
                                             caption='File 1')
        review_request.publish(review_request.submitter)

        draft = ReviewRequestDraft.create(review_request)
        self.assertEqual(draft.screenshots_count, 1)
        self.assertEqual(draft.inactive_screenshots_count, 0)
        self.assertEqual(review_request.screenshots_count, 1)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

        screenshot2 = self.create_screenshot(review_request,
                                             caption='File 2',
                                             draft_caption='New File 2',
                                             draft=draft)
        self.assertEqual(draft.screenshots_count, 2)
        self.assertEqual(draft.inactive_screenshots_count, 0)
        self.assertEqual(review_request.screenshots_count, 1)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

        changes = draft.publish()

        screenshot1 = Screenshot.objects.get(pk=screenshot1.pk)
        self.assertEqual(screenshot1.caption, 'File 1')

        screenshot2 = Screenshot.objects.get(pk=screenshot2.pk)
        self.assertEqual(screenshot2.caption, 'New File 2')

        fields = changes.fields_changed

        self.assertEqual(fields['screenshots'], {
            'new': [
                (screenshot1.caption,
                 screenshot1.get_absolute_url(),
                 screenshot1.pk),
                (screenshot2.caption,
                 screenshot2.get_absolute_url(),
                 screenshot2.pk),
            ],
            'added': [
                (screenshot2.caption,
                 screenshot2.get_absolute_url(),
                 screenshot2.pk),
            ],
            'old': [
                (screenshot1.caption,
                 screenshot1.get_absolute_url(),
                 screenshot1.pk),
            ],
            'removed': [],
        })
        self.assertEqual(review_request.screenshots_count, 2)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

    def test_publish_with_delete_screenshot(self):
        """Testing ReviewRequestDraft.publish with deleting a screenshot"""
        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(target_people=[user])
        attachment = self.create_screenshot(review_request,
                                            caption='File 1')
        review_request.publish(review_request.submitter)

        draft = ReviewRequestDraft.create(review_request)
        self.assertEqual(draft.screenshots_count, 1)
        self.assertEqual(draft.inactive_screenshots_count, 0)
        self.assertEqual(review_request.screenshots_count, 1)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

        draft.screenshots.remove(attachment)
        draft.inactive_screenshots.add(attachment)

        self.assertEqual(draft.screenshots_count, 0)
        self.assertEqual(draft.inactive_screenshots_count, 1)
        self.assertEqual(review_request.screenshots_count, 1)
        self.assertEqual(review_request.inactive_screenshots_count, 0)

        changes = draft.publish()
        fields = changes.fields_changed

        self.assertEqual(fields['screenshots'], {
            'new': [],
            'added': [],
            'old': [
                (attachment.caption,
                 attachment.get_absolute_url(),
                 attachment.pk),
            ],
            'removed': [
                (attachment.caption,
                 attachment.get_absolute_url(),
                 attachment.pk),
            ],
        })
        self.assertEqual(review_request.screenshots_count, 0)
        self.assertEqual(review_request.inactive_screenshots_count, 1)

    def test_publish_with_custom_fields(self):
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
            draft.target_people.add(review_request.submitter)

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

        self.user = User.objects.create_user(username='testuser', password='',
                                             email='email@example.com')
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

            commit = Commit(message='This is my commit message\n\n'
                                    'With a summary line too.')
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')

            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        draft = ReviewRequestDraft.create(review_request)

        self.spy_on(draft.repository.get_change, call_fake=get_change)
        self.spy_on(draft.repository.get_file_exists)

        draft.update_from_commit_id(commit_id)

        self.assertFalse(draft.repository.get_file_exists.called)
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
            commit = Commit(
                message='* This is a summary\n\n* This is a description.')
            diff_filename = os.path.join(self.testdata_dir, 'git_readme.diff')

            with open(diff_filename, 'r') as f:
                commit.diff = f.read()

            return commit

        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        draft = ReviewRequestDraft.create(review_request)

        self.spy_on(draft.repository.get_change, call_fake=get_change)
        self.spy_on(draft.repository.get_file_exists)

        draft.description_rich_text = True
        draft.update_from_commit_id('4')

        self.assertFalse(draft.repository.get_file_exists.called)
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

    def test_publish_without_reviewer_or_group(self):
        """Testing ReviewRequestDraft.publish when there isn't a reviewer or
        group name"""
        review_request = self.create_review_request()
        draft = ReviewRequestDraft.create(review_request)
        draft.summary = 'New summary'
        draft.description = 'New description'
        draft.testing_done = 'New testing done'
        draft.branch = 'New branch'
        draft.bugs_closed = '12, 34, 56'
        error_message = ('There must be at least one reviewer before this '
                         'review request can be published.')

        with self.assertRaisesMessage(PublishError, error_message):
            draft.publish()

    def test_publish_without_summary(self):
        """Testing publish when there isn't a summary"""

        review_request = self.create_review_request()
        draft = ReviewRequestDraft.create(review_request)

        draft.description = 'New description'
        draft.testing_done = 'New testing done'
        draft.branch = 'New branch'
        draft.bugs_closed = '12, 34, 56'
        draft.target_people = [self.user]
        # Summary is set by default in create_review_request
        draft.summary = ''

        error_message = 'The draft must have a summary.'

        with self.assertRaisesMessage(PublishError, error_message):
            draft.publish()

    def test_publish_without_description(self):
        """Testing publish when there isn't a description"""

        review_request = self.create_review_request()
        draft = ReviewRequestDraft.create(review_request)

        draft.testing_done = 'New testing done'
        draft.branch = 'New branch'
        draft.bugs_closed = '12, 34, 56'
        draft.target_people = [self.user]
        # Description is set by default in create_review_request
        draft.description = ''
        error_message = 'The draft must have a description.'

        with self.assertRaisesMessage(PublishError, error_message):
            draft.publish()
