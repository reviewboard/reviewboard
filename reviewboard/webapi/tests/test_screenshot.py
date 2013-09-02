from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class ScreenshotResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('screenshots')
    item_mimetype = _build_mimetype('screenshot')

    def test_get_screenshots_with_invalid_review_request_id(self):
        """Testing the GET review-requests/<id>/screenshots/ API with an invalid review request ID"""
        screenshot_invalid_id_url = local_site_reverse(
            'screenshots-resource',
            kwargs={
                'review_request_id': 999999,
            })

        rsp = self.apiGet(screenshot_invalid_id_url, expected_status=404)

        self.assertEqual(rsp['stat'], 'fail')

    def test_post_screenshots(self):
        """Testing the POST review-requests/<id>/screenshots/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        screenshots_url = rsp['review_request']['links']['screenshots']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            screenshots_url,
            {'path': f},
            expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_reviewrequests'])
    def test_post_screenshots_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/screenshots/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            public=True, local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(
            self.get_list_url(review_request),
            {
                'caption': 'Trophy',
                'path': f,
            },
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _test_review_request_with_site(self):
        self._login_user(local_site=True)

        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')

        return rsp['review_request']['links']['screenshots']['href']

    @add_fixtures(['test_site'])
    def test_post_screenshots_with_site(self):
        """Testing the POST review-requests/<id>/screenshots/ API with a local site"""
        screenshots_url = self._test_review_request_with_site()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            screenshots_url,
            {'path': f},
            expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_post_screenshots_with_site_no_access(self):
        """Testing the POST review-requests/<id>/screenshots/ API with a local site and Permission Denied error"""
        screenshots_url = self._test_review_request_with_site()
        self._login_user()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            screenshots_url,
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @classmethod
    def get_list_url(cls, review_request, local_site_name=None):
        return local_site_reverse(
            'screenshots-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })
