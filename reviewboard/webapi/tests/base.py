import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.utils import simplejson
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.testcases import TestCase

from reviewboard import initialize, scmtools
from reviewboard.notifications.tests import EmailTestHelper
from reviewboard.reviews.models import Review
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite


def _build_mimetype(resource_name, fmt='json'):
    return 'application/vnd.reviewboard.org.%s+%s' % (resource_name, fmt)


class BaseWebAPITestCase(TestCase, EmailTestHelper):
    local_site_name = 'local-site-1'

    error_mimetype = _build_mimetype('error')

    def setUp(self):
        initialize()

        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set("mail_send_review_mail", True)
        self.siteconfig.set("auth_require_sitewide_login", False)
        self.siteconfig.save()
        self._saved_siteconfig_settings = self.siteconfig.settings.copy()

        mail.outbox = []

        fixtures = getattr(self, 'fixtures', [])

        if 'test_scmtools' in fixtures:
            svn_repo_path = os.path.join(os.path.dirname(scmtools.__file__),
                                         'testdata', 'svn_repo')
            tool = Tool.objects.get(name='Subversion')
            self.repository = Repository(name='Subversion SVN',
                                         path='file://' + svn_repo_path,
                                         tool=tool)
            self.repository.save()

        if 'test_users' in fixtures:
            self.client.login(username="grumpy", password="grumpy")
            self.user = User.objects.get(username="grumpy")

        self.base_url = 'http://testserver'

    def tearDown(self):
        self.client.logout()

        if self.siteconfig.settings != self._saved_siteconfig_settings:
            self.siteconfig.settings = self._saved_siteconfig_settings
            self.siteconfig.save()

    def api_func_wrapper(self, api_func, path, query, expected_status,
                         follow_redirects, expected_redirects,
                         expected_mimetype):
        response = api_func(path, query, follow=follow_redirects)
        self.assertEqual(response.status_code, expected_status)

        if expected_status >= 400:
            self.assertEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], self.error_mimetype)
        else:
            self.assertNotEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], expected_mimetype)

        if expected_redirects:
            self.assertEqual(len(response.redirect_chain),
                             len(expected_redirects))

            for redirect in expected_redirects:
                self.assertEqual(response.redirect_chain[0][0],
                                 self.base_url + expected_redirects[0])

        return response

    def apiGet(self, path, query={}, follow_redirects=False,
               expected_status=200, expected_redirects=[],
               expected_headers=[], expected_mimetype=None):
        path = self._normalize_path(path)

        print 'GETing %s' % path
        print "Query data: %s" % query

        response = self.api_func_wrapper(self.client.get, path, query,
                                         expected_status, follow_redirects,
                                         expected_redirects, expected_mimetype)

        print "Raw response: %s" % response.content

        for header in expected_headers:
            self.assertTrue(header in response)

        rsp = simplejson.loads(response.content)
        print "Response: %s" % rsp

        return rsp

    def api_post_with_response(self, path, query={}, expected_status=201,
                               expected_mimetype=None):
        path = self._normalize_path(path)

        print 'POSTing to %s' % path
        print "Post data: %s" % query
        response = self.client.post(path, query,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        print "Raw response: %s" % response.content
        self.assertEqual(response.status_code, expected_status)

        if expected_status >= 400:
            self.assertEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], self.error_mimetype)
        else:
            self.assertNotEqual(expected_mimetype, None)
            self.assertEqual(response['Content-Type'], expected_mimetype)

        return self._get_result(response, expected_status), response

    def apiPost(self, *args, **kwargs):
        rsp, result = self.api_post_with_response(*args, **kwargs)

        return rsp

    def apiPut(self, path, query={}, expected_status=200,
               follow_redirects=False, expected_redirects=[],
               expected_mimetype=None):
        path = self._normalize_path(path)

        print 'PUTing to %s' % path
        print "Post data: %s" % query
        response = self.api_func_wrapper(self.client.put, path, query,
                                         expected_status, follow_redirects,
                                         expected_redirects, expected_mimetype)
        print "Raw response: %s" % response.content

        return self._get_result(response, expected_status)

    def apiDelete(self, path, expected_status=204):
        path = self._normalize_path(path)

        print 'DELETEing %s' % path
        response = self.client.delete(path)
        print "Raw response: %s" % response.content
        self.assertEqual(response.status_code, expected_status)

        return self._get_result(response, expected_status)

    def assertHttpOK(self, response, check_last_modified=False,
                     check_etag=False):
        self.assertEquals(response.status_code, 200)

        if check_last_modified:
            self.assertTrue('Last-Modified' in response)

        if check_etag:
            self.assertTrue('ETag' in response)

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
            headers['If-None-Match'] = response['ETag']

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
        if expected_status == 204:
            self.assertEqual(response.content, '')
            rsp = None
        else:
            rsp = simplejson.loads(response.content)
            print "Response: %s" % rsp

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

        self.assertTrue(self.client.login(username=username, password=username))

        return User.objects.get(username=username)

    def _postNewReviewRequest(self, local_site_name=None,
                              repository=None):
        """Creates a review request and returns the payload response."""
        from reviewboard.webapi.tests.test_repository import \
            RepositoryResourceTests
        from reviewboard.webapi.tests.test_review_request import \
            ReviewRequestResourceTests

        if not repository:
            repository = self.repository

        rsp = self.apiPost(
            ReviewRequestResourceTests.get_list_url(local_site_name),
            {'repository': repository.path},
            expected_mimetype=ReviewRequestResourceTests.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['repository']['href'],
            self.base_url +
            RepositoryResourceTests.get_item_url(repository.id,
                                                 local_site_name))

        return rsp

    def _postNewReview(self, review_request, body_top="",
                       body_bottom=""):
        """Creates a review and returns the payload response."""
        from reviewboard.webapi.tests.test_review import ReviewResourceTests

        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        post_data = {
            'body_top': body_top,
            'body_bottom': body_bottom,
        }

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request, local_site_name),
            post_data,
            expected_mimetype=ReviewResourceTests.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review']['body_top'], body_top)
        self.assertEqual(rsp['review']['body_bottom'], body_bottom)

        return rsp

    def _postNewDiffComment(self, review_request, review_id, comment_text,
                            filediff_id=None, interfilediff_id=None,
                            first_line=10, num_lines=5, issue_opened=None,
                            issue_status=None):
        """Creates a diff comment and returns the payload response."""
        from reviewboard.webapi.tests.test_review_comment import \
            ReviewCommentResourceTests

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

        rsp = self.apiPost(
            ReviewCommentResourceTests.get_list_url(review, local_site_name),
            data,
            expected_mimetype=ReviewCommentResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewScreenshotComment(self, review_request, review_id, screenshot,
                                  comment_text, x, y, w, h, issue_opened=None,
                                  issue_status=None):
        """Creates a screenshot comment and returns the payload response."""
        from reviewboard.webapi.tests.test_draft_review_screenshot_comment \
            import DraftReviewScreenshotCommentResourceTests

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
        rsp = self.apiPost(
            DraftReviewScreenshotCommentResourceTests.get_list_url(
                review, local_site_name),
            post_data,
            expected_mimetype=
                DraftReviewScreenshotCommentResourceTests.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewScreenshot(self, review_request):
        """Creates a screenshot and returns the payload response."""
        from reviewboard.webapi.tests.test_screenshot import \
            ScreenshotResourceTests

        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)

        post_data = {
            'path': f,
        }

        rsp = self.apiPost(
            ScreenshotResourceTests.get_list_url(review_request,
                                                 local_site_name),
            post_data,
            expected_mimetype=ScreenshotResourceTests.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _delete_screenshot(self, review_request, screenshot):
        """Deletes a screenshot but does not return, as deletes don't return a
        payload response.
        """
        from reviewboard.webapi.tests.test_screenshot import \
            ScreenshotResourceTests

        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        self.apiDelete(ScreenshotResourceTests.get_list_url(
            review_request, local_site_name) + str(screenshot.id) + '/')

    def _postNewFileAttachmentComment(self, review_request, review_id,
                                      file_attachment, comment_text,
                                      issue_opened=None,
                                      issue_status=None,
                                      extra_fields={}):
        """Creates a file attachment comment and returns the payload response."""
        from reviewboard.webapi.tests.test_draft_review_file_attachment_comment \
            import DraftReviewFileAttachmentCommentResourceTests

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
        rsp = self.apiPost(
            DraftReviewFileAttachmentCommentResourceTests.get_list_url(
                review, local_site_name),
            post_data,
            expected_mimetype=
                DraftReviewFileAttachmentCommentResourceTests.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewFileAttachment(self, review_request):
        """Creates a file_attachment and returns the payload response."""
        from reviewboard.webapi.tests.test_file_attachment import \
            FileAttachmentResourceTests

        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)

        post_data = {
            'path': f,
        }

        rsp = self.apiPost(
            FileAttachmentResourceTests.get_list_url(review_request,
                                                     local_site_name),
            post_data,
            expected_mimetype=FileAttachmentResourceTests.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewDiff(self, review_request):
        """Creates a diff and returns the payload response."""
        from reviewboard.webapi.tests.test_diff import DiffResourceTests

        diff_filename = os.path.join(
            os.path.dirname(scmtools.__file__),
            'testdata', 'svn_makefile.diff')

        f = open(diff_filename, "r")
        rsp = self.apiPost(
            DiffResourceTests.get_list_url(review_request),
            {
                'path': f,
                'basedir': "/trunk",
            },
            expected_mimetype=DiffResourceTests.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _getTrophyFilename(self):
        return os.path.join(settings.STATIC_ROOT, "rb", "images", "trophy.png")
