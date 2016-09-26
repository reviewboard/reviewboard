from __future__ import unicode_literals

from django.contrib import auth
from django.contrib.auth.models import Permission, User
from django.core import mail
from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED
from kgb import SpyAgency

from reviewboard.accounts.backends import AuthBackend
from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.reviews.fields import (BaseEditableField,
                                        BaseTextAreaField,
                                        BaseReviewRequestField,
                                        get_review_request_fieldset)
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.reviews.signals import review_request_published
from reviewboard.webapi.errors import NOTHING_TO_PUBLISH
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    review_request_draft_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import get_review_request_draft_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(SpyAgency, ExtraDataListMixin, ExtraDataItemMixin,
                    BaseWebAPITestCase):
    """Testing the ReviewRequestDraftResource API tests."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/'
    resource = resources.review_request_draft

    def compare_item(self, item_rsp, draft):
        changedesc = draft.changedesc

        self.assertEqual(item_rsp['description'], draft.description)
        self.assertEqual(item_rsp['testing_done'], draft.testing_done)
        self.assertEqual(item_rsp['extra_data'], draft.extra_data)
        self.assertEqual(item_rsp['changedescription'], changedesc.text)

        if changedesc.rich_text:
            self.assertEqual(item_rsp['changedescription_text_type'],
                             'markdown')
        else:
            self.assertEqual(item_rsp['changedescription_text_type'],
                             'plain')

        if draft.description_rich_text:
            self.assertEqual(item_rsp['description_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['description_text_type'], 'plain')

        if draft.testing_done_rich_text:
            self.assertEqual(item_rsp['testing_done_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['testing_done_text_type'], 'plain')

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        ReviewRequestDraft.create(review_request)

        return (get_review_request_draft_url(review_request, local_site_name),
                [review_request])

    def check_delete_result(self, user, review_request):
        self.assertIsNone(review_request.get_draft())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        draft = ReviewRequestDraft.create(review_request)

        return (get_review_request_draft_url(review_request, local_site_name),
                review_request_draft_item_mimetype,
                draft)

    def test_get_with_markdown_and_force_text_type_markdown(self):
        """Testing the GET review-requests/<id>/draft/ API
        with *_text_type=markdown and ?force-text-type=markdown
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='markdown',
            expected_text=r'\# `This` is a **test**')

    def test_get_with_markdown_and_force_text_type_plain(self):
        """Testing the GET review-requests/<id>/draft/ API
        with *_text_type=markdown and ?force-text-type=plain
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='plain',
            expected_text='# `This` is a **test**')

    def test_get_with_markdown_and_force_text_type_html(self):
        """Testing the GET review-requests/<id>/draft/ API
        with *_text_type=markdown and ?force-text-type=html
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='html',
            expected_text='<p># <code>This</code> is a '
                          '<strong>test</strong></p>')

    def test_get_with_plain_and_force_text_type_markdown(self):
        """Testing the GET review-requests/<id>/draft/ API
        with *_text_type=plain and ?force-text-type=markdown
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='markdown',
            expected_text=r'\#<\`This\` is a \*\*test\*\*>')

    def test_get_with_plain_and_force_text_type_plain(self):
        """Testing the GET review-requests/<id>/draft/ API
        with *_text_type=plain and ?force-text-type=plain
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='plain',
            expected_text='#<`This` is a **test**>')

    def test_get_with_plain_and_force_text_type_html(self):
        """Testing the GET review-requests/<id>/draft/ API
        with *_text_type=plain and ?force-text-type=html
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='html',
            expected_text='#&lt;`This` is a **test**&gt;')

    def test_get_with_markdown_and_force_markdown_and_custom_markdown(self):
        """Testing the GET review-requests/<id>/draft/ API with rich text,
        ?force-text-type=raw,markdown, and custom field that supports markdown
        """
        self._test_get_with_custom_and_force(
            source_text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='markdown',
            expected_text=r'\# `This` is a **test**',
            custom_field_supports_markdown=True)

    def test_get_with_markdown_and_force_plain_and_custom_markdown(self):
        """Testing the GET review-requests/<id>/draft/ API with rich text,
        ?force-text-type=raw,plain, and custom field that supports markdown
        """
        self._test_get_with_custom_and_force(
            source_text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='plain',
            expected_text='# `This` is a **test**',
            custom_field_supports_markdown=True)

    def test_get_with_markdown_and_force_html_and_custom_markdown(self):
        """Testing the GET review-requests/<id>/draft/ API with rich text,
        ?force-text-type=raw,html, and custom field that supports markdown
        """
        self._test_get_with_custom_and_force(
            source_text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='html',
            expected_text='<p># <code>This</code> is a '
                          '<strong>test</strong></p>',
            custom_field_supports_markdown=True)

    def test_get_with_markdown_and_force_markdown_and_custom_nomarkdown(self):
        """Testing the GET review-requests/<id>/draft/ API with rich text,
        ?force-text-type=raw,markdown, and custom field that does not support
        markdown
        """
        self._test_get_with_custom_and_force(
            source_text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='markdown',
            expected_text=r'\# `This` is a **test**',
            custom_field_supports_markdown=False)

    def test_get_with_markdown_and_force_plain_and_custom_nomarkdown(self):
        """Testing the GET review-requests/<id>/draft/ API with rich text,
        ?force-text-type=raw,plain, and custom field that does not support
        markdown
        """
        self._test_get_with_custom_and_force(
            source_text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='plain',
            expected_text='# `This` is a **test**',
            custom_field_supports_markdown=False)

    def test_get_with_markdown_and_force_html_and_custom_nomarkdown(self):
        """Testing the GET review-requests/<id>/draft/ API with rich text,
        ?force-text-type=raw,html, and custom field that does not support
        markdown
        """
        self._test_get_with_custom_and_force(
            source_text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='html',
            expected_text='<p># <code>This</code> is a '
                          '<strong>test</strong></p>',
            custom_field_supports_markdown=False)

    def test_get_with_plain_and_force_markdown_and_custom_nomarkdown(self):
        """Testing the GET review-requests/<id>/draft/ API with plain text,
        ?force-text-type=raw,markdown, and custom field that does not support
        markdown
        """
        self._test_get_with_custom_and_force(
            source_text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='markdown',
            expected_text=r'\#<\`This\` is a \*\*test\*\*>',
            custom_field_supports_markdown=False)

    def test_get_with_plain_and_force_plain_and_custom_nomarkdown(self):
        """Testing the GET review-requests/<id>/draft/ API with plain text,
        ?force-text-type=raw,markdown, and custom field that does not support
        markdown
        """
        self._test_get_with_custom_and_force(
            source_text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='plain',
            expected_text='#<`This` is a **test**>',
            custom_field_supports_markdown=False)

    def test_get_with_plain_and_force_html_and_custom_nomarkdown(self):
        """Testing the GET review-requests/<id>/draft/ API with plain text,
        ?force-text-type=raw,markdown, and custom field that does not support
        markdown
        """
        self._test_get_with_custom_and_force(
            source_text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='html',
            expected_text='#&lt;`This` is a **test**&gt;',
            custom_field_supports_markdown=False)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        return (get_review_request_draft_url(review_request, local_site_name),
                review_request_draft_item_mimetype,
                {
                    'description': 'New description',
                },
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertFalse(draft.rich_text)
        self.compare_item(rsp['draft'], draft)

    def test_post_with_publish_and_custom_field(self):
        """Testing the POST review-requests/<id>/draft/ API with custom
        field set in same request and public=1
        """
        class CustomField(BaseReviewRequestField):
            can_record_change_entry = True
            field_id = 'my-test'

        fieldset = get_review_request_fieldset('info')
        fieldset.add_field(CustomField)

        try:
            review_request = self.create_review_request(submitter=self.user,
                                                        publish=True)

            rsp = self.api_post(
                get_review_request_draft_url(review_request),
                {
                    'extra_data.my-test': 123,
                    'public': True
                },
                expected_mimetype=review_request_draft_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')

            review_request = ReviewRequest.objects.get(pk=review_request.id)
            self.assertIn('my-test', review_request.extra_data)
            self.assertEqual(review_request.extra_data['my-test'], 123)
            self.assertTrue(review_request.public)
        finally:
            fieldset.remove_field(CustomField)

    def test_post_with_publish_and_custom_field_and_unbound_extra_data(self):
        """Testing the POST review-requests/<id>/draft/ API with custom
        text field and extra_data unbound to a field set in same request and
        public=1
        """
        class CustomField(BaseTextAreaField):
            field_id = 'my-test'

        fieldset = get_review_request_fieldset('info')
        fieldset.add_field(CustomField)

        try:
            review_request = self.create_review_request(submitter=self.user,
                                                        publish=True)

            rsp = self.api_post(
                get_review_request_draft_url(review_request),
                {
                    'extra_data.my-test': 'foo',
                    'extra_data.my-test_text_type': 'markdown',
                    'extra_data.unbound': 42,
                    'public': True
                },
                expected_mimetype=review_request_draft_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')

            # Confirm all the extra_data fields appear in the draft response.
            draft_rsp = rsp['draft']
            draft_extra_data = draft_rsp['extra_data']
            self.assertIn('my-test', draft_extra_data)
            self.assertEqual(draft_extra_data['my-test'], 'foo')
            self.assertIn('unbound', draft_extra_data)
            self.assertEqual(draft_extra_data['unbound'], 42)
            self.assertIn('my-test_text_type', draft_extra_data)
            self.assertEqual(draft_extra_data['my-test_text_type'], 'markdown')

            # Further confirm only extra_data contents bound to a field were
            # promoted to the review request upon publishing.
            review_request = ReviewRequest.objects.get(pk=review_request.id)
            self.assertIn('my-test', review_request.extra_data)
            self.assertEqual(review_request.extra_data['my-test'], 'foo')
            self.assertNotIn('unbound', review_request.extra_data)
            self.assertIn('my-test_text_type', review_request.extra_data)
            self.assertEqual(review_request.extra_data['my-test_text_type'],
                             'markdown')
            self.assertTrue(review_request.public)
        finally:
            fieldset.remove_field(CustomField)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        draft = ReviewRequestDraft.create(review_request)

        return (get_review_request_draft_url(review_request, local_site_name),
                review_request_draft_item_mimetype,
                {
                    'description': 'New description',
                },
                draft,
                [review_request])

    def check_put_result(self, user, item_rsp, draft, review_request):
        draft = ReviewRequestDraft.create(review_request)
        self.compare_item(item_rsp, draft)

    def test_put_with_changedesc(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with a change description
        """
        changedesc = 'This is a test change description.'
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        rsp = self.api_post(
            get_review_request_draft_url(review_request),
            {'changedescription': changedesc},
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['changedescription'], changedesc)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertNotEqual(draft.changedesc, None)
        self.assertEqual(draft.changedesc.text, changedesc)

    def test_put_with_no_changes(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with no changes made to the fields
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        ReviewRequestDraft.create(review_request)

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {'public': True},
            expected_status=NOTHING_TO_PUBLISH.http_status)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], NOTHING_TO_PUBLISH.code)

    def test_put_with_text_type_markdown(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with legacy text_type=markdown
        """
        self._test_put_with_text_types(
            text_type_field='text_type',
            text_type_value='markdown',
            expected_change_text_type='markdown',
            expected_description_text_type='markdown',
            expected_testing_done_text_type='markdown',
            expected_custom_field_text_type='markdown')

    def test_put_with_text_type_plain(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with legacy text_type=plain
        """
        self._test_put_with_text_types(
            text_type_field='text_type',
            text_type_value='plain',
            expected_change_text_type='plain',
            expected_description_text_type='plain',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='plain')

    def test_put_with_changedescription_text_type_markdown(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with changedescription_text_type=markdown
        """
        self._test_put_with_text_types(
            text_type_field='changedescription_text_type',
            text_type_value='markdown',
            expected_change_text_type='markdown',
            expected_description_text_type='plain',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='markdown')

    def test_put_with_changedescription_text_type_plain(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with changedescription_text_type=plain
        """
        self._test_put_with_text_types(
            text_type_field='changedescription_text_type',
            text_type_value='plain',
            expected_change_text_type='plain',
            expected_description_text_type='plain',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='markdown')

    def test_put_with_description_text_type_markdown(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with description_text_type=markdown
        """
        self._test_put_with_text_types(
            text_type_field='description_text_type',
            text_type_value='markdown',
            expected_change_text_type='plain',
            expected_description_text_type='markdown',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='markdown')

    def test_put_with_description_text_type_plain(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with description_text_type=plain
        """
        self._test_put_with_text_types(
            text_type_field='description_text_type',
            text_type_value='plain',
            expected_change_text_type='plain',
            expected_description_text_type='plain',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='markdown')

    def test_put_with_testing_done_text_type_markdown(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with testing_done_text_type=markdown
        """
        self._test_put_with_text_types(
            text_type_field='testing_done_text_type',
            text_type_value='markdown',
            expected_change_text_type='plain',
            expected_description_text_type='plain',
            expected_testing_done_text_type='markdown',
            expected_custom_field_text_type='markdown')

    def test_put_with_testing_done_text_type_plain(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with testing_done_text_type=plain
        """
        self._test_put_with_text_types(
            text_type_field='testing_done_text_type',
            text_type_value='plain',
            expected_change_text_type='plain',
            expected_description_text_type='plain',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='markdown')

    def test_put_with_custom_field_text_type_markdown(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with extra_data.*_text_type=markdown
        """
        self._test_put_with_text_types(
            text_type_field='extra_data.mytext_text_type',
            text_type_value='markdown',
            expected_change_text_type='plain',
            expected_description_text_type='plain',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='markdown')

    def test_put_with_custom_field_text_type_plain(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with extra_data.*_text_type=plain
        """
        self._test_put_with_text_types(
            text_type_field='extra_data.mytext_text_type',
            text_type_value='plain',
            expected_change_text_type='plain',
            expected_description_text_type='plain',
            expected_testing_done_text_type='plain',
            expected_custom_field_text_type='plain')

    def test_put_with_commit_id(self):
        """Testing the PUT review-requests/<id>/draft/ API with commit_id"""
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        commit_id = 'abc123'

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {
                'commit_id': commit_id,
            },
            expected_mimetype=review_request_draft_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['commit_id'], commit_id)
        self.assertEqual(rsp['draft']['summary'], review_request.summary)
        self.assertEqual(rsp['draft']['description'],
                         review_request.description)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertNotEqual(review_request.commit_id, commit_id)

    def test_put_with_commit_id_and_used_in_review_request(self):
        """Testing the PUT review-requests/<id>/draft/ API with commit_id
        used in another review request
        """
        commit_id = 'abc123'

        self.create_review_request(submitter=self.user,
                                   commit_id=commit_id,
                                   publish=True)

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        self.api_put(
            get_review_request_draft_url(review_request),
            {
                'commit_id': commit_id,
            },
            expected_status=409)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertIsNone(review_request.commit_id, None)

    def test_put_with_commit_id_and_used_in_draft(self):
        """Testing the PUT review-requests/<id>/draft/ API with commit_id
        used in another review request draft
        """
        commit_id = 'abc123'

        existing_review_request = self.create_review_request(
            submitter=self.user,
            publish=True)
        existing_draft = ReviewRequestDraft.create(existing_review_request)
        existing_draft.commit_id = commit_id
        existing_draft.save()

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        self.api_put(
            get_review_request_draft_url(review_request),
            {
                'commit_id': commit_id,
            },
            expected_status=409)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertIsNone(review_request.commit_id, None)

    def test_put_with_commit_id_empty_string(self):
        """Testing the PUT review-requests/<id>/draft/ API with commit_id=''"""
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {
                'commit_id': '',
            },
            expected_mimetype=review_request_draft_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIsNone(rsp['draft']['commit_id'])

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertIsNone(review_request.commit_id)

    @add_fixtures(['test_scmtools'])
    def test_put_with_commit_id_with_update_from_commit_id(self):
        """Testing the PUT review-requests/<id>/draft/ API with
        commit_id and update_from_commit_id=1
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(submitter=self.user,
                                                    repository=repository,
                                                    publish=True)
        commit_id = 'abc123'

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {
                'commit_id': commit_id,
                'update_from_commit_id': True,
            },
            expected_mimetype=review_request_draft_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['commit_id'], commit_id)
        self.assertEqual(rsp['draft']['summary'], 'Commit summary')
        self.assertEqual(rsp['draft']['description'], 'Commit description.')

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertNotEqual(review_request.commit_id, commit_id)

    def test_put_with_depends_on(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with depends_on field
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        depends_1 = self.create_review_request(
            summary='Dependency 1',
            publish=True)
        depends_2 = self.create_review_request(
            summary='Dependency 2',
            publish=True)

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {'depends_on': '%s, %s' % (depends_1.pk, depends_2.pk)},
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        depends_on = rsp['draft']['depends_on']
        self.assertEqual(len(depends_on), 2)
        depends_on.sort(key=lambda x: x['title'])
        self.assertEqual(depends_on[0]['title'], depends_1.summary)
        self.assertEqual(depends_on[1]['title'], depends_2.summary)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertEqual(list(draft.depends_on.order_by('pk')),
                         [depends_1, depends_2])
        self.assertEqual(list(depends_1.draft_blocks.all()), [draft])
        self.assertEqual(list(depends_2.draft_blocks.all()), [draft])

    @add_fixtures(['test_site'])
    def test_put_with_depends_on_and_site(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with depends_on field and local site
        """
        review_request = self.create_review_request(submitter='doc',
                                                    with_local_site=True)

        self._login_user(local_site=True)

        depends_1 = self.create_review_request(
            with_local_site=True,
            submitter=self.user,
            summary='Test review request',
            local_id=3,
            publish=True)

        # This isn't the review request we want to match.
        bad_depends = self.create_review_request(id=3, publish=True)

        rsp = self.api_put(
            get_review_request_draft_url(review_request, self.local_site_name),
            {'depends_on': '3'},
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        depends_on = rsp['draft']['depends_on']
        self.assertEqual(len(depends_on), 1)
        self.assertNotEqual(rsp['draft']['depends_on'][0]['title'],
                            bad_depends.summary)
        self.assertEqual(rsp['draft']['depends_on'][0]['title'],
                         depends_1.summary)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertEqual(list(draft.depends_on.all()), [depends_1])
        self.assertEqual(list(depends_1.draft_blocks.all()), [draft])
        self.assertEqual(bad_depends.draft_blocks.count(), 0)

    def test_put_with_depends_on_invalid_id(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with depends_on field and invalid ID
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {'depends_on': '10000'},
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')

        draft = review_request.get_draft()
        self.assertEqual(draft.depends_on.count(), 0)

    def test_put_with_permission_denied_error(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with Permission Denied error
        """
        bugs_closed = '123,456'
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {'bugs_closed': bugs_closed},
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_publish(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API"""
        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        draft = ReviewRequestDraft.create(review_request)
        draft.summary = 'My Summary'
        draft.description = 'My Description'
        draft.testing_done = 'My Testing Done'
        draft.branch = 'My Branch'
        draft.target_people.add(User.objects.get(username='doc'))
        draft.save()

        mail.outbox = []

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {'public': True},
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")
        self.assertTrue(review_request.public)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            "Re: Review Request %s: My Summary" % review_request.pk)
        self.assertValidRecipients(["doc", "grumpy"])

    def test_put_publish_with_new_review_request(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API
        with a new review request
        """
        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        # Set some data first.
        review_request = self.create_review_request(submitter=self.user)
        review_request.target_people = [
            User.objects.get(username='doc')
        ]
        review_request.save()

        self._create_update_review_request(self.api_put, 200, review_request)

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {'public': True},
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")
        self.assertTrue(review_request.public)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Review Request %s: My Summary" % review_request.pk)
        self.assertValidRecipients(["doc", "grumpy"], [])

    def test_put_as_other_user_with_permission(self):
        """Testing the PUT review-requests/<id>/draft/ API
        as another user with permission
        """
        self.user.user_permissions.add(
            Permission.objects.get(codename='can_edit_reviewrequest'))

        self._test_put_as_other_user()

    def test_put_as_other_user_with_admin(self):
        """Testing the PUT review-requests/<id>/draft/ API
        as another user with admin
        """
        self._login_user(admin=True)

        self._test_put_as_other_user()

    @add_fixtures(['test_site'])
    def test_put_as_other_user_with_site_and_permission(self):
        """Testing the PUT review-requests/<id>/draft/ API
        as another user with local site and permission
        """
        self.user = self._login_user(local_site=True)

        local_site = self.get_local_site(name=self.local_site_name)

        site_profile = LocalSiteProfile.objects.create(
            local_site=local_site,
            user=self.user,
            profile=self.user.get_profile())
        site_profile.permissions['reviews.can_edit_reviewrequest'] = True
        site_profile.save()

        self._test_put_as_other_user(local_site)

    @add_fixtures(['test_site'])
    def test_put_as_other_user_with_site_and_admin(self):
        """Testing the PUT review-requests/<id>/draft/ API
        as another user with local site and admin
        """
        self.user = self._login_user(local_site=True, admin=True)

        self._test_put_as_other_user(
            self.get_local_site(name=self.local_site_name))

    def test_put_find_user_fails(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with _find_user failure
        """
        self.spy_on(resources.review_request_draft._find_user,
                    call_fake=lambda *args, **kwargs: None)

        review_request = self.create_review_request(
            submitter=self.user)

        ReviewRequestDraft.create(review_request)

        rsp = self.api_put(
            get_review_request_draft_url(review_request, None),
            {
                'target_people': 'grumpy'
            },
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], 105)
        self.assertTrue(resources.review_request_draft._find_user.called)

    def test_put_with_publish_and_trivial(self):
        """Testing the PUT review-requests/<id>/draft/ API with trivial
        changes
        """
        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        draft = ReviewRequestDraft.create(review_request)
        draft.summary = 'My Summary'
        draft.description = 'My Description'
        draft.testing_done = 'My Testing Done'
        draft.branch = 'My Branch'
        draft.target_people.add(User.objects.get(username='doc'))
        draft.save()

        mail.outbox = []

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {
                'public': True,
                'trivial': True,
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")
        self.assertTrue(review_request.public)

        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_scmtools'])
    def test_put_with_publish_and_signal_handler_with_queries(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API with
        review_request_published signal handlers needing to fetch latest
        changedescs/diffsets
        """
        # We had a bug where diffset and changedesc information was cached
        # prior to publishing through the API, and was then stale when handled
        # by signal handlers. This change checks to ensure that state is
        # always fresh.

        def _on_published(review_request, *args, **kwargs):
            # Note that we're explicitly checking all() and not count() here
            # and below, because this is what was impacted by the bug before.
            self.assertEqual(len(review_request.changedescs.all()),
                             expected_changedesc_count)
            self.assertEqual(
                len(review_request.diffset_history.diffsets.all()),
                expected_diffset_count)

        expected_changedesc_count = 0
        expected_diffset_count = 0

        review_request_published.connect(_on_published, weak=True)

        try:
            self.spy_on(_on_published)

            review_request = self.create_review_request(submitter=self.user,
                                                        create_repository=True)
            draft_url = get_review_request_draft_url(review_request)

            # First, we're going to try publishing an initial draft. There
            # should be 1 diffset upon publish, and 0 changedescs.
            draft = ReviewRequestDraft.create(review_request)
            draft.summary = 'My Summary'
            draft.description = 'My Description'
            draft.testing_done = 'My Testing Done'
            draft.branch = 'My Branch'
            draft.target_people.add(User.objects.get(username='doc'))
            draft.save()
            diffset = self.create_diffset(review_request, draft=True)
            self.create_filediff(diffset)

            self.assertEqual(len(review_request.changedescs.all()),
                             expected_changedesc_count)
            self.assertEqual(
                len(review_request.diffset_history.diffsets.all()),
                expected_diffset_count)

            expected_diffset_count += 1

            rsp = self.api_put(
                draft_url,
                {'public': True},
                expected_mimetype=review_request_draft_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertTrue(_on_published.spy.called)

            _on_published.spy.reset_calls()

            # Now try posting an update. There should be 1 changedesc, 2
            # diffsets.
            diffset = self.create_diffset(review_request, draft=True)
            self.create_filediff(diffset)

            expected_changedesc_count += 1
            expected_diffset_count += 1

            rsp = self.api_put(
                draft_url,
                {'public': True},
                expected_mimetype=review_request_draft_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertTrue(_on_published.spy.called)
        finally:
            review_request_published.disconnect(_on_published)

    def test_put_with_numeric_extra_data(self):
        """Testing the PUT review-requests/<id>/draft/ API with numeric
        extra_data values
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        rsp = self.api_put(
            get_review_request_draft_url(review_request),
            {
                'extra_data.int_val': 42,
                'extra_data.float_val': 3.14159,
                'extra_data.scientific_val': 2.75e-15
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft_rsp = rsp['draft']
        extra_data = draft_rsp['extra_data']
        self.assertEqual(extra_data['int_val'], 42)
        self.assertEqual(extra_data['float_val'], 3.14159)
        self.assertEqual(extra_data['scientific_val'], 2.75e-15)

    def test_get_or_create_user_auth_backend(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with AuthBackend.get_or_create_user failure
        """
        class SandboxAuthBackend(AuthBackend):
            backend_id = 'test-id'
            name = 'test'

            def get_or_create_user(self, username, request=None,
                                   password=None):
                raise Exception

        backend = SandboxAuthBackend()

        self.spy_on(auth.get_backends, call_fake=lambda: [backend])

        # The first spy messes with permissions, this lets it through
        self.spy_on(ReviewRequest.is_mutable_by, call_fake=lambda x, y: True)
        self.spy_on(backend.get_or_create_user)

        review_request = self.create_review_request(
            submitter=self.user)

        ReviewRequestDraft.create(review_request)

        rsp = self.api_put(
            get_review_request_draft_url(review_request, None),
            {
                'target_people': 'Target',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertTrue(backend.get_or_create_user.called)

    def _create_update_review_request(self, api_func, expected_status,
                                      review_request=None,
                                      local_site_name=None):
        summary = "My Summary"
        description = "My Description"
        testing_done = "My Testing Done"
        branch = "My Branch"
        bugs = "#123,456"

        if review_request is None:
            review_request = self.create_review_request(submitter=self.user,
                                                        publish=True)
            review_request.target_people.add(
                User.objects.get(username='doc'))

        func_kwargs = {
            'summary': summary,
            'description': description,
            'testing_done': testing_done,
            'branch': branch,
            'bugs_closed': bugs,
        }

        if expected_status >= 400:
            expected_mimetype = None
        else:
            expected_mimetype = review_request_draft_item_mimetype

        rsp = api_func(
            get_review_request_draft_url(review_request, local_site_name),
            func_kwargs,
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

        if expected_status >= 200 and expected_status < 300:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertEqual(rsp['draft']['summary'], summary)
            self.assertEqual(rsp['draft']['description'], description)
            self.assertEqual(rsp['draft']['testing_done'], testing_done)
            self.assertEqual(rsp['draft']['branch'], branch)
            self.assertEqual(rsp['draft']['bugs_closed'], ['123', '456'])

            draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
            self.assertEqual(draft.summary, summary)
            self.assertEqual(draft.description, description)
            self.assertEqual(draft.testing_done, testing_done)
            self.assertEqual(draft.branch, branch)
            self.assertEqual(draft.get_bug_list(), ['123', '456'])

        return rsp

    def _create_update_review_request_with_site(self, api_func,
                                                expected_status,
                                                relogin=True,
                                                review_request=None):
        if relogin:
            self._login_user(local_site=True)

        if review_request is None:
            review_request = self.create_review_request(submitter='doc',
                                                        with_local_site=True)

        return self._create_update_review_request(
            api_func, expected_status, review_request, self.local_site_name)

    def _test_get_with_force_text_type(self, text, rich_text,
                                       force_text_type, expected_text):
        url, mimetype, draft = \
            self.setup_basic_get_test(self.user, False, None)

        draft.description = text
        draft.testing_done = text
        draft.description_rich_text = rich_text
        draft.testing_done_rich_text = rich_text
        draft.save()

        draft.changedesc.text = text
        draft.changedesc.rich_text = rich_text
        draft.changedesc.save()

        rsp = self.api_get(url + '?force-text-type=%s' % force_text_type,
                           expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        draft_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(draft_rsp['description_text_type'], force_text_type)
        self.assertEqual(draft_rsp['testing_done_text_type'], force_text_type)
        self.assertEqual(draft_rsp['changedescription'], expected_text)
        self.assertEqual(draft_rsp['description'], expected_text)
        self.assertEqual(draft_rsp['testing_done'], expected_text)
        self.assertNotIn('raw_text_fields', draft_rsp)

        rsp = self.api_get('%s?force-text-type=%s&include-text-types=raw'
                           % (url, force_text_type),
                           expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        draft_rsp = rsp[self.resource.item_result_key]
        self.assertIn('raw_text_fields', draft_rsp)
        raw_text_fields = draft_rsp['raw_text_fields']
        self.assertEqual(raw_text_fields['changedescription'], text)
        self.assertEqual(raw_text_fields['description'], text)
        self.assertEqual(raw_text_fields['testing_done'], text)

    def _test_get_with_custom_and_force(self, source_text, rich_text,
                                        force_text_type, expected_text,
                                        custom_field_supports_markdown):
        """Helper function to test custom fields and ``?include-text-types=``.

        This will test GET requests of custom text fields in two alternative
        formats (one fixed as ``raw`` and the other controlled by
        ``force_text_type``) via the ``?include-text-types=`` query parameter.

        Args:
            source_text (unicode):
                Text to use as source data for fields being tested.

            rich_text (bool):
                Whether ``source_text`` is rich text.

            force_text_type (unicode):
                Value for ``?force-text-type=`` query parameter. Should be one
                of: ``plain``, ``markdown`` or ``html``.

            expected_text (unicode):
                Expected resultant text after forcing ``source_text`` to
                requested format.

            custom_field_supports_markdown (bool)
                Whether custom field being tested should enable markdown
                support.
        """
        # Exercise custom fields that support markdown (BaseTextAreaField) and
        # those that don't (BaseEditableField). Fields that don't support
        # markdown do not get serialized into
        # <text_type>_text_fields.extra_data.
        if custom_field_supports_markdown:
            base = BaseTextAreaField
        else:
            base = BaseEditableField

        class CustomField(base):
            # Utilize "text" as the field_id because it is a special case and
            # results in a text type field named "text_type".
            field_id = 'text'

        fieldset = get_review_request_fieldset('main')
        fieldset.add_field(CustomField)

        try:
            url, mimetype, draft = \
                self.setup_basic_get_test(self.user, False, None)

            source_text_type = "markdown" if rich_text else "plain"

            draft.description = source_text
            draft.description_rich_text = rich_text
            draft.extra_data['text'] = source_text
            if custom_field_supports_markdown:
                draft.extra_data['text_type'] = source_text_type
            draft.save()

            rsp = self.api_get(url + '?force-text-type=%s' % force_text_type,
                               expected_mimetype=mimetype)
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(self.resource.item_result_key, rsp)

            draft_rsp = rsp[self.resource.item_result_key]
            self.assertIn('extra_data', draft_rsp)
            extra_data = draft_rsp['extra_data']
            self.assertEqual(draft_rsp['description_text_type'],
                             force_text_type)
            self.assertEqual(draft_rsp['description'], expected_text)
            self.assertNotIn('raw_text_fields', draft_rsp)

            if custom_field_supports_markdown:
                # Ensure the name of the text_type field has not been
                # formulated incorrectly, since "text" is a special name, and
                # thus we expect "text_type" not "text_text_type".
                self.assertNotIn('text_text_type', extra_data)

                self.assertEqual(extra_data['text'], expected_text)
                self.assertEqual(extra_data['text_type'], force_text_type)
            else:
                self.assertEqual(extra_data['text'], source_text)
                self.assertNotIn('text_type', extra_data)

            # Exercise including multiple text types via a CSV list.
            rsp = self.api_get(
                '%s?force-text-type=%s&include-text-types=raw,%s'
                % (url, force_text_type, force_text_type),
                expected_mimetype=mimetype)
            self.assertEqual(rsp['stat'], 'ok')

            draft_rsp = rsp[self.resource.item_result_key]
            self.assertIn('raw_text_fields', draft_rsp)
            raw_text_fields = draft_rsp['raw_text_fields']
            self.assertEqual(raw_text_fields['description'], source_text)
            self.assertEqual(raw_text_fields['description_text_type'],
                             source_text_type)

            other_field_name = '%s_text_fields' % force_text_type
            self.assertIn(other_field_name, draft_rsp)
            other_text_fields = draft_rsp[other_field_name]
            self.assertEqual(other_text_fields['description'], expected_text)
            self.assertEqual(other_text_fields['description_text_type'],
                             force_text_type)

            if custom_field_supports_markdown:
                self.assertIn('extra_data', raw_text_fields)
                extra_data_raw = raw_text_fields['extra_data']
                self.assertEqual(extra_data_raw['text'], source_text)
                self.assertEqual(extra_data_raw['text_type'], source_text_type)

                self.assertIn('extra_data', other_text_fields)
                extra_data_other = other_text_fields['extra_data']
                self.assertEqual(extra_data_other['text'], expected_text)
                self.assertEqual(extra_data_other['text_type'],
                                 force_text_type)
            else:
                self.assertNotIn('extra_data', raw_text_fields)
                self.assertNotIn('extra_data', other_text_fields)
        finally:
            fieldset.remove_field(CustomField)

    def _test_put_with_text_types(self, text_type_field, text_type_value,
                                  expected_change_text_type,
                                  expected_description_text_type,
                                  expected_testing_done_text_type,
                                  expected_custom_field_text_type):
        text = '`This` is a **test**'

        class CustomField(BaseTextAreaField):
            field_id = 'mytext'

        fieldset = get_review_request_fieldset('main')
        fieldset.add_field(CustomField)

        try:
            review_request = self.create_review_request(submitter=self.user,
                                                        publish=True)

            rsp = self.api_put(
                get_review_request_draft_url(review_request),
                {
                    'changedescription': text,
                    'description': text,
                    'testing_done': text,
                    'extra_data.mytext': text,
                    text_type_field: text_type_value,
                },
                expected_mimetype=review_request_draft_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')

            draft_rsp = rsp['draft']
            extra_data = draft_rsp['extra_data']
            self.assertEqual(draft_rsp['changedescription'], text)
            self.assertEqual(draft_rsp['description'], text)
            self.assertEqual(draft_rsp['testing_done'], text)
            self.assertEqual(extra_data['mytext'], text)
            self.assertEqual(draft_rsp['changedescription_text_type'],
                             expected_change_text_type)
            self.assertEqual(draft_rsp['description_text_type'],
                             expected_description_text_type)
            self.assertEqual(draft_rsp['testing_done_text_type'],
                             expected_testing_done_text_type)
            self.assertEqual(extra_data['mytext_text_type'],
                             expected_custom_field_text_type)

            draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
            self.compare_item(draft_rsp, draft)
        finally:
            fieldset.remove_field(CustomField)

    def _test_put_as_other_user(self, local_site=None):
        review_request = self.create_review_request(
            with_local_site=(local_site is not None),
            submitter='dopey',
            publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        ReviewRequestDraft.create(review_request)

        if local_site:
            local_site_name = local_site.name
        else:
            local_site_name = None

        rsp = self.api_put(
            get_review_request_draft_url(review_request, local_site_name),
            {
                'description': 'New description',
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(rsp['draft']['description'], 'New description')
