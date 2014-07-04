from __future__ import unicode_literals

from django.utils import six
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import ReviewRequestDraft, Screenshot
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (screenshot_item_mimetype,
                                                screenshot_draft_item_mimetype,
                                                screenshot_draft_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_screenshot_draft_item_url,
                                           get_screenshot_draft_list_url,
                                           get_screenshot_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the DraftScreenshotResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/screenshots/'
    resource = resources.draft_screenshot

    def compare_item(self, item_rsp, screenshot):
        self.assertEqual(item_rsp['id'], screenshot.pk)
        self.assertEqual(item_rsp['caption'], screenshot.caption)

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

            # The first screenshot will be automatically copied into the draft.
            ReviewRequestDraft.create(review_request)

            items.append(self.create_screenshot(review_request, draft=True))
        else:
            items = []

        return (get_screenshot_draft_list_url(review_request, local_site_name),
                screenshot_draft_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        return (get_screenshot_list_url(review_request, local_site_name),
                screenshot_item_mimetype,
                {
                    'caption': 'Trophy',
                    'path': open(self._getTrophyFilename(), 'r'),
                },
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        screenshots = list(review_request.get_draft().screenshots.all())
        self.assertEqual(len(screenshots), 1)

        screenshot = screenshots[0]
        self.assertEqual(screenshot.draft_caption, 'Trophy')
        self.assertEqual(screenshot.caption, '')

    def test_post_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API
        with Permission Denied error
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        f = open(self._getTrophyFilename(), "r")
        rsp = self.api_post(
            get_screenshot_draft_list_url(review_request),
            {
                'caption': 'Trophy',
                'path': f,
            },
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the DraftScreenshotResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/screenshots/<id>/'
    resource = resources.draft_screenshot

    def compare_item(self, item_rsp, screenshot):
        self.assertEqual(item_rsp['id'], screenshot.pk)
        self.assertEqual(item_rsp['caption'], screenshot.caption)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request, draft=True)

        return (get_screenshot_draft_item_url(review_request, screenshot.pk,
                                              local_site_name),
                [screenshot, review_request])

    def check_delete_result(self, user, screenshot, review_request):
        self.assertNotIn(screenshot,
                         review_request.get_draft().screenshots.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        screenshot = self.create_screenshot(review_request, draft=True)

        return (get_screenshot_draft_item_url(review_request, screenshot.pk,
                                              local_site_name),
                screenshot_draft_item_mimetype,
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
        screenshot = self.create_screenshot(review_request, draft=True)

        if put_valid_data:
            put_data = {
                'caption': 'The new caption',
            }
        else:
            put_data = {}

        return (get_screenshot_draft_item_url(review_request, screenshot.pk,
                                              local_site_name),
                screenshot_draft_item_mimetype,
                put_data,
                screenshot,
                [review_request])

    def check_put_result(self, user, item_rsp, screenshot, review_request):
        screenshot = Screenshot.objects.get(pk=screenshot.pk)
        self.assertEqual(screenshot.draft_caption, 'The new caption')
        self.assertNotIn(screenshot, review_request.screenshots.all())
        self.assertIn(screenshot, review_request.get_draft().screenshots.all())
