from django.contrib.auth.models import User
from django.core import mail
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import INVALID_FORM_DATA, PERMISSION_DENIED

from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    review_request_draft_item_mimetype
from reviewboard.webapi.tests.urls import get_review_request_draft_url


class ReviewRequestDraftResourceTests(BaseWebAPITestCase):
    """Testing the ReviewRequestDraftResource API tests."""
    fixtures = ['test_users']

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

    def test_delete_reviewrequestdraft(self):
        """Testing the DELETE review-requests/<id>/draft/ API"""
        review_request = self.create_review_request(submitter=self.user)
        summary = review_request.summary
        description = review_request.description

        # Set some data.
        self.test_put_reviewrequestdraft(review_request)

        self.apiDelete(get_review_request_draft_url(review_request))

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    @add_fixtures(['test_site'])
    def test_delete_reviewrequestdraft_with_site(self):
        """Testing the DELETE review-requests/<id>/draft/ API
        with a local site
        """
        review_request = self.create_review_request(submitter='doc',
                                                    with_local_site=True)
        summary = review_request.summary
        description = review_request.description

        self.test_put_reviewrequestdraft_with_site(review_request)

        self.apiDelete(get_review_request_draft_url(review_request,
                                                    self.local_site_name))

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    @add_fixtures(['test_site'])
    def test_delete_reviewrequestdraft_with_site_no_access(self):
        """Testing the DELETE review-requests/<id>/draft/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(submitter='doc',
                                                    with_local_site=True)

        rsp = self.apiDelete(
            get_review_request_draft_url(review_request, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_reviewrequestdraft(self):
        """Testing the POST review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPost, 201)

    @add_fixtures(['test_site'])
    def test_post_reviewrequestdraft_with_site(self):
        """Testing the POST review-requests/<id>/draft/ API
        with a local site
        """
        self._create_update_review_request_with_site(self.apiPost, 201)

    @add_fixtures(['test_site'])
    def test_post_reviewrequestdraft_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/ API
        with a local site and Permission Denied error
        """
        rsp = self._create_update_review_request_with_site(
            self.apiPost, 403, relogin=False)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequestdraft(self, review_request=None):
        """Testing the PUT review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPut, 200, review_request)

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_site(self, review_request=None):
        """Testing the PUT review-requests/<id>/draft/ API with a local site"""
        self._create_update_review_request_with_site(
            self.apiPut, 200, review_request=review_request)

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/draft/ API
        with a local site and Permission Denied error
        """
        rsp = self._create_update_review_request_with_site(
            self.apiPut, 403, relogin=False)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequestdraft_with_changedesc(self):
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

    def test_put_reviewrequestdraft_with_depends_on(self):
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
    def test_put_reviewrequestdraft_with_depends_on_and_site(self):
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

    def test_put_reviewrequestdraft_with_depends_on_invalid_id(self):
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

    def test_put_reviewrequestdraft_with_invalid_field_name(self):
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

    def test_put_reviewrequestdraft_with_permission_denied_error(self):
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

    def test_put_reviewrequestdraft_publish(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API"""
        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        # Set some data first.
        self.test_put_reviewrequestdraft()

        mail.outbox = []

        review_request = ReviewRequest.objects.from_user(self.user.username)[0]

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
        self.assertValidRecipients(["doc", "grumpy"])

    def test_put_reviewrequestdraft_publish_with_new_review_request(self):
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
