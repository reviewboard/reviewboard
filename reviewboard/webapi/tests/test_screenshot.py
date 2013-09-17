from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import screenshot_item_mimetype
from reviewboard.webapi.tests.urls import get_screenshot_list_url


class ScreenshotResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_get_screenshots_with_invalid_review_request_id(self):
        """Testing the GET review-requests/<id>/screenshots/ API
        with an invalid review request ID
        """
        screenshot_invalid_id_url = get_screenshot_list_url(999999)
        rsp = self.apiGet(screenshot_invalid_id_url, expected_status=404)

        self.assertEqual(rsp['stat'], 'fail')

    def test_post_screenshots(self):
        """Testing the POST review-requests/<id>/screenshots/ API"""
        review_request = self.create_review_request(publish=True,
                                                    submitter=self.user)

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_screenshot_list_url(review_request),
            {'path': f},
            expected_mimetype=screenshot_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_screenshots_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/screenshots/ API
        with Permission Denied error
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(
            get_screenshot_list_url(review_request),
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
        """Testing the POST review-requests/<id>/screenshots/ API
        with a local site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(submitter=user,
                                                    with_local_site=True,
                                                    publish=True)

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_screenshot_list_url(review_request, self.local_site_name),
            {'path': f},
            expected_mimetype=screenshot_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_post_screenshots_with_site_no_access(self):
        """Testing the POST review-requests/<id>/screenshots/ API
        with a local site and Permission Denied error
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(submitter=user,
                                                    with_local_site=True,
                                                    publish=True)

        self._login_user()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_screenshot_list_url(review_request, self.local_site_name),
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
