from __future__ import print_function, unicode_literals

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.utils import six
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.testing.testcases import WebAPITestCaseMixin

from reviewboard.notifications.tests.test_email_sending import EmailTestHelper
from reviewboard.reviews.models import Review
from reviewboard.testing import TestCase
from reviewboard.webapi.tests.mimetypes import (
    error_mimetype,
    file_attachment_comment_item_mimetype,
    general_comment_item_mimetype,
    review_diff_comment_item_mimetype,
    screenshot_comment_item_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_diff_comment_list_url,
    get_review_file_attachment_comment_list_url,
    get_review_general_comment_list_url,
    get_review_screenshot_comment_list_url,
    get_screenshot_list_url)


class BaseWebAPITestCase(WebAPITestCaseMixin, TestCase, EmailTestHelper):
    error_mimetype = error_mimetype

    def setUp(self):
        super(BaseWebAPITestCase, self).setUp()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set("mail_send_review_mail", False)
        self.siteconfig.set("auth_require_sitewide_login", False)
        self.siteconfig.save()
        self._saved_siteconfig_settings = self.siteconfig.settings.copy()

        mail.outbox = []

        fixtures = getattr(self, 'fixtures', None)

        if fixtures and 'test_users' in fixtures:
            self.client.login(username="grumpy", password="grumpy")
            self.user = User.objects.get(username="grumpy")

        self.base_url = 'http://testserver'

    def tearDown(self):
        super(BaseWebAPITestCase, self).tearDown()

        self.client.logout()

        if self.siteconfig.settings != self._saved_siteconfig_settings:
            self.siteconfig.settings = self._saved_siteconfig_settings
            self.siteconfig.save()

    def _testHttpCaching(self, url, check_etags=False,
                         check_last_modified=False):
        response = self.client.get(url)
        self.assertHttpOK(response, check_etag=check_etags,
                          check_last_modified=check_last_modified)

        headers = {}

        if check_etags:
            headers['HTTP_IF_NONE_MATCH'] = response['ETag']

        if check_last_modified:
            headers['HTTP_IF_MODIFIED_SINCE'] = response['Last-Modified']

        response = self.client.get(url, **headers)

        self.assertHttpNotModified(response)

    #
    # Some utility functions shared across test suites.
    #
    def _login_user(self, local_site=False, admin=False):
        """Creates a user for a test.

        The proper user will be created based on whether a valid LocalSite
        user is needed, and/or an admin user is needed.
        """
        self.client.logout()

        # doc is a member of the default LocalSite.
        username = 'doc'

        if admin:
            if local_site:
                user = User.objects.get(username=username)
                local_site = self.get_local_site(name=self.local_site_name)
                local_site.admins.add(user)
            else:
                username = 'admin'
        elif not local_site:
            # Pick a user that's not part of the default LocalSite.
            username = 'grumpy'

        self.assertTrue(self.client.login(username=username,
                                          password=username))

        return User.objects.get(username=username)

    def _postNewDiffComment(self, review_request, review_id, comment_text,
                            filediff_id=None, interfilediff_id=None,
                            first_line=10, num_lines=5, issue_opened=None,
                            issue_status=None):
        """Creates a diff comment and returns the payload response."""
        if filediff_id is None:
            diffset = review_request.diffset_history.diffsets.latest()
            filediff = diffset.files.all()[0]
            filediff_id = filediff.id

        data = {
            'filediff_id': filediff_id,
            'text': comment_text,
            'first_line': first_line,
            'num_lines': num_lines,
        }

        if interfilediff_id is not None:
            data['interfilediff_id'] = interfilediff_id

        if issue_opened is not None:
            data['issue_opened'] = issue_opened

        if issue_status is not None:
            data['issue_status'] = issue_status

        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        review = Review.objects.get(pk=review_id)

        rsp = self.api_post(
            get_review_diff_comment_list_url(review, local_site_name),
            data,
            expected_mimetype=review_diff_comment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewScreenshotComment(self, review_request, review_id, screenshot,
                                  comment_text, x, y, w, h, issue_opened=None,
                                  issue_status=None):
        """Creates a screenshot comment and returns the payload response."""
        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        post_data = {
            'screenshot_id': screenshot.id,
            'text': comment_text,
            'x': x,
            'y': y,
            'w': w,
            'h': h,
        }

        if issue_opened is not None:
            post_data['issue_opened'] = issue_opened

        if issue_status is not None:
            post_data['issue_status'] = issue_status

        review = Review.objects.get(pk=review_id)
        rsp = self.api_post(
            get_review_screenshot_comment_list_url(review, local_site_name),
            post_data,
            expected_mimetype=screenshot_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _delete_screenshot(self, review_request, screenshot):
        """Deletes a screenshot.

        This does not return anything, because DELETE requests don't return a
        response with a payload.
        """
        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        self.api_delete(
            get_screenshot_list_url(review_request, local_site_name) +
            six.text_type(screenshot.id) + '/')

    def _postNewFileAttachmentComment(self, review_request, review_id,
                                      file_attachment, comment_text,
                                      issue_opened=None,
                                      issue_status=None,
                                      extra_fields={}):
        """Creates a file attachment comment.

        This returns the response from the API call to create the comment."""
        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        post_data = {
            'file_attachment_id': file_attachment.id,
            'text': comment_text,
        }
        post_data.update(extra_fields)

        if issue_opened is not None:
            post_data['issue_opened'] = issue_opened

        if issue_status is not None:
            post_data['issue_status'] = issue_status

        review = Review.objects.get(pk=review_id)
        rsp = self.api_post(
            get_review_file_attachment_comment_list_url(review,
                                                        local_site_name),
            post_data,
            expected_mimetype=file_attachment_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _post_new_general_comment(self, review_request, review_id,
                                  comment_text,
                                  issue_opened=None,
                                  issue_status=None):
        """Creates a general comment.

        This returns the response from the API call to create the comment.
        """
        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        post_data = {
            'text': comment_text,
        }

        if issue_opened is not None:
            post_data['issue_opened'] = issue_opened

        if issue_status is not None:
            post_data['issue_status'] = issue_status

        review = Review.objects.get(pk=review_id)
        rsp = self.api_post(
            get_review_general_comment_list_url(review, local_site_name),
            post_data,
            expected_mimetype=general_comment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def get_sample_image_filename(self):
        return os.path.join(settings.STATIC_ROOT, 'rb', 'images', 'logo.png')
