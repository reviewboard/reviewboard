from __future__ import print_function, unicode_literals

import json
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils import six
from djblets.siteconfig.models import SiteConfiguration

from reviewboard import initialize
from reviewboard.notifications.tests import EmailTestHelper
from reviewboard.reviews.models import Review
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase
from reviewboard.webapi.tests.mimetypes import (
    screenshot_comment_item_mimetype,
    error_mimetype,
    file_attachment_comment_item_mimetype,
    review_diff_comment_item_mimetype)
from reviewboard.webapi.tests.urls import (
    get_review_diff_comment_list_url,
    get_review_file_attachment_comment_list_url,
    get_screenshot_comment_list_url,
    get_screenshot_list_url)


class BaseWebAPITestCase(TestCase, EmailTestHelper):
    sample_api_url = None

    error_mimetype = error_mimetype

    def setUp(self):
        super(BaseWebAPITestCase, self).setUp()

        initialize()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set("mail_send_review_mail", False)
        self.siteconfig.set("auth_require_sitewide_login", False)
        self.siteconfig.save()
        self._saved_siteconfig_settings = self.siteconfig.settings.copy()

        mail.outbox = []

        fixtures = getattr(self, 'fixtures', [])

        if 'test_users' in fixtures:
            self.client.login(username="grumpy", password="grumpy")
            self.user = User.objects.get(username="grumpy")

        self.base_url = 'http://testserver'

    def tearDown(self):
        super(BaseWebAPITestCase, self).tearDown()

        self.client.logout()

        if self.siteconfig.settings != self._saved_siteconfig_settings:
            self.siteconfig.settings = self._saved_siteconfig_settings
            self.siteconfig.save()

    def shortDescription(self):
        desc = super(BaseWebAPITestCase, self).shortDescription()

        if self.sample_api_url:
            test_method = getattr(self, self._testMethodName)

            if getattr(test_method, 'is_test_template', False):
                desc = desc.replace('<URL>', self.sample_api_url)

        return desc

    def api_func_wrapper(self, api_func, path, query, expected_status,
                         follow_redirects, expected_redirects,
                         expected_mimetype, content_type='', extra={}):
        response = api_func(path, query, follow=follow_redirects,
                            content_type=content_type, extra=extra,
                            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        print("Raw response: %s" % response.content)

        self.assertEqual(response.status_code, expected_status)

        if expected_status >= 400:
            self.assertEqual(expected_mimetype, None)

            if expected_status != 405:
                self.assertEqual(response['Content-Type'], self.error_mimetype)
        elif expected_status != 302:
            self.assertNotEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], expected_mimetype)

        if expected_redirects:
            self.assertEqual(len(response.redirect_chain),
                             len(expected_redirects))

            for redirect in expected_redirects:
                self.assertEqual(response.redirect_chain[0][0],
                                 self.base_url + expected_redirects[0])

        return response

    def api_get(self, path, query={}, follow_redirects=False,
                expected_status=200, expected_redirects=[],
                expected_headers={}, expected_mimetype=None,
                expected_json=True):
        path = self._normalize_path(path)

        print('GETing %s' % path)
        print("Query data: %s" % query)

        response = self.api_func_wrapper(
            self.client.get, path, query, expected_status, follow_redirects,
            expected_redirects, expected_mimetype,
            content_type='text/html; charset=utf-8')

        for header, value in six.iteritems(expected_headers):
            self.assertIn(header, response)
            self.assertEqual(response[header], value)

        if expected_status != 302 and expected_json:
            rsp = json.loads(response.content)
        else:
            rsp = response.content

        print("Response: %s" % rsp)

        return rsp

    def api_post_with_response(self, path, query={}, expected_status=201,
                               expected_mimetype=None):
        path = self._normalize_path(path)

        print('POSTing to %s' % path)
        print("Post data: %s" % query)
        response = self.client.post(path, query,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        print("Raw response: %s" % response.content)
        self.assertEqual(response.status_code, expected_status)

        if expected_status >= 400:
            self.assertEqual(expected_mimetype, None)

            if expected_status != 405:
                self.assertEqual(response['Content-Type'], self.error_mimetype)
        else:
            self.assertNotEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], expected_mimetype)

        return self._get_result(response, expected_status), response

    def api_post(self, *args, **kwargs):
        rsp, result = self.api_post_with_response(*args, **kwargs)

        return rsp

    def api_put(self, path, query={}, expected_status=200,
                follow_redirects=False, expected_redirects=[],
                expected_mimetype=None):
        path = self._normalize_path(path)

        print('PUTing to %s' % path)
        print("Post data: %s" % query)
        data = encode_multipart(BOUNDARY, query)

        response = self.api_func_wrapper(self.client.put, path, data,
                                         expected_status, follow_redirects,
                                         expected_redirects, expected_mimetype,
                                         content_type=MULTIPART_CONTENT)

        return self._get_result(response, expected_status)

    def api_delete(self, path, expected_status=204):
        path = self._normalize_path(path)

        print('DELETEing %s' % path)
        response = self.client.delete(path)
        print("Raw response: %s" % response.content)
        self.assertEqual(response.status_code, expected_status)

        return self._get_result(response, expected_status)

    def assertHttpOK(self, response, check_last_modified=False,
                     check_etag=False):
        self.assertEquals(response.status_code, 200)

        if check_last_modified:
            self.assertIn('Last-Modified', response)

        if check_etag:
            self.assertIn('ETag', response)

    def assertHttpNotModified(self, response):
        self.assertEquals(response.status_code, 304)
        self.assertEquals(response.content, '')

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

    def _normalize_path(self, path):
        if path.startswith(self.base_url):
            return path[len(self.base_url):]
        else:
            return path

    def _get_result(self, response, expected_status):
        if expected_status in (204, 405):
            self.assertEqual(response.content, '')
            rsp = None
        else:
            rsp = json.loads(response.content)
            print("Response: %s" % rsp)

        return rsp

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
                local_site = LocalSite.objects.get(name=self.local_site_name)
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
            get_screenshot_comment_list_url(review, local_site_name),
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

    def _getTrophyFilename(self):
        return os.path.join(settings.STATIC_ROOT, "rb", "images", "trophy.png")
