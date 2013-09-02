from django.contrib.auth.models import User
from django.core import mail
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import INVALID_FORM_DATA, PERMISSION_DENIED

from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    review_request_draft_item_mimetype
from reviewboard.webapi.tests.urls import get_review_request_draft_url


class ReviewRequestDraftResourceTests(BaseWebAPITestCase):
    """Testing the ReviewRequestDraftResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    def _create_update_review_request(self, apiFunc, expected_status,
                                      review_request=None,
                                      local_site_name=None):
        summary = "My Summary"
        description = "My Description"
        testing_done = "My Testing Done"
        branch = "My Branch"
        bugs = "#123,456"

        if review_request is None:
            review_request = \
                ReviewRequest.objects.from_user(self.user.username)[0]

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
            review_request = ReviewRequest.objects.from_user(
                'doc',
                local_site=LocalSite.objects.get(name=self.local_site_name))[0]

        return self._create_update_review_request(
            apiFunc, expected_status, review_request, self.local_site_name)

    def test_put_reviewrequestdraft(self):
        """Testing the PUT review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPut, 200)

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_site(self):
        """Testing the PUT review-requests/<id>/draft/ API with a local site"""
        self._create_update_review_request_with_site(self.apiPut, 200)

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/draft/ API with a local site and Permission Denied error"""
        rsp = self._create_update_review_request_with_site(
            self.apiPut, 403, relogin=False)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_reviewrequestdraft(self):
        """Testing the POST review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPost, 201)

    @add_fixtures(['test_site'])
    def test_post_reviewrequestdraft_with_site(self):
        """Testing the POST review-requests/<id>/draft/ API with a local site"""
        self._create_update_review_request_with_site(self.apiPost, 201)

    @add_fixtures(['test_site'])
    def test_post_reviewrequestdraft_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/ API with a local site and Permission Denied error"""
        rsp = self._create_update_review_request_with_site(
            self.apiPost, 403, relogin=False)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequestdraft_with_changedesc(self):
        """Testing the PUT review-requests/<id>/draft/ API with a change description"""
        changedesc = 'This is a test change description.'
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.publish(self.user)

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
        """Testing the PUT review-requests/<id>/draft/ API with depends_on field"""
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.publish(self.user)

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {'depends_on': '1, 3'},
            expected_mimetype=review_request_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        depends_1 = ReviewRequest.objects.get(pk=1)
        depends_2 = ReviewRequest.objects.get(pk=3)

        depends_on = rsp['draft']['depends_on']
        self.assertEqual(len(depends_on), 2)
        self.assertEqual(rsp['draft']['depends_on'][0]['title'],
                         depends_1.summary)
        self.assertEqual(rsp['draft']['depends_on'][1]['title'],
                         depends_2.summary)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertEqual(list(draft.depends_on.all()), [depends_1, depends_2])
        self.assertEqual(list(depends_1.draft_blocks.all()), [draft])
        self.assertEqual(list(depends_2.draft_blocks.all()), [draft])

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_depends_on_and_site(self):
        """Testing the PUT review-requests/<id>/draft/ API with depends_on field and local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.from_user(
            'doc', local_site=local_site)[0]

        self._login_user(local_site=True)

        depends_1 = ReviewRequest.objects.create(self.user, self.repository)
        depends_1.summary = "Test review request"
        depends_1.local_site = local_site
        depends_1.local_id = 3
        depends_1.public = True
        depends_1.save()

        # This isn't the review request we want to match.
        bad_depends = ReviewRequest.objects.get(pk=3)

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
        """Testing the PUT review-requests/<id>/draft/ API with depends_on field and invalid ID"""
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.publish(self.user)

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {'depends_on': '10000'},
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')

        draft = review_request.get_draft()
        self.assertEqual(draft.depends_on.count(), 0)

    def test_put_reviewrequestdraft_with_invalid_field_name(self):
        """Testing the PUT review-requests/<id>/draft/ API with Invalid Form Data error"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {'foobar': 'foo'},
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('foobar' in rsp['fields'])

    def test_put_reviewrequestdraft_with_permission_denied_error(self):
        """Testing the PUT review-requests/<id>/draft/ API with Permission Denied error"""
        bugs_closed = '123,456'
        review_request = ReviewRequest.objects.from_user('admin')[0]

        rsp = self.apiPut(
            get_review_request_draft_url(review_request),
            {'bugs_closed': bugs_closed},
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequestdraft_publish(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API"""
        # Set some data first.
        self.test_put_reviewrequestdraft()

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
        self.assertEqual(mail.outbox[0].subject, "Review Request 4: My Summary")
        self.assertValidRecipients(["doc", "grumpy"], [])

    def test_put_reviewrequestdraft_publish_with_new_review_request(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API with a new review request"""
        # Set some data first.
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
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
        self.assertEqual(mail.outbox[0].subject, "Review Request 10: My Summary")
        self.assertValidRecipients(["doc", "grumpy"], [])

    def test_delete_reviewrequestdraft(self):
        """Testing the DELETE review-requests/<id>/draft/ API"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]
        summary = review_request.summary
        description = review_request.description

        # Set some data.
        self.test_put_reviewrequestdraft()

        self.apiDelete(get_review_request_draft_url(review_request))

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    @add_fixtures(['test_site'])
    def test_delete_reviewrequestdraft_with_site(self):
        """Testing the DELETE review-requests/<id>/draft/ API with a local site"""
        review_request = ReviewRequest.objects.from_user(
            'doc',
            local_site=LocalSite.objects.get(name=self.local_site_name))[0]
        summary = review_request.summary
        description = review_request.description

        self.test_put_reviewrequestdraft_with_site()

        self.apiDelete(get_review_request_draft_url(review_request,
                                                    self.local_site_name))

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    @add_fixtures(['test_site'])
    def test_delete_reviewrequestdraft_with_site_no_access(self):
        """Testing the DELETE review-requests/<id>/draft/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.from_user(
            'doc',
            local_site=LocalSite.objects.get(name=self.local_site_name))[0]
        rsp = self.apiDelete(
            get_review_request_draft_url(review_request, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
