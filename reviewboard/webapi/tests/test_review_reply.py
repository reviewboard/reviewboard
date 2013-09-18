from django.core import mail
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Review
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_reply_item_mimetype,
                                                review_reply_list_mimetype)
from reviewboard.webapi.tests.urls import (get_review_reply_item_url,
                                           get_review_reply_list_url)


class ReviewReplyResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyResource APIs."""
    fixtures = ['test_users']

    #
    # List tests
    #

    def test_get_replies(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies API"""
        review = self._create_test_review()
        reply = self.create_reply(review, user=self.user, publish=True)

        rsp = self.apiGet(get_review_reply_list_url(review),
                          expected_mimetype=review_reply_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), 1)

        reply_rsp = rsp['replies'][0]
        self.assertEqual(reply_rsp['id'], reply.id)
        self.assertEqual(reply_rsp['body_top'], reply.body_top)
        self.assertEqual(reply_rsp['body_bottom'], reply.body_bottom)

    def test_get_replies_with_counts_only(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/replies/?counts-only=1 API
        """
        review = self._create_test_review()
        self.create_reply(review, user=self.user, publish=True)

        rsp = self.apiGet(
            '%s?counts-only=1' % get_review_reply_list_url(review),
            expected_mimetype=review_reply_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 1)

    @add_fixtures(['test_site'])
    def test_get_replies_with_site(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/replies/ API with a local site
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        review = self.create_review(review_request, publish=True)
        review = self.create_reply(review, user=self.user, publish=True)

        self._login_user(local_site=True)

        public_replies = review.public_replies()

        rsp = self.apiGet(
            get_review_reply_list_url(review, self.local_site_name),
            expected_mimetype=review_reply_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), public_replies.count())

        for i in range(public_replies.count()):
            reply = public_replies[i]
            self.assertEqual(rsp['replies'][i]['id'], reply.id)
            self.assertEqual(rsp['replies'][i]['body_top'], reply.body_top)
            self.assertEqual(rsp['replies'][i]['body_bottom'],
                             reply.body_bottom)

    @add_fixtures(['test_site'])
    def test_get_replies_with_site_no_access(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp = self.apiGet(
            get_review_reply_list_url(review, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_replies(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        mail.outbox = []

        rsp = self.apiPost(
            get_review_reply_list_url(review),
            {'body_top': 'Test'},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_replies_with_site(self):
        """Testing the POST review-requsets/<id>/reviews/<id>/replies/ API
        with a local site
        """
        review_request = self.create_review_request(with_local_site=True)
        review = self.create_review(review_request, publish=True)

        mail.outbox = []

        self._login_user(local_site=True)

        rsp = self.apiPost(
            get_review_reply_list_url(review, self.local_site_name),
            {'body_top': 'Test'},
            expected_mimetype=review_reply_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_replies_with_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True)
        review = self.create_review(review_request, publish=True)

        rsp = self.apiPost(
            get_review_reply_list_url(review, self.local_site_name),
            {'body_top': 'Test'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_replies_with_body_top(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API
        with body_top
        """
        body_top = 'My Body Top'

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp = self.apiPost(
            get_review_reply_list_url(review),
            {'body_top': body_top},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_top, body_top)

    def test_post_replies_with_body_bottom(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API
        with body_bottom
        """
        body_bottom = 'My Body Bottom'

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp = self.apiPost(
            get_review_reply_list_url(review),
            {'body_bottom': body_bottom},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_bottom, body_bottom)

    #
    # Item tests
    #

    def test_delete_reply(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, user='doc', publish=True)

        rsp = self.apiPost(
            get_review_reply_list_url(review),
            {'body_top': 'Test'},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_id = rsp['reply']['id']
        rsp = self.apiDelete(rsp['reply']['links']['self']['href'])

        self.assertEqual(Review.objects.filter(pk=reply_id).count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_reply_with_site(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API
        with a local site
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        review = self.create_review(review_request, user='doc', publish=True)
        reply = self.create_reply(review, user=review.user)

        self._login_user(local_site=True)
        self.apiDelete(get_review_reply_item_url(review, reply.id,
                                                 self.local_site_name))
        self.assertEqual(review.replies.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_reply_with_site_no_access(self):
        """Testing the
        DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review)

        rsp = self.apiDelete(get_review_reply_item_url(review, reply.id,
                                                       self.local_site_name),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reply_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review, publish=True)

        self._testHttpCaching(
            get_review_reply_item_url(reply.base_reply_to, reply.id),
            check_last_modified=True)

    def test_put_reply(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/replies/<id>/ API
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp, response = self.api_post_with_response(
            get_review_reply_list_url(review),
            expected_mimetype=review_reply_item_mimetype)

        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(
            response['Location'],
            {'body_top': 'Test'},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_put_reply_with_site(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API
        with a local site
        """
        review_request = self.create_review_request(with_local_site=True)

        review = self.create_review(review_request, user='doc', publish=True)

        self._login_user(local_site=True)

        rsp, response = self.api_post_with_response(
            get_review_reply_list_url(review, self.local_site_name),
            expected_mimetype=review_reply_item_mimetype)
        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(
            response['Location'],
            {'body_top': 'Test'},
            expected_mimetype=review_reply_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_put_reply_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True)
        review = self.create_review(review_request, user='doc', publish=True)
        reply = self.create_reply(review, user=self.user, publish=True)

        rsp = self.apiPut(
            get_review_reply_item_url(review, reply.id, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reply_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/replies/<id>/?public=1 API
        """
        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        mail.outbox = []

        rsp, response = self.api_post_with_response(
            get_review_reply_list_url(review),
            expected_mimetype=review_reply_item_mimetype)

        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(
            response['Location'],
            {
                'body_top': 'Test',
                'public': True,
            },
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.public, True)

        self.assertEqual(len(mail.outbox), 1)

    def _create_test_review(self, with_local_site=False):
        review_request = self.create_review_request(
            submitter=self.user,
            with_local_site=with_local_site)
        file_attachment = self.create_file_attachment(review_request)
        review_request.publish(review_request.submitter)

        review = self.create_review(review_request, publish=True)
        self.create_file_attachment_comment(review, file_attachment)

        return review
