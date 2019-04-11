from __future__ import unicode_literals

from django.utils import six
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (screenshot_item_mimetype,
                                                screenshot_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.urls import (get_screenshot_list_url,
                                           get_screenshot_item_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    """Testing the ScreenshotResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/screenshots/'
    resource = resources.screenshot

    def setup_review_request_child_test(self, review_request):
        return (get_screenshot_list_url(review_request),
                screenshot_list_mimetype)

    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['caption'], comment.caption)

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
            items = [self.create_screenshot(review_request)]
        else:
            items = []

        return (get_screenshot_list_url(review_request, local_site_name),
                screenshot_list_mimetype,
                items)

    def test_get_with_invalid_review_request_id(self):
        """Testing the GET review-requests/<id>/screenshots/ API
        with an invalid review request ID
        """
        screenshot_invalid_id_url = get_screenshot_list_url(999999)
        rsp = self.api_get(screenshot_invalid_id_url, expected_status=404)

        self.assertEqual(rsp['stat'], 'fail')

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        if post_valid_data:
            post_data = {
                'path': open(self.get_sample_image_filename(), 'rb'),
            }
        else:
            post_data = {}

        return (get_screenshot_list_url(review_request, local_site_name),
                screenshot_item_mimetype,
                post_data,
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        self.assertEqual(draft.screenshots.count(), 1)
        self.assertEqual(draft.screenshots_count, 1)
        self.assertEqual(review_request.screenshots.count(), 0)
        self.assertEqual(review_request.screenshots_count, 0)

    def test_post_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/screenshots/ API
        with Permission Denied error
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        with open(self.get_sample_image_filename(), 'rb') as f:
            rsp = self.api_post(
                get_screenshot_list_url(review_request),
                {
                    'caption': 'Trophy',
                    'path': f,
                },
                expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ReviewRequestChildItemMixin, BaseWebAPITestCase):
    """Testing the ScreenshotResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/screenshots/<id>/'
    resource = resources.screenshot

    def setup_review_request_child_test(self, review_request):
        screenshot = self.create_screenshot(review_request)

        return (get_screenshot_item_url(screenshot),
                screenshot_item_mimetype)

    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['caption'], comment.caption)
        self.assertEqual(item_rsp['absolute_url'],
                         self.base_url + comment.image.url)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)

        return (get_screenshot_item_url(screenshot, local_site_name),
                [review_request, screenshot])

    def check_delete_result(self, user, review_request, screenshot):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertIn(screenshot, review_request.screenshots.all())
        self.assertIn(screenshot, draft.inactive_screenshots.all())
        self.assertNotIn(screenshot, draft.screenshots.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)

        return (get_screenshot_item_url(screenshot, local_site_name),
                screenshot_item_mimetype,
                screenshot)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request)

        return (get_screenshot_item_url(screenshot, local_site_name),
                screenshot_item_mimetype,
                {'caption': 'My new caption'},
                screenshot,
                [review_request])

    def check_put_result(self, user, item_rsp, screenshot, review_request):
        self.assertEqual(item_rsp['id'], screenshot.pk)

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertIn(screenshot, draft.screenshots.all())
