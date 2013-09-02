from django.contrib.auth.models import User
from django.core import mail
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Review, ReviewRequest
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_reply_item_mimetype,
                                                review_reply_list_mimetype)
from reviewboard.webapi.tests.urls import (get_review_reply_item_url,
                                           get_review_reply_list_url)


class ReviewReplyResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    def test_get_replies(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.test_put_reply()

        public_replies = review.public_replies()

        rsp = self.apiGet(get_review_reply_list_url(review),
                          expected_mimetype=review_reply_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), public_replies.count())

        for i in range(public_replies.count()):
            reply = public_replies[i]
            self.assertEqual(rsp['replies'][i]['id'], reply.id)
            self.assertEqual(rsp['replies'][i]['body_top'], reply.body_top)
            self.assertEqual(rsp['replies'][i]['body_bottom'],
                             reply.body_bottom)

    def test_get_replies_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies/?counts-only=1 API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.test_put_reply()

        rsp = self.apiGet(
            '%s?counts-only=1' % get_review_reply_list_url(review),
            expected_mimetype=review_reply_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.public_replies().count())

    @add_fixtures(['test_site'])
    def test_get_replies_with_site(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = True
        reply.base_reply_to = review
        reply.save()

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
        """Testing the GET review-requests/<id>/reviews/<id>/replies/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        rsp = self.apiGet(
            get_review_reply_list_url(review, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reply_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/ with Not Modified response"""
        reply = \
            Review.objects.filter(base_reply_to__isnull=False, public=True)[0]
        self._testHttpCaching(
            get_review_reply_item_url(reply.base_reply_to, reply.id),
            check_last_modified=True)

    def test_post_replies(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost(
            get_review_reply_list_url(review),
            {'body_top': 'Test'},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_replies_with_site(self):
        """Testing the POST review-requsets/<id>/reviews/<id>/replies/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        self._login_user(local_site=True)

        rsp = self.apiPost(
            get_review_reply_list_url(review, self.local_site_name),
            {'body_top': 'Test'},
            expected_mimetype=review_reply_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_replies_with_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        rsp = self.apiPost(
            get_review_reply_list_url(review, self.local_site_name),
            {'body_top': 'Test'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_replies_with_body_top(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with body_top"""
        body_top = 'My Body Top'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost(
            get_review_reply_list_url(review),
            {'body_top': body_top},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_top, body_top)

    def test_post_replies_with_body_bottom(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with body_bottom"""
        body_bottom = 'My Body Bottom'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost(
            get_review_reply_list_url(review),
            {'body_bottom': body_bottom},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_bottom, body_bottom)

    def test_put_reply(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

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
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

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
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = True
        reply.base_reply_to = review
        reply.save()

        rsp = self.apiPut(
            get_review_reply_item_url(review, reply.id, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reply_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/?public=1 API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

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

    def test_delete_reply(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

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
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = False
        reply.base_reply_to = review
        reply.save()

        self._login_user(local_site=True)
        self.apiDelete(get_review_reply_item_url(review, reply.id,
                                                 self.local_site_name))
        self.assertEqual(review.replies.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_reply_with_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = False
        reply.base_reply_to = review
        reply.save()

        rsp = self.apiDelete(get_review_reply_item_url(review, reply.id,
                                                       self.local_site_name),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
