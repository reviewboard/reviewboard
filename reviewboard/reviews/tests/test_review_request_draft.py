from __future__ import unicode_literals

from reviewboard.reviews.fields import (BaseEditableField,
                                        BaseTextAreaField,
                                        get_review_request_fieldset)
from reviewboard.reviews.models import ReviewRequestDraft
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
