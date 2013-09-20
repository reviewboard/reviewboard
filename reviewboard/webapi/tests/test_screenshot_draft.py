from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Screenshot
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (screenshot_item_mimetype,
                                                screenshot_draft_item_mimetype)
from reviewboard.webapi.tests.urls import (get_screenshot_draft_item_url,
                                           get_screenshot_draft_list_url,
                                           get_screenshot_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the ScreenshotDraftResource list APIs."""
    fixtures = ['test_users']

    #
    # HTTP POST tests
    #

    def test_post(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API"""
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        f = open(self._getTrophyFilename(), "r")
        rsp = self.apiPost(
            get_screenshot_list_url(review_request),
            {'path': f},
            expected_mimetype=screenshot_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API
        with Permission Denied error
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        f = open(self._getTrophyFilename(), "r")
        rsp = self.apiPost(
            get_screenshot_draft_list_url(review_request),
            {
                'caption': 'Trophy',
                'path': f,
            },
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_post_with_site(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API
        with a local site
        """
        self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True)

        f = open(self._getTrophyFilename(), 'r')

        post_data = {
            'path': f,
            'caption': 'Trophy',
        }

        rsp = self.apiPost(
            get_screenshot_draft_list_url(review_request,
                                          self.local_site_name),
            post_data,
            expected_mimetype=screenshot_draft_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft_screenshot']['caption'], 'Trophy')

        draft = review_request.get_draft(User.objects.get(username='doc'))
        self.assertNotEqual(draft, None)

        return review_request, rsp['draft_screenshot']['id']

    @add_fixtures(['test_site'])
    def test_post_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API
        with a local site and Permission Denied error
        """
        review_request = self.create_review_request(with_local_site=True)

        f = open(self._getTrophyFilename(), 'r')
        rsp = self.apiPost(
            get_screenshot_draft_list_url(review_request,
                                          self.local_site_name),
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ScreenshotDraftResource item APIs."""
    fixtures = ['test_users']

    #
    # HTTP PUT tests
    #

    def test_put(self):
        """Testing the PUT review-requests/<id>/draft/screenshots/<id>/ API"""
        draft_caption = 'The new caption'

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        f = open(self._getTrophyFilename(), "r")
        rsp = self.apiPost(
            get_screenshot_draft_list_url(review_request),
            {
                'caption': 'Trophy',
                'path': f,
            },
            expected_mimetype=screenshot_draft_item_mimetype)
        f.close()
        review_request.publish(self.user)

        screenshot = Screenshot.objects.get(pk=rsp['draft_screenshot']['id'])

        # Now modify the caption.
        rsp = self.apiPut(
            get_screenshot_draft_item_url(review_request, screenshot.id),
            {'caption': draft_caption},
            expected_mimetype=screenshot_draft_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(self.user)
        self.assertNotEqual(draft, None)

        screenshot = Screenshot.objects.get(pk=screenshot.id)
        self.assertEqual(screenshot.draft_caption, draft_caption)

    @add_fixtures(['test_site'])
    def test_put_with_site(self):
        """Testing the PUT review-requests/<id>/draft/screenshots/<id>/ API
        with a local site
        """
        draft_caption = 'The new caption'
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(submitter=user,
                                                    with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)

        rsp = self.apiPut(
            get_screenshot_draft_item_url(review_request, screenshot.pk,
                                          self.local_site_name),
            {'caption': draft_caption},
            expected_mimetype=screenshot_draft_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(user)
        self.assertNotEqual(draft, None)

        screenshot = Screenshot.objects.get(pk=screenshot.pk)
        self.assertEqual(screenshot.draft_caption, draft_caption)

    @add_fixtures(['test_site'])
    def test_put_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/draft/screenshots/<id>/ API
        with a local site and Permission Denied error
        """
        user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter=user,
                                                    with_local_site=True,
                                                    publish=True)
        screenshot = self.create_screenshot(review_request)

        self._login_user()

        rsp = self.apiPut(
            get_screenshot_draft_item_url(review_request, screenshot.pk,
                                          self.local_site_name),
            {'caption': 'test'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
