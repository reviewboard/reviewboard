from __future__ import unicode_literals

from django.core import mail
from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.reviews.models import Review
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_list_mimetype,
                                                review_item_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_review import (ReviewItemMixin,
                                                    ReviewListMixin)
from reviewboard.webapi.tests.urls import (get_review_item_url,
                                           get_review_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewListMixin, ReviewRequestChildListMixin,
                        BaseWebAPITestCase):
    """Testing the ReviewResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/reviews/'
    resource = resources.review

    def setup_review_request_child_test(self, review_request):
        return (get_review_list_url(review_request),
                review_list_mimetype)

    def compare_item(self, item_rsp, review):
        self.assertEqual(item_rsp['id'], review.pk)
        self.assertEqual(item_rsp['ship_it'], review.ship_it)
        self.assertEqual(item_rsp['body_top'], review.body_top)
        self.assertEqual(item_rsp['body_bottom'], review.body_bottom)

        if review.body_top_rich_text:
            self.assertEqual(item_rsp['body_top_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_top_text_type'], 'plain')

        if review.body_bottom_rich_text:
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

        if populate_items:
            items = [self.create_review(review_request, publish=True)]
        else:
            items = []

        return (get_review_list_url(review_request, local_site_name),
                review_list_mimetype,
                items)

    def test_get_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/?counts-only=1 API"""
        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, publish=True)
        self.create_review(review_request, publish=True)

        rsp = self.api_get(get_review_list_url(review_request), {
            'counts-only': 1,
        }, expected_mimetype=review_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_with_invite_only_group_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/reviews/ API
        with invite-only group and Permission Denied error
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        group = self.create_review_group(invite_only=True)

        review_request.target_groups.add(group)
        review_request.save()

        rsp = self.api_get(get_review_list_url(review_request),
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        return (get_review_list_url(review_request, local_site_name),
                review_item_mimetype,
                {
                    'ship_it': True,
                    'body_top': 'My body top',
                    'body_bottom': 'My body bottom',
                },
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        review = Review.objects.get(pk=rsp['review']['id'])
        self.assertFalse(review.rich_text)
        self.compare_item(rsp['review'], review)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ReviewItemMixin, ReviewRequestChildItemMixin,
                        BaseWebAPITestCase):
    """Testing the ReviewResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/reviews/<id>/'
    resource = resources.review

    def setup_review_request_child_test(self, review_request):
        review = self.create_review(review_request, publish=True)

        return (get_review_item_url(review_request, review.pk),
                review_item_mimetype)

    def compare_item(self, item_rsp, review):
        self.assertEqual(item_rsp['id'], review.pk)
        self.assertEqual(item_rsp['ship_it'], review.ship_it)
        self.assertEqual(item_rsp['body_top'], review.body_top)
        self.assertEqual(item_rsp['body_bottom'], review.body_bottom)

        if review.body_top_rich_text:
            self.assertEqual(item_rsp['body_top_text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['body_top_text_type'], 'plain')

        if review.body_bottom_rich_text:
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
        review = self.create_review(review_request, user=user)

        return (get_review_item_url(review_request, review.pk,
                                    local_site_name),
                [review, review_request])

    def check_delete_result(self, user, review, review_request):
        self.assertNotIn(review, review_request.reviews.all())

    def test_delete_with_published_review(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API
        with pre-published review
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)

        self.api_delete(get_review_item_url(review_request, review.id),
                        expected_status=403)
        self.assertEqual(review_request.reviews.count(), 1)

    def test_delete_with_does_not_exist(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API
        with Does Not Exist error
        """
        review_request = self.create_review_request(publish=True)

        rsp = self.api_delete(get_review_item_url(review_request, 919239),
                              expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        review = self.create_review(review_request, user=user)

        return (get_review_item_url(review_request, review.pk,
                                    local_site_name),
                review_item_mimetype,
                review)

    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        self._testHttpCaching(
            get_review_item_url(review_request, review.pk),
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
        review = self.create_review(review_request, user=user)

        return (get_review_item_url(review_request, review.pk,
                                    local_site_name),
                review_item_mimetype,
                {
                    'body_top': 'New body top',
                },
                review,
                [])

    def check_put_result(self, user, item_rsp, review, *args):
        self.assertEqual(item_rsp['id'], review.pk)
        self.assertEqual(item_rsp['body_top'], 'New body top')
        self.assertEqual(item_rsp['body_top_text_type'], 'plain')
        self.assertEqual(item_rsp['body_bottom_text_type'], 'plain')

        review = Review.objects.get(pk=review.pk)
        self.compare_item(item_rsp, review)

    def test_put_with_published_review(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API
        with pre-published review
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, user=self.user,
                                    publish=True)

        self.api_put(
            get_review_item_url(review_request, review.id),
            {'ship_it': True},
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/?public=1 API"""
        body_top = "My Body Top"
        body_bottom = ""
        ship_it = True

        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        review_request = self.create_review_request(publish=True)
        mail.outbox = []

        review = self.create_review(review_request, user=self.user)

        self.api_put(
            get_review_item_url(review_request, review.pk),
            {
                'public': True,
                'ship_it': ship_it,
                'body_top': body_top,
                'body_bottom': body_bottom,
            },
            expected_mimetype=review_item_mimetype)

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, True)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         'Re: Review Request %s: %s'
                         % (review_request.display_id, review_request.summary))
        self.assertValidRecipients([
            review_request.submitter.username,
            self.user.username,
        ])
