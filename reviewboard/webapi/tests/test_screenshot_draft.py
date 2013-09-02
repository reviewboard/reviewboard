from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import ReviewRequest, Screenshot
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (screenshot_item_mimetype,
                                                screenshot_draft_item_mimetype)
from reviewboard.webapi.tests.urls import (get_screenshot_draft_item_url,
                                           get_screenshot_draft_list_url)


class ScreenshotDraftResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotDraftResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_post_screenshots(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        screenshots_url = rsp['review_request']['links']['screenshots']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            screenshots_url,
            {'path': f},
            expected_mimetype=screenshot_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_reviewrequests'])
    def test_post_screenshots_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            public=True, local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
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
    def test_post_screenshots_with_site(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API with a local site"""
        self._login_user(local_site=True)

        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)

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

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_screenshots_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_screenshot_draft_list_url(review_request,
                                          self.local_site_name),
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_screenshot(self):
        """Testing the PUT review-requests/<id>/draft/screenshots/<id>/ API"""
        draft_caption = 'The new caption'

        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
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
    def test_put_screenshot_with_site(self):
        """Testing the PUT review-requests/<id>/draft/screenshots/<id>/ API with a local site"""
        draft_caption = 'The new caption'
        user = User.objects.get(username='doc')

        review_request, screenshot_id = self.test_post_screenshots_with_site()
        review_request.publish(user)

        rsp = self.apiPut(
            get_screenshot_draft_item_url(review_request, screenshot_id,
                                          self.local_site_name),
            {'caption': draft_caption},
            expected_mimetype=screenshot_draft_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(user)
        self.assertNotEqual(draft, None)

        screenshot = Screenshot.objects.get(pk=screenshot_id)
        self.assertEqual(screenshot.draft_caption, draft_caption)

    @add_fixtures(['test_site'])
    def test_put_screenshot_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/draft/screenshots/<id>/ API with a local site and Permission Denied error"""
        review_request, screenshot_id = self.test_post_screenshots_with_site()
        review_request.publish(User.objects.get(username='doc'))

        self._login_user()

        rsp = self.apiPut(
            get_screenshot_draft_item_url(review_request, screenshot_id,
                                          self.local_site_name),
            {'caption': 'test'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
