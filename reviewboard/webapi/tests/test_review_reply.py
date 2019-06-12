from __future__ import unicode_literals

from django.core import mail
from django.utils import six

from reviewboard.reviews.models import Review
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_reply_item_mimetype,
                                                review_reply_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_review import (ReviewItemMixin,
                                                    ReviewListMixin)
from reviewboard.webapi.tests.urls import (get_review_reply_item_url,
                                           get_review_reply_list_url)


class BaseResourceTestCase(BaseWebAPITestCase):
    def _create_test_review(self, with_local_site=False):
        review_request = self.create_review_request(
            submitter=self.user,
            with_local_site=with_local_site)
        file_attachment = self.create_file_attachment(review_request)
        review_request.publish(review_request.submitter)

        review = self.create_review(review_request, publish=True)
        self.create_file_attachment_comment(review, file_attachment)

        return review


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewListMixin, ReviewRequestChildListMixin,
                        BaseResourceTestCase):
    """Testing the ReviewReplyResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/reviews/<id>/replies/'
    resource = resources.review_reply

    def setup_review_request_child_test(self, review_request):
        review = self.create_review(review_request, publish=True)

        return (get_review_reply_list_url(review),
                review_reply_list_mimetype)

    def compare_item(self, item_rsp, reply):
        self.assertEqual(item_rsp['id'], reply.pk)
        self.assertEqual(item_rsp['body_top'], reply.body_top)
        self.assertEqual(item_rsp['body_bottom'], reply.body_bottom)

        if reply.body_top_rich_text:
            self.assertEqual(item_rsp['body_top_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_top_text_type'], 'plain')

        if reply.body_bottom_rich_text:
            self.assertEqual(item_rsp['body_bottom_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_bottom_text_type'], 'plain')

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        review = self.create_review(review_request, publish=True)

        if populate_items:
            items = [self.create_reply(review, publish=True)]
        else:
            items = []

        return (get_review_reply_list_url(review, local_site_name),
                review_reply_list_mimetype,
                items)

    def test_get_with_counts_only(self):
        """Testing the
        GET review-requests/<id>/reviews/<id>/replies/?counts-only=1 API
        """
        review = self._create_test_review()
        self.create_reply(review, user=self.user, publish=True)

        rsp = self.api_get(
            '%s?counts-only=1' % get_review_reply_list_url(review),
            expected_mimetype=review_reply_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 1)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        review = self.create_review(review_request, publish=True)

        return (get_review_reply_list_url(review, local_site_name),
                review_reply_item_mimetype,
                {},
                [review])

    def check_post_result(self, user, rsp, review):
        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertFalse(reply.body_top_rich_text)
        self.compare_item(rsp['reply'], reply)

    def test_post_with_body_top(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API
        with body_top
        """
        body_top = 'My Body Top'

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp = self.api_post(
            get_review_reply_list_url(review),
            {'body_top': body_top},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_top, body_top)

    def test_post_with_body_bottom(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API
        with body_bottom
        """
        body_bottom = 'My Body Bottom'

        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp = self.api_post(
            get_review_reply_list_url(review),
            {'body_bottom': body_bottom},
            expected_mimetype=review_reply_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_bottom, body_bottom)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ReviewItemMixin, ReviewRequestChildItemMixin,
                        BaseResourceTestCase):
    """Testing the ReviewReplyResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/reviews/<id>/replies/<id>/'
    resource = resources.review_reply

    def setup_review_request_child_test(self, review_request):
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review, publish=True)

        return (get_review_reply_item_url(review, reply.pk),
                review_reply_item_mimetype)

    def compare_item(self, item_rsp, reply):
        self.assertEqual(item_rsp['id'], reply.pk)
        self.assertEqual(item_rsp['body_top'], reply.body_top)
        self.assertEqual(item_rsp['body_bottom'], reply.body_bottom)

        if reply.body_top_rich_text:
            self.assertEqual(item_rsp['body_top_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_top_text_type'], 'plain')

        if reply.body_bottom_rich_text:
            self.assertEqual(item_rsp['body_bottom_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_bottom_text_type'], 'plain')

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        review = self.create_review(review_request, user=user, publish=True)
        reply = self.create_reply(review, user=user)

        return (get_review_reply_item_url(review, reply.pk, local_site_name),
                [reply, review])

    def check_delete_result(self, user, reply, review):
        self.assertNotIn(reply, review.replies.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        review = self.create_review(review_request, user=user, publish=True)
        reply = self.create_reply(review, user=user)

        return (get_review_reply_item_url(review, reply.pk, local_site_name),
                review_reply_item_mimetype,
                reply)

    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        reply = self.create_reply(review, publish=True)

        self._testHttpCaching(
            get_review_reply_item_url(reply.base_reply_to, reply.id),
            check_etags=True)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        review = self.create_review(review_request, user=user, publish=True)
        reply = self.create_reply(review, user=user)

        return (get_review_reply_item_url(review, reply.pk, local_site_name),
                review_reply_item_mimetype,
                {'body_top': 'New body top'},
                reply,
                [])

    def check_put_result(self, user, item_rsp, reply, *args):
        self.assertEqual(item_rsp['id'], reply.pk)
        self.assertEqual(item_rsp['body_top'], 'New body top')
        self.assertEqual(item_rsp['body_top_text_type'], 'plain')

        reply = Review.objects.get(pk=reply.pk)
        self.compare_item(item_rsp, reply)

    def test_put_with_publish(self):
        """Testing the
        PUT review-requests/<id>/reviews/<id>/replies/<id>/?public=1 API
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        rsp, response = self.api_post_with_response(
            get_review_reply_list_url(review),
            expected_mimetype=review_reply_item_mimetype)

        self.assertIn('Location', response)
        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        with self.siteconfig_settings({'mail_send_review_mail': True},
                                      reload_settings=False):
            rsp = self.api_put(
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

    def test_put_with_publish_and_trivial(self):
        """Testing the PUT review-requests/<id>/draft/ API with trivial
        changes
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        review = self.create_review(review_request, publish=True)

        rsp, response = self.api_post_with_response(
            get_review_reply_list_url(review),
            expected_mimetype=review_reply_item_mimetype)

        self.assertIn('Location', response)
        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        with self.siteconfig_settings({'mail_send_review_mail': True},
                                      reload_settings=False):
            rsp = self.api_put(
                response['Location'],
                {
                    'body_top': 'Test',
                    'public': True,
                    'trivial': True
                },
                expected_mimetype=review_reply_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('reply', rsp)
        self.assertIn('id', rsp['reply'])

        reply = Review.objects.get(pk=rsp['reply']['id'])

        self.assertTrue(reply.public)

        self.assertEqual(len(mail.outbox), 0)
