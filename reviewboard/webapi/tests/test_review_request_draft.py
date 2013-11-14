from __future__ import unicode_literals

from django.contrib.auth.models import Permission, User
from django.core import mail
from djblets.testing.decorators import add_fixtures
from djblets.util.compat import six
from djblets.webapi.errors import INVALID_FORM_DATA, PERMISSION_DENIED

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    review_request_draft_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_review_request_draft_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the ReviewRequestDraftResource API tests."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/'
    resource = resources.review_request_draft

    def compare_item(self, item_rsp, draft):
        changedesc = draft.changedesc

        self.assertEqual(item_rsp['description'], draft.description)
        self.assertEqual(item_rsp['testing_done'], draft.testing_done)
        self.assertEqual(item_rsp['rich_text'], draft.rich_text)
        self.assertEqual(item_rsp['rich_text'], changedesc.rich_text)
        self.assertEqual(item_rsp['changedescription'], changedesc.text)

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

        rsp = self.apiPost(
            get_review_request_draft_url(review_request),
            {'changedescription': changedesc},
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['changedescription'], changedesc)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertNotEqual(draft.changedesc, None)
        self.assertEqual(draft.changedesc.text, changedesc)

    def test_put_with_rich_text_true_all_fields(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with rich_text=true and all fields specified
        """
        self._test_put_with_rich_text_all_fields(True)

    def test_put_with_rich_text_false_all_fields(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with rich_text=false and all fields specified
        """
        self._test_put_with_rich_text_all_fields(False)

    def test_put_with_rich_text_true_escaping_all_fields(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with changing rich_text to true and escaping all fields
        """
        self._test_put_with_rich_text_escaping_all_fields(
            True,
            '`This` is a **test**',
            '\\`This\\` is a \\*\\*test\\*\\*')

    def test_put_with_rich_text_false_unescaping_all_fields(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with changing rich_text to false and unescaping all fields
        """
        self._test_put_with_rich_text_escaping_all_fields(
            False,
            '\\`This\\` is a \\*\\*test\\*\\*',
            '`This` is a **test**')

    def test_put_with_rich_text_true_escaping_unspecified_fields(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with changing rich_text to true and escaping unspecified fields
        """
        self._test_put_with_rich_text_escaping_unspecified_fields(
            True,
            '`This` is a **test**',
            '\\`This\\` is a \\*\\*test\\*\\*')

    def test_put_with_rich_text_false_unescaping_unspecified_fields(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with changing rich_text to false and unescaping unspecified fields
        """
        self._test_put_with_rich_text_escaping_unspecified_fields(
            False,
            '\\`This\\` is a \\*\\*test\\*\\*',
            '`This` is a **test**')

    def test_put_without_rich_text_and_escaping_provided_fields(self):
        """Testing the PUT review-requests/<id>/draft/ API
        without changing rich_text and with escaping provided fields
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        review_request.rich_text = True
        review_request.save()

        draft = ReviewRequestDraft.create(review_request)

        self.assertTrue(draft.rich_text)
        self.assertTrue(draft.changedesc.rich_text)

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {
                'description': 'This is **Description**',
                'testing_done': 'This is **Testing Done**',
                'changedescription': 'This is **Change Description**',
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft_rsp = rsp['draft']
        self.assertTrue(draft_rsp['rich_text'])
        self.assertEqual(draft_rsp['description'],
                         'This is \*\*Description\*\*')
        self.assertEqual(draft_rsp['testing_done'],
                         'This is \*\*Testing Done\*\*')
        self.assertEqual(draft_rsp['changedescription'],
                         'This is \*\*Change Description\*\*')

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.compare_item(draft_rsp, draft)

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

        rsp = self.apiPut(
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

        rsp = self.apiPut(
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

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {'depends_on': '10000'},
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')

        draft = review_request.get_draft()
        self.assertEqual(draft.depends_on.count(), 0)

    def test_put_with_invalid_field_name(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with Invalid Form Data error
        """
        review_request = self.create_review_request(submitter=self.user)

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {'foobar': 'foo'},
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('foobar' in rsp['fields'])

    def test_put_with_permission_denied_error(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with Permission Denied error
        """
        bugs_closed = '123,456'
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        rsp = self.apiPut(
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

        rsp = self.apiPut(
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

        self._create_update_review_request(self.apiPut, 200, review_request)

        rsp = self.apiPut(
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

        local_site = LocalSite.objects.get(name=self.local_site_name)

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
            LocalSite.objects.get(name=self.local_site_name))

    def _create_update_review_request(self, apiFunc, expected_status,
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

        rsp = apiFunc(
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

    def _create_update_review_request_with_site(self, apiFunc, expected_status,
                                                relogin=True,
                                                review_request=None):
        if relogin:
            self._login_user(local_site=True)

        if review_request is None:
            review_request = self.create_review_request(submitter='doc',
                                                        with_local_site=True)

        return self._create_update_review_request(
            apiFunc, expected_status, review_request, self.local_site_name)

    def _test_put_with_rich_text_all_fields(self, rich_text):
        text = '`This` is a **test**'

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {
                'rich_text': rich_text,
                'changedescription': text,
                'description': text,
                'testing_done': text,
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft_rsp = rsp['draft']
        self.assertEqual(draft_rsp['rich_text'], rich_text)
        self.assertEqual(draft_rsp['changedescription'], text)
        self.assertEqual(draft_rsp['description'], text)
        self.assertEqual(draft_rsp['testing_done'], text)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.compare_item(draft_rsp, draft)

    def _test_put_with_rich_text_escaping_all_fields(
            self, rich_text, text, expected_text):

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        review_request.rich_text = not rich_text
        review_request.description = text
        review_request.testing_done = text
        review_request.save()

        draft = ReviewRequestDraft.create(review_request)
        draft.changedesc.text = text
        draft.changedesc.save()

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {
                'rich_text': rich_text,
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft_rsp = rsp['draft']
        self.assertEqual(draft_rsp['rich_text'], rich_text)
        self.assertEqual(draft_rsp['changedescription'], expected_text)
        self.assertEqual(draft_rsp['description'], expected_text)
        self.assertEqual(draft_rsp['testing_done'], expected_text)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.compare_item(draft_rsp, draft)

    def _test_put_with_rich_text_escaping_unspecified_fields(
            self, rich_text, text, expected_text):

        description = '`This` is the **description**'

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        review_request.rich_text = not rich_text
        review_request.description = text
        review_request.testing_done = text
        review_request.save()

        draft = ReviewRequestDraft.create(review_request)
        draft.changedesc.text = text
        draft.changedesc.save()

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {
                'rich_text': rich_text,
                'description': description,
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft_rsp = rsp['draft']
        self.assertEqual(draft_rsp['rich_text'], rich_text)
        self.assertEqual(draft_rsp['changedescription'], expected_text)
        self.assertEqual(draft_rsp['description'], description)
        self.assertEqual(draft_rsp['testing_done'], expected_text)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.compare_item(draft_rsp, draft)

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

        rsp = self.apiPut(
            get_review_request_draft_url(review_request, local_site_name),
            {
                'description': 'New description',
            },
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(rsp['draft']['description'], 'New description')
