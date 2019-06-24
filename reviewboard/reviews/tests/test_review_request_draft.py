from __future__ import unicode_literals

import os

from django.contrib.auth.models import User
from djblets.features.testing import override_feature_check
from kgb import SpyAgency

from reviewboard.accounts.models import Profile
from reviewboard.attachments.models import FileAttachment
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.features import dvcs_feature
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

    def test_create_with_new_draft(self):
        """Testing ReviewRequestDraft.create with new draft"""
        user1 = User.objects.create(username='reviewer1')
        user2 = User.objects.create(username='reviewer2')

        group1 = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')

        dep_review_request_1 = self.create_review_request(publish=True)
        dep_review_request_2 = self.create_review_request(publish=True)

        review_request = self.create_review_request(
            publish=True,
            bugs_closed='1,20,300',
            commit_id='abc123',
            description_rich_text=True,
            depends_on=[dep_review_request_1, dep_review_request_2],
            rich_text=True,
            target_groups=[group1, group2],
            target_people=[user1, user2],
            testing_done_rich_text=True,
            extra_data={
                'key': {
                    'values': [1, 2, 3],
                },
                'mybool': True,
            })

        active_file_attachment_1 = self.create_file_attachment(review_request)
        active_file_attachment_2 = self.create_file_attachment(review_request)
        inactive_file_attachment = self.create_file_attachment(review_request,
                                                               active=False)

        active_screenshot_1 = self.create_screenshot(review_request)
        active_screenshot_2 = self.create_screenshot(review_request)
        inactive_screenshot = self.create_screenshot(review_request,
                                                     active=False)

        # Create the draft.
        draft = ReviewRequestDraft.create(review_request)

        # Make sure all the fields are the same.
        self.assertEqual(draft.branch, review_request.branch)
        self.assertEqual(draft.bugs_closed, review_request.bugs_closed)
        self.assertEqual(draft.commit_id, review_request.commit_id)
        self.assertEqual(draft.description, review_request.description)
        self.assertEqual(draft.description_rich_text,
                         review_request.description_rich_text)
        self.assertEqual(draft.extra_data, review_request.extra_data)
        self.assertEqual(draft.rich_text, review_request.rich_text)
        self.assertEqual(draft.summary, review_request.summary)
        self.assertEqual(draft.testing_done, review_request.testing_done)
        self.assertEqual(draft.testing_done_rich_text,
                         review_request.testing_done_rich_text)

        self.assertEqual(list(draft.depends_on.order_by('pk')),
                         [dep_review_request_1, dep_review_request_2])
        self.assertEqual(list(draft.target_groups.all()),
                         [group1, group2])
        self.assertEqual(list(draft.target_people.all()),
                         [user1, user2])
        self.assertEqual(list(draft.file_attachments.all()),
                         [active_file_attachment_1, active_file_attachment_2])
        self.assertEqual(list(draft.inactive_file_attachments.all()),
                         [inactive_file_attachment])
        self.assertEqual(list(draft.screenshots.all()),
                         [active_screenshot_1, active_screenshot_2])
        self.assertEqual(list(draft.inactive_screenshots.all()),
                         [inactive_screenshot])

        self.assertIsNotNone(draft.changedesc)

    def test_create_with_new_draft_and_custom_changedesc(self):
        """Testing ReviewRequestDraft.create with new draft and custom
        ChangeDescription
        """
        review_request = self.create_review_request(
            publish=True,
            bugs_closed='1,20,300',
            commit_id='abc123',
            description_rich_text=True,
            rich_text=True,
            testing_done_rich_text=True,
            extra_data={
                'key': {
                    'values': [1, 2, 3],
                },
                'mybool': True,
            })

        # Create the draft.
        changedesc = ChangeDescription.objects.create()
        orig_draft = ReviewRequestDraft.create(review_request,
                                               changedesc=changedesc)

        self.assertEqual(orig_draft.changedesc_id, changedesc.pk)
        self.assertEqual(ChangeDescription.objects.count(), 1)

        # Reload to be sure.
        draft = ReviewRequestDraft.objects.get(pk=orig_draft.pk)
        self.assertEqual(orig_draft, draft)
        self.assertEqual(draft.changedesc, changedesc)

    def test_create_with_existing_new_draft(self):
        """Testing ReviewRequestDraft.create with existing draft"""
        review_request = self.create_review_request(
            publish=True,
            bugs_closed='1,20,300',
            commit_id='abc123',
            description_rich_text=True,
            rich_text=True,
            testing_done_rich_text=True,
            extra_data={
                'key': {
                    'values': [1, 2, 3],
                },
                'mybool': True,
            })

        # Create the first draft.
        orig_draft = ReviewRequestDraft.create(review_request)
        self.assertIsNotNone(orig_draft.changedesc)

        # Try to create it again.
        draft = ReviewRequestDraft.create(review_request)
        self.assertIsNotNone(draft.changedesc)

        self.assertEqual(orig_draft, draft)
        self.assertEqual(orig_draft.changedesc, draft.changedesc)

    def test_create_with_existing_new_draft_new_custom_changedesc(self):
        """Testing ReviewRequestDraft.create with existing draft and new
        custom ChangeDescription
        """
        review_request = self.create_review_request(
            publish=True,
            bugs_closed='1,20,300',
            commit_id='abc123',
            description_rich_text=True,
            rich_text=True,
            testing_done_rich_text=True,
            extra_data={
                'key': {
                    'values': [1, 2, 3],
                },
                'mybool': True,
            })

        # Create the first draft.
        orig_draft = ReviewRequestDraft.create(review_request)
        self.assertIsNotNone(orig_draft.changedesc)

        # Try to create it again.
        new_changedesc = ChangeDescription.objects.create()
        draft = ReviewRequestDraft.create(review_request,
                                          changedesc=new_changedesc)

        self.assertEqual(orig_draft, draft)
        self.assertEqual(draft.changedesc, new_changedesc)

        # Reload to be sure.
        draft = ReviewRequestDraft.objects.get(pk=draft.pk)
        self.assertEqual(orig_draft, draft)
        self.assertEqual(draft.changedesc, new_changedesc)

        # Make sure we've deleted the old ChangeDescription.
        self.assertEqual(list(ChangeDescription.objects.all()),
                         [new_changedesc])

    def test_create_with_existing_new_draft_existing_custom_changedesc(self):
        """Testing ReviewRequestDraft.create with existing draft and existing
        custom ChangeDescription
        """
        review_request = self.create_review_request(
            publish=True,
            bugs_closed='1,20,300',
            commit_id='abc123',
            description_rich_text=True,
            rich_text=True,
            testing_done_rich_text=True,
            extra_data={
                'key': {
                    'values': [1, 2, 3],
                },
                'mybool': True,
            })

        # Create the first draft.
        orig_draft = ReviewRequestDraft.create(review_request)
        orig_changedesc = orig_draft.changedesc
        self.assertIsNotNone(orig_changedesc)

        # Try to create it again.
        draft = ReviewRequestDraft.create(review_request,
                                          changedesc=orig_changedesc)

        self.assertEqual(orig_draft, draft)
        self.assertEqual(draft.changedesc, orig_changedesc)

        # Reload to be sure.
        draft = ReviewRequestDraft.objects.get(pk=draft.pk)
        self.assertEqual(orig_draft, draft)
        self.assertEqual(draft.changedesc, orig_changedesc)

        # Make sure we have not created any new ChangeDescription in the
        # database.
        self.assertEqual(list(ChangeDescription.objects.all()),
                         [orig_changedesc])

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

        target_person = User.objects.get(username='doc')

        draft.description = 'New description'
        draft.testing_done = 'New testing done'
        draft.branch = 'New branch'
        draft.bugs_closed = '12, 34, 56'
        draft.target_people = [target_person]
        # Summary is set by default in create_review_request
        draft.summary = ''

        error_message = 'The draft must have a summary.'

        with self.assertRaisesMessage(PublishError, error_message):
            draft.publish()

    def test_publish_without_description(self):
        """Testing publish when there isn't a description"""
        review_request = self.create_review_request()
        draft = ReviewRequestDraft.create(review_request)

        target_person = User.objects.get(username='doc')

        draft.testing_done = 'New testing done'
        draft.branch = 'New branch'
        draft.bugs_closed = '12, 34, 56'
        draft.target_people = [target_person]
        # Description is set by default in create_review_request
        draft.description = ''
        error_message = 'The draft must have a description.'

        with self.assertRaisesMessage(PublishError, error_message):
            draft.publish()

    def test_publish_with_history_no_commits_in_diffset(self):
        """Testing ReviewRequestDraft.publish when the diffset has no commits
        """
        review_request = self.create_review_request(create_with_history=True,
                                                    create_repository=True)
        self.create_diffset(review_request, draft=True)

        target_person = User.objects.get(username='doc')

        draft = review_request.get_draft()
        draft.target_people = [target_person]
        draft.summary = 'Summary'
        draft.description = 'Description'
        draft.save()

        error_msg = 'There are no commits attached to the diff.'

        with self.assertRaisesMessage(PublishError, error_msg):
            draft.publish()

    def test_publish_with_history_diffset_not_finalized(self):
        """Testing ReviewRequestDraft.publish for a review request created with
        commit history support when the diffset has not been finalized
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_with_history=True,
                create_repository=True)
            self.create_diffset(review_request, draft=True)
            draft = review_request.get_draft()

            draft.target_people = [review_request.submitter]

            error_msg = \
                'Error publishing: There are no commits attached to the diff'

            with self.assertRaisesMessage(PublishError, error_msg):
                draft.publish()

    def test_publish_with_history_diffset_finalized(self):
        """Testing ReviewRequestDraft.publish for a review request created with
        commit history support when the diffset has been finalized
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_with_history=True,
                create_repository=True)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            self.create_diffcommit(diffset=diffset)
            diffset.finalize_commit_series(
                cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                validation_info=None,
                validate=False,
                save=True)

            draft = review_request.get_draft()
            draft.target_people = [review_request.submitter]
            draft.publish()

            review_request = ReviewRequest.objects.get(pk=review_request.pk)
            self.assertEqual(review_request.status,
                             ReviewRequest.PENDING_REVIEW)

    def test_publish_without_history_not_finalized(self):
        """Testing ReviewRequestDraft.publish for a review request created
        without commit history support when the diffset has not been finalized
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True)
            diffset = self.create_diffset(review_request, draft=True)
            draft = review_request.get_draft()
            draft.target_people = [review_request.submitter]
            self.create_filediff(diffset=diffset)

            draft.publish()

            review_request = ReviewRequest.objects.get(pk=review_request.pk)
            self.assertEqual(review_request.status,
                             ReviewRequest.PENDING_REVIEW)

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
        self.profile = self.user.get_profile()

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
                                    'With a summary line too.',
                            diff=self.DEFAULT_GIT_README_DIFF)

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
                message='* This is a summary\n\n* This is a description.',
                diff=self.DEFAULT_GIT_README_DIFF)

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
        scmtool_cls = type(self.repository.get_scmtool())

        old_supports_post_commit = scmtool_cls.supports_post_commit
        scmtool_cls.supports_post_commit = False

        try:
            review_request = ReviewRequest.objects.create(self.user,
                                                          self.repository)
            draft = ReviewRequestDraft.create(review_request)

            with self.assertRaises(NotImplementedError):
                draft.update_from_commit_id('4')
        finally:
            scmtool_cls.supports_post_commit = old_supports_post_commit
