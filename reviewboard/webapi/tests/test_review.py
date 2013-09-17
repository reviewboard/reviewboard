from django.contrib.auth.models import User
from django.core import mail
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_list_mimetype,
                                                review_item_mimetype)
from reviewboard.webapi.tests.urls import (get_review_item_url,
                                           get_review_list_url)


class ReviewResourceTests(BaseWebAPITestCase):
    """Testing the ReviewResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = review_list_mimetype
    item_mimetype = review_item_mimetype

    #
    # List tests
    #

    def test_get_reviews(self):
        """Testing the GET review-requests/<id>/reviews/ API"""
        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, publish=True)

        rsp = self.apiGet(get_review_list_url(review_request),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['reviews']), 1)

    @add_fixtures(['test_site'])
    def test_get_reviews_with_site(self):
        """Testing the GET review-requests/<id>/reviews/ API
        with a local site
        """
        self.test_post_reviews_with_site(public=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        rsp = self.apiGet(get_review_list_url(review_request,
                                              self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['reviews']), review_request.reviews.count())

    @add_fixtures(['test_site'])
    def test_get_reviews_with_site_no_access(self):
        """Testing the GET review-requests/<id>/reviews/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)

        rsp = self.apiGet(get_review_list_url(review_request,
                                              self.local_site_name),
                          expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reviews_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/?counts-only=1 API"""
        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, publish=True)
        self.create_review(review_request, publish=True)

        rsp = self.apiGet(get_review_list_url(review_request), {
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_reviewrequest_reviews_with_invite_only_group_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/reviews/ API
        with invite-only group and Permission Denied error
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        group = self.create_review_group(invite_only=True)

        review_request.target_groups.add(group)
        review_request.save()

        rsp = self.apiGet(get_review_list_url(review_request),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_post_reviews(self):
        """Testing the POST review-requests/<id>/reviews/ API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        review_request = self.create_review_request(publish=True)
        mail.outbox = []

        rsp, response = self.api_post_with_response(
            get_review_list_url(review_request),
            {
                'ship_it': ship_it,
                'body_top': body_top,
                'body_bottom': body_bottom,
            },
            expected_mimetype=self.item_mimetype)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(response['Location'],
                         self.base_url +
                         get_review_item_url(review_request, review.id))

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, False)

        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_reviews_with_site(self, public=False):
        """Testing the POST review-requests/<id>/reviews/ API
        with a local site
        """
        self._login_user(local_site=True)

        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)

        mail.outbox = []

        post_data = {
            'ship_it': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
            'public': public,
        }

        rsp, response = self.api_post_with_response(
            get_review_list_url(review_request, self.local_site_name),
            post_data,
            expected_mimetype=self.item_mimetype)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        reviews = review_request.reviews.all()
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(rsp['review']['id'], review.id)

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, public)

        if public:
            self.assertEqual(len(mail.outbox), 1)
        else:
            self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_reviews_with_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)

        rsp = self.apiPost(
            get_review_list_url(review_request, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # Item tests
    #

    @add_fixtures(['test_site'])
    def test_delete_review(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API"""
        # Set up the draft to delete.
        review = self.test_put_review()
        review_request = review.review_request

        self.apiDelete(get_review_item_url(review_request, review.id))
        self.assertEqual(review_request.reviews.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_review_with_permission_denied(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API
        with Permission Denied error
        """
        # Set up the draft to delete.
        review = self.test_put_review()
        review.user = User.objects.get(username='doc')
        review.save()

        review_request = review.review_request
        old_count = review_request.reviews.count()

        self.apiDelete(get_review_item_url(review_request, review.id),
                       expected_status=403)
        self.assertEqual(review_request.reviews.count(), old_count)

    def test_delete_review_with_published_review(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API
        with pre-published review
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, username=self.user,
                                    publish=True)

        self.apiDelete(get_review_item_url(review_request, review.id),
                       expected_status=403)
        self.assertEqual(review_request.reviews.count(), 1)

    def test_delete_review_with_does_not_exist(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API
        with Does Not Exist error
        """
        review_request = self.create_review_request(publish=True)

        rsp = self.apiDelete(get_review_item_url(review_request, 919239),
                             expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_review_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API
        with a local site
        """
        review = self.test_put_review_with_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        self.apiDelete(get_review_item_url(review_request, review.id,
                                           self.local_site_name))
        self.assertEqual(review_request.reviews.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_review_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        review = self.create_review(review_request, username='doc')

        rsp = self.apiDelete(get_review_item_url(review_request, review.id,
                                                 self.local_site_name),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_review_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        self._testHttpCaching(
            get_review_item_url(review_request, review.pk),
            check_last_modified=True)

    @add_fixtures(['test_site'])
    def test_put_review(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        review_request = self.create_review_request(publish=True)
        mail.outbox = []

        rsp, response = self.api_post_with_response(
            get_review_list_url(review_request),
            expected_mimetype=self.item_mimetype)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        review_url = response['Location']

        rsp = self.apiPut(
            review_url,
            {
                'ship_it': ship_it,
                'body_top': body_top,
                'body_bottom': body_bottom,
            },
            expected_mimetype=self.item_mimetype)

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, False)

        self.assertEqual(len(mail.outbox), 0)

        # Make this easy to use in other tests.
        return review

    @add_fixtures(['test_site'])
    def test_put_review_with_site(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API
        with a local site
        """
        self._login_user(local_site=True)

        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        mail.outbox = []

        rsp, response = self.api_post_with_response(
            get_review_list_url(review_request, self.local_site_name),
            expected_mimetype=self.item_mimetype)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        review_url = response['Location']

        rsp = self.apiPut(
            review_url,
            {
                'ship_it': ship_it,
                'body_top': body_top,
                'body_bottom': body_bottom,
            },
            expected_mimetype=self.item_mimetype)

        reviews = review_request.reviews.filter(user__username='doc')
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, False)

        self.assertEqual(len(mail.outbox), 0)

        # Make this easy to use in other tests.
        return review

    @add_fixtures(['test_site'])
    def test_put_review_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)
        review = self.create_review(review_request, username='doc',
                                    publish=True)

        rsp = self.apiPut(
            get_review_item_url(review_request, review.id,
                                self.local_site_name),
            {'ship_it': True},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_review_with_published_review(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API
        with pre-published review
        """
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, username=self.user,
                                    publish=True)

        self.apiPut(
            get_review_item_url(review.review_request, review.id),
            {'ship_it': True},
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_review_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/?public=1 API"""
        body_top = "My Body Top"
        body_bottom = ""
        ship_it = True

        self.siteconfig.set('mail_send_review_mail', True)
        self.siteconfig.save()

        review_request = self.create_review_request(publish=True)
        mail.outbox = []

        review = self.create_review(review_request, user=self.user)

        self.apiPut(
            get_review_item_url(review_request, review.pk),
            {
                'public': True,
                'ship_it': ship_it,
                'body_top': body_top,
                'body_bottom': body_bottom,
            },
            expected_mimetype=self.item_mimetype)

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
