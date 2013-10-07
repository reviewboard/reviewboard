from datetime import timedelta
import os

from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core import mail
from django.core.files import File
from django.db.models import Q
from django.utils import simplejson, timezone
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import DOES_NOT_EXIST, INVALID_FORM_DATA, \
                                  PERMISSION_DENIED
import paramiko

from reviewboard import initialize
from reviewboard.attachments.models import FileAttachment
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet
from reviewboard.notifications.tests import EmailTestHelper
from reviewboard.reviews.models import DefaultReviewer, \
                                       FileAttachmentComment, Group, \
                                       ReviewRequest, ReviewRequestDraft, \
                                       Review, Comment, Screenshot, \
                                       ScreenshotComment
from reviewboard.scmtools.errors import AuthenticationError, \
                                        UnverifiedCertificateError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.svn import SVNTool
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.site.models import LocalSite
from reviewboard.ssh.client import SSHClient
from reviewboard.ssh.errors import BadHostKeyError, \
                                   UnknownHostKeyError
from reviewboard.testing.testcase import TestCase
from reviewboard.webapi.errors import BAD_HOST_KEY, \
                                      DIFF_TOO_BIG, \
                                      GROUP_ALREADY_EXISTS, \
                                      INVALID_REPOSITORY, \
                                      INVALID_USER, \
                                      MISSING_USER_KEY, \
                                      REPO_AUTHENTICATION_ERROR, \
                                      UNVERIFIED_HOST_CERT, \
                                      UNVERIFIED_HOST_KEY


# A couple classes need keys to test with, so generate them only once.
key1 = paramiko.RSAKey.generate(1024)
key2 = paramiko.RSAKey.generate(1024)


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
            svn_repo_path = os.path.join(os.path.dirname(__file__),
                                         '../scmtools/testdata/svn_repo')
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

    def apiGet(self, path, query={}, follow_redirects=False,
               expected_status=200, expected_redirects=[],
               expected_headers={}, expected_mimetype=None):
        path = self._normalize_path(path)

        print 'GETing %s' % path
        print "Query data: %s" % query

        response = self.api_func_wrapper(self.client.get, path, query,
                                         expected_status, follow_redirects,
                                         expected_redirects, expected_mimetype)

        print "Raw response: %s" % response.content

        for header, value in expected_headers.iteritems():
            self.assertTrue(header in response)
            self.assertEqual(response[header], value)

        if expected_status == 302:
            rsp = response.content
        else:
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
        if not repository:
            repository = self.repository
        rsp = self.apiPost(
            ReviewRequestResourceTests.get_list_url(local_site_name),
            { 'repository': repository.path, },
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
        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        post_data = {
            'body_top': body_top,
            'body_bottom': body_bottom,
        }

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request,
                                                            local_site_name),
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
        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        self.apiDelete(
            ScreenshotResourceTests.get_list_url(review_request,
                                                 local_site_name) +
                                                 str(screenshot.id) + '/')

    def _postNewFileAttachmentComment(self, review_request, review_id,
                                      file_attachment, comment_text,
                                      issue_opened=None,
                                      issue_status=None,
                                      extra_fields={}):
        """Creates a file attachment comment and returns the payload response."""
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
        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scmtools", "testdata", "svn_makefile.diff")

        f = open(diff_filename, "r")
        rsp = self.apiPost(DiffResourceTests.get_list_url(review_request), {
            'path': f,
            'basedir': "/trunk",
        }, expected_mimetype=DiffResourceTests.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _getTrophyFilename(self):
        return os.path.join(settings.STATIC_ROOT, "rb", "images", "trophy.png")


class RootResourceTests(BaseWebAPITestCase):
    """Testing the RootResource APIs."""
    item_mimetype = _build_mimetype('root')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_api_root_with_local_site(self):
        """Testing the GET / API with local sites"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_url('local-site-1'),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('uri_templates' in rsp)
        self.assertTrue('repository' in rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-1/api/repositories/{repository_id}/')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_api_root_with_local_site_and_cache(self):
        """Testing the GET / API with multiple local sites"""
        # djblets had a bug where the uri_templates were cached without any
        # consideration of the local site (or, more generally, the base uri).
        # In this case, fetching /s/<local_site>/api/ might return uri
        # templates for someone else's site. This was breaking rbt post.
        self.test_get_api_root_with_local_site()

        rsp = self.apiGet(self.get_url('local-site-2'),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('uri_templates' in rsp)
        self.assertTrue('repository' in rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-2/api/repositories/{repository_id}/')

    def get_url(self, local_site_name=None):
        return local_site_reverse('root-resource',
                                  local_site_name=local_site_name)


class ServerInfoResourceTests(BaseWebAPITestCase):
    """Testing the ServerInfoResource APIs."""
    item_mimetype = _build_mimetype('server-info')

    def test_get_server_info(self):
        """Testing the GET info/ API"""
        rsp = self.apiGet(self.get_url(),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('info' in rsp)
        self.assertTrue('product' in rsp['info'])
        self.assertTrue('site' in rsp['info'])
        self.assertTrue('capabilities' in rsp['info'])

        caps = rsp['info']['capabilities']
        self.assertTrue('diffs' in caps)

        diffs_caps = caps.get('diffs')
        self.assertTrue(diffs_caps.get('moved_files', False))
        self.assertTrue(diffs_caps.get('base_commit_ids', False))

    @add_fixtures(['test_users', 'test_site'])
    def test_get_server_info_with_site(self):
        """Testing the GET info/ API with a local site"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_url(self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('info' in rsp)
        self.assertTrue('product' in rsp['info'])
        self.assertTrue('site' in rsp['info'])

    @add_fixtures(['test_users', 'test_site'])
    def test_get_server_info_with_site_no_access(self):
        """Testing the GET info/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_url(self.local_site_name),
                    expected_status=403)

    def get_url(self, local_site_name=None):
        return local_site_reverse('info-resource',
                                  local_site_name=local_site_name)


class SessionResourceTests(BaseWebAPITestCase):
    """Testing the SessionResource APIs."""
    item_mimetype = _build_mimetype('session')

    @add_fixtures(['test_users'])
    def test_get_session_with_logged_in_user(self):
        """Testing the GET session/ API with logged in user"""
        rsp = self.apiGet(self.get_url(),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertTrue(rsp['session']['authenticated'])
        self.assertEqual(rsp['session']['links']['user']['title'],
                         self.user.username)

    def test_get_session_with_anonymous_user(self):
        """Testing the GET session/ API with anonymous user"""
        rsp = self.apiGet(self.get_url(),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertFalse(rsp['session']['authenticated'])

    @add_fixtures(['test_users', 'test_site'])
    def test_get_session_with_site(self):
        """Testing the GET session/ API with a local site"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_url(self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('session' in rsp)
        self.assertTrue(rsp['session']['authenticated'])
        self.assertEqual(rsp['session']['links']['user']['title'], 'doc')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_session_with_site_no_access(self):
        """Testing the GET session/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_url(self.local_site_name),
                    expected_status=403)

    def get_url(self, local_site_name=None):
        return local_site_reverse('session-resource',
                                  local_site_name=local_site_name)


class RepositoryResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('repositories')
    item_mimetype = _build_mimetype('repository')

    def setUp(self):
        super(RepositoryResourceTests, self).setUp()

        # Some tests will temporarily replace some functions, so back them up
        # so we can restore them.
        self._old_check_repository = SVNTool.check_repository
        self._old_accept_certificate = SVNTool.accept_certificate
        self._old_add_host_key = SSHClient.add_host_key
        self._old_replace_host_key = SSHClient.replace_host_key

    def tearDown(self):
        super(RepositoryResourceTests, self).tearDown()

        SVNTool.check_repository = self._old_check_repository
        SVNTool.accept_certificate = self._old_accept_certificate
        SSHClient.add_host_key = self._old_add_host_key
        SSHClient.replace_host_key = self._old_replace_host_key

    def test_get_repositories(self):
        """Testing the GET repositories/ API"""
        rsp = self.apiGet(self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']),
                         Repository.objects.accessible(self.user).count())

    @add_fixtures(['test_site'])
    def test_get_repositories_with_site(self):
        """Testing the GET repositories/ API with a local site"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_list_url(self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(len(rsp['repositories']),
                         Repository.objects.filter(
                             local_site__name=self.local_site_name).count())

    @add_fixtures(['test_site'])
    def test_get_repositories_with_site_no_access(self):
        """Testing the GET repositories/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_list_url(self.local_site_name),
                    expected_status=403)

    def test_post_repository(self):
        """Testing the POST repositories/ API"""
        self._login_user(admin=True)
        self._post_repository(False)

    def test_post_repository_with_bad_host_key(self):
        """Testing the POST repositories/ API with Bad Host Key error"""
        hostname = 'example.com'
        key = key1
        expected_key = key2

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise BadHostKeyError(hostname, key, expected_key)

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], BAD_HOST_KEY.code)
        self.assertTrue('hostname' in rsp)
        self.assertTrue('expected_key' in rsp)
        self.assertTrue('key' in rsp)
        self.assertEqual(rsp['hostname'], hostname)
        self.assertEqual(rsp['expected_key'], expected_key.get_base64())
        self.assertEqual(rsp['key'], key.get_base64())

    def test_post_repository_with_bad_host_key_and_trust_host(self):
        """Testing the POST repositories/ API with Bad Host Key error and trust_host=1"""
        hostname = 'example.com'
        key = key1
        expected_key = key2
        saw = {'replace_host_key': False}

        def _replace_host_key(cls, _hostname, _expected_key, _key):
            self.assertEqual(hostname, _hostname)
            self.assertEqual(expected_key, _expected_key)
            self.assertEqual(key, _key)
            saw['replace_host_key'] = True

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            if not saw['replace_host_key']:
                raise BadHostKeyError(hostname, key, expected_key)

        SVNTool.check_repository = _check_repository
        SSHClient.replace_host_key = _replace_host_key

        self._login_user(admin=True)
        self._post_repository(False, data={
            'trust_host': 1,
        })

        self.assertTrue(saw['replace_host_key'])

    def test_post_repository_with_unknown_host_key(self):
        """Testing the POST repositories/ API with Unknown Host Key error"""
        hostname = 'example.com'
        key = key1

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise UnknownHostKeyError(hostname, key)

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_KEY.code)
        self.assertTrue('hostname' in rsp)
        self.assertTrue('key' in rsp)
        self.assertEqual(rsp['hostname'], hostname)
        self.assertEqual(rsp['key'], key.get_base64())

    def test_post_repository_with_unknown_host_key_and_trust_host(self):
        """Testing the POST repositories/ API with Unknown Host Key error and trust_host=1"""
        hostname = 'example.com'
        key = key1
        saw = {'add_host_key': False}

        def _add_host_key(cls, _hostname, _key):
            self.assertEqual(hostname, _hostname)
            self.assertEqual(key, _key)
            saw['add_host_key'] = True

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            if not saw['add_host_key']:
                raise UnknownHostKeyError(hostname, key)

        SVNTool.check_repository = _check_repository
        SSHClient.add_host_key = _add_host_key

        self._login_user(admin=True)
        self._post_repository(False, data={
            'trust_host': 1,
        })

        self.assertTrue(saw['add_host_key'])

    def test_post_repository_with_unknown_cert(self):
        """Testing the POST repositories/ API with Unknown Certificate error"""
        class Certificate(object):
            failures = ['failures']
            fingerprint = 'fingerprint'
            hostname = 'example.com'
            issuer = 'issuer'
            valid_from = 'valid_from'
            valid_until = 'valid_until'

        cert = Certificate()

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise UnverifiedCertificateError(cert)

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], UNVERIFIED_HOST_CERT.code)
        self.assertTrue('certificate' in rsp)
        self.assertEqual(rsp['certificate']['failures'], cert.failures)
        self.assertEqual(rsp['certificate']['fingerprint'], cert.fingerprint)
        self.assertEqual(rsp['certificate']['hostname'], cert.hostname)
        self.assertEqual(rsp['certificate']['issuer'], cert.issuer)
        self.assertEqual(rsp['certificate']['valid']['from'], cert.valid_from)
        self.assertEqual(rsp['certificate']['valid']['until'], cert.valid_until)

    def test_post_repository_with_unknown_cert_and_trust_host(self):
        """Testing the POST repositories/ API with Unknown Certificate error and trust_host=1"""
        class Certificate(object):
            failures = ['failures']
            fingerprint = 'fingerprint'
            hostname = 'example.com'
            issuer = 'issuer'
            valid_from = 'valid_from'
            valid_until = 'valid_until'

        cert = Certificate()
        saw = {'accept_certificate': False}

        @classmethod
        def _check_repository(cls, *args, **kwargs):
            if not saw['accept_certificate']:
                raise UnverifiedCertificateError(cert)

        @classmethod
        def _accept_certificate(cls, path, local_site_name=None):
            saw['accept_certificate'] = True
            return {
                'fingerprint': '123',
            }

        SVNTool.check_repository = _check_repository
        SVNTool.accept_certificate = _accept_certificate

        self._login_user(admin=True)
        rsp = self._post_repository(False, data={
            'trust_host': 1,
        })
        self.assertTrue(saw['accept_certificate'])

        repository = Repository.objects.get(pk=rsp['repository']['id'])
        self.assertTrue('cert' in repository.extra_data)
        self.assertEqual(repository.extra_data['cert']['fingerprint'], '123')

    def test_post_repository_with_missing_user_key(self):
        """Testing the POST repositories/ API with Missing User Key error"""
        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise AuthenticationError(allowed_types=['publickey'],
                                      user_key=None)

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], MISSING_USER_KEY.code)

    def test_post_repository_with_authentication_error(self):
        """Testing the POST repositories/ API with Authentication Error"""
        @classmethod
        def _check_repository(cls, *args, **kwargs):
            raise AuthenticationError

        SVNTool.check_repository = _check_repository

        self._login_user(admin=True)
        rsp = self._post_repository(False, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_AUTHENTICATION_ERROR.code)
        self.assertTrue('reason' in rsp)

    @add_fixtures(['test_site'])
    def test_post_repository_with_site(self):
        """Testing the POST repositories/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        self._post_repository(True)

    def test_post_repository_full_info(self):
        """Testing the POST repositories/ API with all available info"""
        self._login_user(admin=True)
        self._post_repository(False, {
            'bug_tracker': 'http://bugtracker/%s/',
            'encoding': 'UTF-8',
            'mirror_path': 'http://svn.example.com/',
            'username': 'user',
            'password': '123',
            'public': False,
            'raw_file_url': 'http://example.com/<filename>/<version>',
        })

    def test_post_repository_with_no_access(self):
        """Testing the POST repositories/ API with no access"""
        self._login_user()
        self._post_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_post_repository_with_site_no_access(self):
        """Testing the POST repositories/ API with a local site and no access"""
        self._login_user(local_site=True)
        self._post_repository(True, expected_status=403)

    def test_put_repository(self):
        """Testing the PUT repositories/<id>/ API"""
        self._login_user(admin=True)
        self._put_repository(False, {
            'bug_tracker': 'http://bugtracker/%s/',
            'encoding': 'UTF-8',
            'mirror_path': 'http://svn.example.com/',
            'username': 'user',
            'password': '123',
            'public': False,
            'raw_file_url': 'http://example.com/<filename>/<version>',
        })

    @add_fixtures(['test_site'])
    def test_put_repository_with_site(self):
        """Testing the PUT repositories/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        self._put_repository(True, {
            'bug_tracker': 'http://bugtracker/%s/',
            'encoding': 'UTF-8',
            'mirror_path': 'http://svn.example.com/',
            'username': 'user',
            'password': '123',
            'public': False,
            'raw_file_url': 'http://example.com/<filename>/<version>',
        })

    def test_put_repository_with_no_access(self):
        """Testing the PUT repositories/<id>/ API with no access"""
        self._login_user()
        self._put_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_repository_with_site_no_access(self):
        """Testing the PUT repositories/<id>/ API with a local site and no access"""
        self._login_user(local_site=True)
        self._put_repository(False, expected_status=403)

    def test_put_repository_with_archive(self):
        """Testing the PUT repositories/<id>/ API with archive_name=True"""
        self._login_user(admin=True)
        repo_id = self._put_repository(False, {'archive_name': True})

        repo = Repository.objects.get(pk=repo_id)
        self.assertEqual(repo.name[:23], 'ar:New Test Repository:')

    def test_delete_repository(self):
        """Testing the DELETE repositories/<id>/ API"""
        self._login_user(admin=True)
        repo_id = self._delete_repository(False, with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertFalse(repo.visible)

    def test_delete_empty_repository(self):
        """Testing the DELETE repositories/<id>/ API with no review requests"""
        self._login_user(admin=True)
        repo_id = self._delete_repository(False)
        self.assertRaises(Repository.DoesNotExist,
                          Repository.objects.get,
                          pk=repo_id)

    @add_fixtures(['test_site'])
    def test_delete_repository_with_site(self):
        """Testing the DELETE repositories/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        repo_id = self._delete_repository(True, with_review_request=True)

        repo = Repository.objects.get(pk=repo_id)
        self.assertFalse(repo.visible)

    @add_fixtures(['test_site'])
    def test_delete_empty_repository_with_site(self):
        """Testing the DELETE repositories/<id>/ API with a local site and no review requests"""
        self._login_user(local_site=True, admin=True)
        repo_id = self._delete_repository(True)
        self.assertRaises(Repository.DoesNotExist,
                          Repository.objects.get,
                          pk=repo_id)

    def test_delete_repository_with_no_access(self):
        """Testing the DELETE repositories/<id>/ API with no access"""
        self._login_user()
        self._delete_repository(False, expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_repository_with_site_no_access(self):
        """Testing the DELETE repositories/<id>/ API with a local site and no access"""
        self._login_user(local_site=True)
        self._delete_repository(True, expected_status=403)

    def _post_repository(self, use_local_site, data={}, expected_status=201):
        repo_name = 'Test Repository'
        repo_path = 'file://' + os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         '../scmtools/testdata/svn_repo'))

        local_site_name = self._get_local_site_info(use_local_site)[1]

        if 200 <= expected_status < 300:
            expected_mimetype = self.item_mimetype
        else:
            expected_mimetype = None

        rsp = self.apiPost(self.get_list_url(local_site_name), dict({
                'name': repo_name,
                'path': repo_path,
                'tool': 'Subversion',
            }, **data),
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

        if 200 <= expected_status < 300:
            self._verify_repository_info(rsp, repo_name, repo_path, data)

            self.assertEqual(
                rsp['repository']['links']['self']['href'],
                self.base_url + self.get_item_url(rsp['repository']['id'],
                                                  local_site_name))

        return rsp

    def _put_repository(self, use_local_site, data={}, expected_status=200):
        repo_name = 'New Test Repository'
        repo_path = 'file://' + os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         '../scmtools/testdata/svn_repo'))

        local_site, local_site_name = self._get_local_site_info(use_local_site)
        repo_id = Repository.objects.filter(local_site=local_site,
                                            tool__name='Subversion')[0].pk


        if 200 <= expected_status < 300:
            expected_mimetype = self.item_mimetype
        else:
            expected_mimetype = None

        rsp = self.apiPut(self.get_item_url(repo_id, local_site_name), dict({
                'name': repo_name,
                'path': repo_path,
            }, **data),
            expected_status=expected_status,
            expected_mimetype=expected_mimetype)

        if 200 <= expected_status < 300:
            self._verify_repository_info(rsp, repo_name, repo_path, data)

        return repo_id

    def _delete_repository(self, use_local_site, expected_status=204,
                           with_review_request=False):
        local_site, local_site_name = self._get_local_site_info(use_local_site)
        repo = Repository.objects.filter(local_site=local_site,
                                         tool__name='Subversion')[0]
        repo_id = repo.pk

        if with_review_request:
            request = ReviewRequest.objects.create(self.user, repo)
            request.save()

        self.apiDelete(self.get_item_url(repo_id, local_site_name),
                       expected_status=expected_status)

        return repo_id

    def _get_local_site_info(self, use_local_site):
        if use_local_site:
            return (LocalSite.objects.get(name=self.local_site_name),
                    self.local_site_name)
        else:
            return None, None

    def _verify_repository_info(self, rsp, repo_name, repo_path, data):
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('repository' in rsp)

        repository = Repository.objects.get(pk=rsp['repository']['id'])

        self.assertEqual(rsp['repository']['path'], repo_path)
        self.assertEqual(repository.path, repo_path)

        if not data.get('archive_name', False):
            self.assertEqual(rsp['repository']['name'], repo_name)
            self.assertEqual(repository.name, repo_name)

        for key, value in data.iteritems():
            if hasattr(repository, key):
                self.assertEqual(getattr(repository, key), value)

    def get_list_url(self, local_site_name=None):
        return local_site_reverse('repositories-resource',
                                  local_site_name=local_site_name)

    @classmethod
    def get_item_url(cls, repository_id, local_site_name=None):
        return local_site_reverse('repository-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'repository_id': repository_id,
                                  })


class RepositoryInfoResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryInfoResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    item_mimetype = _build_mimetype('repository-info')

    def test_get_repository_info(self):
        """Testing the GET repositories/<id>/info API"""
        rsp = self.apiGet(self.get_url(self.repository),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['info'],
                         self.repository.get_scmtool().get_repository_info())

    @add_fixtures(['test_site'])
    def test_get_repository_info_with_site(self):
        """Testing the GET repositories/<id>/info API with a local site"""
        self._login_user(local_site=True)
        self.repository.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        self.repository.save()

        rsp = self.apiGet(self.get_url(self.repository, self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['info'],
                         self.repository.get_scmtool().get_repository_info())

    @add_fixtures(['test_site'])
    def test_get_repository_info_with_site_no_access(self):
        """Testing the GET repositories/<id>/info API with a local site and Permission Denied error"""
        self.repository.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        self.repository.save()

        self.apiGet(self.get_url(self.repository, self.local_site_name),
                    expected_status=403)

    def get_url(self, repository, local_site_name=None):
        return local_site_reverse('info-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'repository_id': repository.pk,
                                  })


class ReviewGroupResourceTests(BaseWebAPITestCase):
    """Testing the ReviewGroupResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('review-groups')
    item_mimetype = _build_mimetype('review-group')

    def test_post_group(self, local_site=None):
        """Testing the POST groups/ API"""
        name = 'my-group'
        display_name = 'My Group'
        mailing_list = 'mygroup@example.com'
        visible = False
        invite_only = True

        self._login_user(admin=True)

        rsp = self.apiPost(self.get_list_url(local_site), {
            'name': name,
            'display_name': display_name,
            'mailing_list': mailing_list,
            'visible': visible,
            'invite_only': invite_only,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        group = Group.objects.get(pk=rsp['group']['id'])
        self.assertEqual(group.local_site, local_site)
        self.assertEqual(group.name, name)
        self.assertEqual(group.display_name, display_name)
        self.assertEqual(group.mailing_list, mailing_list)
        self.assertEqual(group.visible, visible)
        self.assertEqual(group.invite_only, invite_only)

    @add_fixtures(['test_site'])
    def test_post_group_with_site(self):
        """Testing the POST groups/ API with a local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        self.test_post_group(local_site)

    def test_post_group_with_defaults(self):
        """Testing the POST groups/ API with field defaults"""
        name = 'my-group'
        display_name = 'My Group'

        self._login_user(admin=True)

        rsp = self.apiPost(self.get_list_url(), {
            'name': name,
            'display_name': display_name,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        group = Group.objects.get(pk=rsp['group']['id'])
        self.assertEqual(group.mailing_list, '')
        self.assertEqual(group.visible, True)
        self.assertEqual(group.invite_only, False)

    @add_fixtures(['test_site'])
    def test_post_group_with_site_admin(self):
        """Testing the POST groups/ API with a local site admin"""
        self._login_user(local_site=True, admin=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)

        rsp = self.apiPost(self.get_list_url(local_site), {
            'name': 'mygroup',
            'display_name': 'My Group',
            'mailing_list': 'mygroup@example.com',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_group_with_no_access(self, local_site=None):
        """Testing the POST groups/ API with no access"""
        rsp = self.apiPost(self.get_list_url(local_site), {
            'name': 'mygroup',
            'display_name': 'My Group',
            'mailing_list': 'mygroup@example.com',
        }, expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_post_group_with_site_no_access(self):
        """Testing the POST groups/ API with local site and no access"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        self.test_post_group_with_no_access(local_site)

    def test_post_group_with_conflict(self):
        """Testing the POST groups/ API with Group Already Exists error"""
        self._login_user(admin=True)
        group = Group.objects.get(pk=1)

        rsp = self.apiPost(self.get_list_url(), {
            'name': group.name,
            'display_name': 'My Group',
        }, expected_status=409)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], GROUP_ALREADY_EXISTS.code)

    @add_fixtures(['test_site'])
    def test_put_group(self, local_site=None):
        """Testing the PUT groups/<name>/ API"""
        name = 'my-group'
        display_name = 'My Group'
        mailing_list = 'mygroup@example.com'

        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.save()

        self._login_user(admin=True)
        rsp = self.apiPut(self.get_item_url(group.name, local_site), {
            'name': name,
            'display_name': display_name,
            'mailing_list': mailing_list,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        group = Group.objects.get(pk=group.pk)
        self.assertEqual(group.local_site, local_site)
        self.assertEqual(group.name, name)
        self.assertEqual(group.display_name, display_name)
        self.assertEqual(group.mailing_list, mailing_list)

    @add_fixtures(['test_site'])
    def test_put_group_with_site(self):
        """Testing the PUT groups/<name>/ API with local site"""
        self.test_put_group(LocalSite.objects.get(name=self.local_site_name))

    def test_put_group_with_no_access(self, local_site=None):
        """Testing the PUT groups/<name>/ API with no access"""
        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.save()

        rsp = self.apiPut(self.get_item_url(group.name, local_site), {
            'name': 'mygroup',
            'display_name': 'My Group',
            'mailing_list': 'mygroup@example.com',
        }, expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_put_group_with_site_no_access(self):
        """Testing the PUT groups/<name>/ API with local site and no access"""
        self.test_put_group_with_no_access(
            LocalSite.objects.get(name=self.local_site_name))

    def test_put_group_with_conflict(self):
        """Testing the PUT groups/<name>/ API with Group Already Exists error"""
        group = Group.objects.get(pk=1)
        group2 = Group.objects.get(pk=2)

        self._login_user(admin=True)
        rsp = self.apiPut(self.get_item_url(group.name), {
            'name': group2.name,
        }, expected_status=409)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], GROUP_ALREADY_EXISTS.code)

    @add_fixtures(['test_site'])
    def test_get_groups(self):
        """Testing the GET groups/ API"""
        rsp = self.apiGet(self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']),
                         Group.objects.accessible(self.user).count())
        self.assertEqual(len(rsp['groups']), 4)

    @add_fixtures(['test_site'])
    def test_get_groups_with_site(self):
        """Testing the GET groups/ API with a local site"""
        self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)
        groups = Group.objects.accessible(self.user, local_site=local_site)

        rsp = self.apiGet(self.get_list_url(self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), groups.count())
        self.assertEqual(len(rsp['groups']), 1)

    @add_fixtures(['test_site'])
    def test_get_groups_with_site_no_access(self):
        """Testing the GET groups/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_list_url(self.local_site_name),
                    expected_status=403)

    def test_get_groups_with_q(self):
        """Testing the GET groups/?q= API"""
        rsp = self.apiGet(self.get_list_url(), {'q': 'dev'},
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), 1) #devgroup

    def test_get_group_public(self):
        """Testing the GET groups/<id>/ API"""
        group = Group.objects.create(name='test-group')

        rsp = self.apiGet(self.get_item_url(group.name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['group']['name'], group.name)
        self.assertEqual(rsp['group']['display_name'], group.display_name)
        self.assertEqual(rsp['group']['invite_only'], False)

    def test_get_group_public_not_modified(self):
        """Testing the GET groups/<id>/ API with Not Modified response"""
        Group.objects.create(name='test-group')

        self._testHttpCaching(self.get_item_url('test-group'),
                              check_etags=True)

    def test_get_group_invite_only(self):
        """Testing the GET groups/<id>/ API with invite-only"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        rsp = self.apiGet(self.get_item_url(group.name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['group']['invite_only'], True)

    def test_get_group_invite_only_with_permission_denied_error(self):
        """Testing the GET groups/<id>/ API with invite-only and Permission Denied error"""
        group = Group.objects.create(name='test-group', invite_only=True)

        rsp = self.apiGet(self.get_item_url(group.name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_get_group_with_site(self):
        """Testing the GET groups/<id>/ API with a local site"""
        self._login_user(local_site=True)
        group = Group.objects.get(name='sitegroup')

        rsp = self.apiGet(self.get_item_url('sitegroup', self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['group']['name'], group.name)
        self.assertEqual(rsp['group']['display_name'], group.display_name)

    @add_fixtures(['test_site'])
    def test_get_group_with_site_no_access(self):
        """Testing the GET groups/<id>/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_item_url('sitegroup', self.local_site_name),
                    expected_status=403)

    def test_delete_group(self):
        """Testing the DELETE groups/<id>/ API"""
        self._login_user(admin=True)
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        self.apiDelete(self.get_item_url('test-group'),
                       expected_status=204)
        self.assertEqual(Group.objects.filter(name='test-group').exists(), False)

    def test_delete_group_with_permission_denied_error(self):
        """Testing the DELETE groups/<id>/ API with Permission Denied error"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        self.apiDelete(self.get_item_url('test-group'),
                       expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_group_with_local_site(self):
        """Testing the DELETE groups/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)
        self.apiDelete(self.get_item_url('sitegroup', self.local_site_name),
                       expected_status=204)

    @add_fixtures(['test_site'])
    def test_delete_group_with_local_site_and_permission_denied_error(self):
        """Testing the DELETE groups/<id>/ API with a local site and Permission Denied error"""
        self._login_user(local_site=True)
        self.apiDelete(self.get_item_url('sitegroup', self.local_site_name),
                       expected_status=403)

    def test_delete_group_with_review_requests(self):
        """Testing the DELETE groups/<id>/ API with existing review requests"""
        self._login_user(admin=True)

        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        request = ReviewRequest.objects.create(self.user, self.repository)
        request.target_groups.add(group)

        self.apiDelete(self.get_item_url('test-group'),
                       expected_status=204)

        request = ReviewRequest.objects.get(pk=request.id)
        self.assertEqual(request.target_groups.count(), 0)

    def get_list_url(self, local_site_name=None):
        return local_site_reverse('groups-resource',
                                  local_site_name=local_site_name)

    def get_item_url(self, group_name, local_site_name=None):
        return local_site_reverse('group-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'group_name': group_name,
                                  })


class ReviewGroupUserResourceTests(BaseWebAPITestCase):
    """Testing the ReviewGroupUserResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('users')
    item_mimetype = _build_mimetype('user')

    def test_create_user(self, local_site=None):
        """Testing the POST groups/<name>/users/ API"""
        self._login_user(admin=True, local_site=local_site)

        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.users = []
        group.save()

        user = User.objects.get(pk=1)

        rsp = self.apiPost(self.get_list_url(group.name, local_site), {
            'username': user.username,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(group.users.count(), 1)
        self.assertEqual(group.users.get().username, user.username)

    @add_fixtures(['test_site'])
    def test_create_user_with_site(self):
        """Testing the POST groups/<name>/users/ API with local site"""
        self.test_create_user(LocalSite.objects.get(name=self.local_site_name))

    def test_create_user_with_no_access(self, local_site=None):
        """Testing the POST groups/<name>/users/ API with Permission Denied"""
        group = Group.objects.get(pk=1)
        user = User.objects.get(pk=1)

        rsp = self.apiPost(self.get_list_url(group.name, local_site), {
            'username': user.username,
        }, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_create_user_with_site_no_access(self):
        """Testing the POST groups/<name>/users/ API with local site and Permission Denied"""
        self.test_create_user_with_no_access(
            LocalSite.objects.get(name=self.local_site_name))

    def test_create_user_with_invalid_user(self):
        """Testing the POST groups/<name>/users/ API with invalid user"""
        self._login_user(admin=True)

        group = Group.objects.get(pk=1)
        group.users = []
        group.save()

        rsp = self.apiPost(self.get_list_url(group.name), {
            'username': 'grabl',
        }, expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_USER.code)

        self.assertEqual(group.users.count(), 0)

    def test_delete_user(self, local_site=None):
        """Testing the DELETE groups/<name>/users/<username>/ API"""
        self._login_user(admin=True, local_site=local_site)

        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.save()

        old_count = group.users.count()
        user = group.users.all()[0]

        self.apiDelete(
            self.get_item_url(group.name, user.username, local_site),
            expected_status=204)

        self.assertEqual(group.users.count(), old_count - 1)

    @add_fixtures(['test_site'])
    def test_delete_user_with_site(self):
        """Testing the DELETE groups/<name>/users/<username>/ API with local site"""
        self.test_delete_user(LocalSite.objects.get(name=self.local_site_name))

    def test_delete_user_with_no_access(self, local_site=None):
        """Testing the DELETE groups/<name>/users/<username>/ API with Permission Denied"""
        group = Group.objects.get(pk=1)
        user = group.users.all()[0]

        self.apiDelete(
            self.get_item_url(group.name, user.username, local_site),
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_user_with_site_no_access(self):
        """Testing the DELETE groups/<name>/users/<username>/ API with local site and Permission Denied"""
        self.test_delete_user_with_no_access(
            LocalSite.objects.get(name=self.local_site_name))

    def test_get_users(self, local_site=None):
        """Testing the GET groups/<name>/users/ API"""
        group = Group.objects.get(pk=1)
        group.local_site = local_site
        group.save()

        rsp = self.apiGet(self.get_list_url(group.name, local_site),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), group.users.count())

    @add_fixtures(['test_site'])
    def test_get_users_with_site(self):
        """Testing the GET groups/<name>/users/ API with local site"""
        self._login_user(local_site=True)
        self.test_get_users(LocalSite.objects.get(name=self.local_site_name))

    def get_list_url(self, group_name, local_site_name=None):
        return local_site_reverse('users-resource',
                                  kwargs={
                                      'group_name': group_name,
                                  },
                                  local_site_name=local_site_name)

    def get_item_url(self, group_name, username, local_site_name=None):
        return local_site_reverse('user-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'group_name': group_name,
                                      'username': username,
                                  })


class UserResourceTests(BaseWebAPITestCase):
    """Testing the UserResource API tests."""
    fixtures = ['test_users']

    list_mimetype = _build_mimetype('users')
    item_mimetype = _build_mimetype('user')

    def test_get_users(self):
        """Testing the GET users/ API"""
        rsp = self.apiGet(self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), User.objects.count())

    def test_get_users_with_q(self):
        """Testing the GET users/?q= API"""
        rsp = self.apiGet(self.get_list_url(), {'q': 'gru'},
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 1) # grumpy

    @add_fixtures(['test_site'])
    def test_get_users_with_site(self):
        """Testing the GET users/ API with a local site"""
        self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)
        rsp = self.apiGet(self.get_list_url(self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), local_site.users.count())

    @add_fixtures(['test_site'])
    def test_get_users_with_site_no_access(self):
        """Testing the GET users/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_list_url(self.local_site_name),
                    expected_status=403)

    def test_get_user(self):
        """Testing the GET users/<username>/ API"""
        username = 'doc'
        user = User.objects.get(username=username)
        self.assertFalse(user.get_profile().is_private)

        rsp = self.apiGet(self.get_item_url(username),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertEqual(rsp['user']['first_name'], user.first_name)
        self.assertEqual(rsp['user']['last_name'], user.last_name)
        self.assertEqual(rsp['user']['id'], user.id)
        self.assertEqual(rsp['user']['email'], user.email)

    def test_get_user_not_modified(self):
        """Testing the GET users/<username>/ API with Not Modified response"""
        self._testHttpCaching(self.get_item_url('doc'),
                              check_etags=True)

    @add_fixtures(['test_site'])
    def test_get_user_with_site(self):
        """Testing the GET users/<username>/ API with a local site"""
        self._login_user(local_site=True)

        username = 'doc'
        user = User.objects.get(username=username)
        self.assertFalse(user.get_profile().is_private)

        rsp = self.apiGet(self.get_item_url(username, self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertEqual(rsp['user']['first_name'], user.first_name)
        self.assertEqual(rsp['user']['last_name'], user.last_name)
        self.assertEqual(rsp['user']['id'], user.id)
        self.assertEqual(rsp['user']['email'], user.email)

    @add_fixtures(['test_site'])
    def test_get_user_with_site_and_profile_private(self):
        """Testing the GET users/<username>/ API with a local site and private profile"""
        self._login_user(local_site=True)

        username = 'admin'
        user = User.objects.get(username=username)

        profile = user.get_profile()
        profile.is_private = True
        profile.save()

        rsp = self.apiGet(self.get_item_url(username, self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['user']['username'], user.username)
        self.assertFalse('first_name' in rsp['user'])
        self.assertFalse('last_name' in rsp['user'])
        self.assertFalse('email' in rsp['user'])

    @add_fixtures(['test_site'])
    def test_get_missing_user_with_site(self):
        """Testing the GET users/<username>/ API with a local site"""
        self._login_user(local_site=True)
        self.apiGet(self.get_item_url('dopey', self.local_site_name),
                    expected_status=404)

    @add_fixtures(['test_site'])
    def test_get_user_with_site_no_access(self):
        """Testing the GET users/<username>/ API with a local site and Permission Denied error."""
        print self.fixtures
        self.apiGet(self.get_item_url('doc', self.local_site_name),
                    expected_status=403)

    def get_list_url(self, local_site_name=None):
        return local_site_reverse('users-resource',
                                  local_site_name=local_site_name)

    @classmethod
    def get_item_url(cls, username, local_site_name=None):
        return local_site_reverse('user-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'username': username,
                                  })


class WatchedReviewRequestResourceTests(BaseWebAPITestCase):
    """Testing the WatchedReviewRequestResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests',
                'test_site']

    item_mimetype = _build_mimetype('watched-review-request')
    list_mimetype = _build_mimetype('watched-review-requests')

    def test_get(self):
        """Testing the GET users/<username>/watched/review_request/<id>/ API"""
        review_request = ReviewRequest.objects.public()[0]
        profile = self.user.get_profile()
        profile.starred_review_requests.add(review_request)

        expected_url = (
            self.base_url +
            ReviewRequestResourceTests.get_item_url(review_request.display_id))

        self.apiGet(
            self.get_item_url(self.user.username, review_request.display_id),
            expected_status=302,
            expected_headers={
                'Location': expected_url,
            })

    def test_get_with_site(self):
        """Testing the GET users/<username>/watched/review_request/<id>/ API with access to a local site"""
        user = self._login_user(local_site=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        profile = user.get_profile()
        profile.starred_review_requests.add(review_request)

        expected_url = (
            self.base_url +
            ReviewRequestResourceTests.get_item_url(review_request.display_id,
                                                    self.local_site_name))

        self.apiGet(
            self.get_item_url(user.username, review_request.display_id,
                              self.local_site_name),
            expected_status=302,
            expected_headers={
                'Location': expected_url,
            })

    def test_get_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review_request/<id>/ API with access to a local site
        """
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        profile = self.user.get_profile()
        profile.starred_review_requests.add(review_request)

        rsp = self.apiGet(
            self.get_item_url(self.user.username, review_request.display_id,
                              self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_watched_review_request(self):
        """Testing the POST users/<username>/watched/review-request/ API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiPost(self.get_list_url(self.user.username), {
            'object_id': review_request.display_id,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(review_request in
                     self.user.get_profile().starred_review_requests.all())

    def test_post_watched_review_request_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review_request/ with Does Not Exist error"""
        rsp = self.apiPost(self.get_list_url(self.user.username), {
            'object_id': 999,
        }, expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_post_watched_review_request_with_site(self):
        """Testing the POST users/<username>/watched/review_request/ API with a local site"""
        self._login_user(local_site=True)

        username = 'doc'
        user = User.objects.get(username=username)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        rsp = self.apiPost(self.get_list_url(username, self.local_site_name),
                           { 'object_id': review_request.display_id, },
                           expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(review_request in
                        user.get_profile().starred_review_requests.all())

    def test_post_watched_review_request_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review_request/ API with a local site and Does Not Exist error"""
        self._login_user(local_site=True)
        rsp = self.apiPost(self.get_list_url('doc', self.local_site_name),
                           { 'object_id': 10, },
                           expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_post_watched_review_request_with_site_no_access(self):
        """Testing the POST users/<username>/watched/review_request/ API with a local site and Permission Denied error"""
        rsp = self.apiPost(self.get_list_url('doc', self.local_site_name),
                           { 'object_id': 10, },
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_watched_review_request(self):
        """Testing the DELETE users/<username>/watched/review_request/ API"""
        # First, star it.
        self.test_post_watched_review_request()

        review_request = ReviewRequest.objects.public()[0]
        self.apiDelete(self.get_item_url(self.user.username,
                                          review_request.display_id))
        self.assertTrue(review_request not in
                        self.user.get_profile().starred_review_requests.all())

    def test_delete_watched_review_request_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review_request/ API with Does Not Exist error"""
        rsp = self.apiDelete(self.get_item_url(self.user.username, 999),
                             expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_delete_not_owner(self):
        """Testing the DELETE users/<username>/watched/review-requests/<id>/ API without being the owner
        """
        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        review_request = ReviewRequest.objects.public()[0]
        profile = user.get_profile()
        profile.starred_review_requests.add(review_request)

        rsp = self.apiDelete(
            self.get_item_url(user.username, 1, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_watched_review_request_with_site(self):
        """Testing the DELETE users/<username>/watched/review_request/ API with a local site"""
        self.test_post_watched_review_request_with_site()

        user = User.objects.get(username='doc')
        review_request = ReviewRequest.objects.get(
            local_id=1, local_site__name=self.local_site_name)

        self.apiDelete(self.get_item_url(user.username,
                                          review_request.display_id,
                                          self.local_site_name))
        self.assertTrue(review_request not in
                        user.get_profile().starred_review_requests.all())

    def test_delete_watched_review_request_with_site_no_access(self):
        """Testing the DELETE users/<username>/watched/review_request/ API with a local site and Permission Denied error"""
        rsp = self.apiDelete(self.get_item_url(self.user.username, 1,
                                                self.local_site_name),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_watched_review_requests(self):
        """Testing the GET users/<username>/watched/review_request/ API"""
        self.test_post_watched_review_request()

        rsp = self.apiGet(self.get_list_url(self.user.username),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        watched = self.user.get_profile().starred_review_requests.all()
        apiwatched = rsp['watched_review_requests']

        self.assertEqual(len(watched), len(apiwatched))
        for i in range(len(watched)):
            self.assertEqual(watched[i].id,
                             apiwatched[i]['watched_review_request']['id'])
            self.assertEqual(watched[i].summary,
                             apiwatched[i]['watched_review_request']['summary'])

    def test_get_watched_review_requests_with_site(self):
        """Testing the GET users/<username>/watched/review_request/ API with a local site"""
        username = 'doc'
        user = User.objects.get(username=username)

        self.test_post_watched_review_request_with_site()

        rsp = self.apiGet(self.get_list_url(username, self.local_site_name),
                          expected_mimetype=self.list_mimetype)

        watched = user.get_profile().starred_review_requests.filter(
            local_site__name=self.local_site_name)
        apiwatched = rsp['watched_review_requests']

        self.assertEqual(len(watched), len(apiwatched))
        for i in range(len(watched)):
            self.assertEqual(watched[i].display_id,
                             apiwatched[i]['watched_review_request']['id'])
            self.assertEqual(watched[i].summary,
                             apiwatched[i]['watched_review_request']['summary'])

    def test_get_watched_review_requests_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review_request/ API with a local site and Permission Denied error"""
        rsp = self.apiGet(self.get_list_url(self.user.username,
                                             self.local_site_name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_watched_review_requests_with_site_does_not_exist(self):
        """Testing the GET users/<username>/watched/review_request/ API with a local site and Does Not Exist error"""
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_list_url(self.user.username,
                                             self.local_site_name),
                          expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def get_list_url(self, username, local_site_name=None):
        return local_site_reverse('watched-review-requests-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'username': username,
                                  })

    def get_item_url(self, username, object_id, local_site_name=None):
        return local_site_reverse('watched-review-request-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'username': username,
                                      'watched_obj_id': object_id,
                                  })


class WatchedReviewGroupResourceTests(BaseWebAPITestCase):
    """Testing the WatchedReviewGroupResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('watched-review-groups')
    item_mimetype = _build_mimetype('watched-review-group')

    def test_post_watched_review_group(self):
        """Testing the POST users/<username>/watched/review-groups/ API"""
        group = Group.objects.get(name='devgroup', local_site=None)

        rsp = self.apiPost(self.get_list_url(self.user.username), {
            'object_id': group.name,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(group in self.user.get_profile().starred_groups.all())

    def test_post_watched_review_group_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API with Does Not Exist error"""
        rsp = self.apiPost(self.get_list_url(self.user.username), {
            'object_id': 'invalidgroup',
        }, expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_watched_review_group_with_site(self):
        """Testing the POST users/<username>/watched/review-groups/ API with a local site"""
        self._login_user(local_site=True)

        username = 'doc'
        user = User.objects.get(username=username)
        group = Group.objects.get(name='sitegroup',
                                  local_site__name=self.local_site_name)

        rsp = self.apiPost(self.get_list_url(username, self.local_site_name),
                           { 'object_id': group.name, },
                           expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(group in user.get_profile().starred_groups.all())

    @add_fixtures(['test_site'])
    def test_post_watched_review_group_with_site_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API with a local site and Does Not Exist error"""
        username = 'doc'

        self._login_user(local_site=True)
        rsp = self.apiPost(self.get_list_url(username, self.local_site_name),
                           { 'object_id': 'devgroup', },
                           expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_post_watched_review_group_with_site_no_access(self):
        """Testing the POST users/<username>/watched/review-groups/ API with a local site and Permission Denied error"""
        rsp = self.apiPost(self.get_list_url(self.user.username,
                                              self.local_site_name),
                           { 'object_id': 'devgroup', },
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


    def test_delete_watched_review_group(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API"""
        # First, star it.
        self.test_post_watched_review_group()

        group = Group.objects.get(name='devgroup', local_site=None)

        self.apiDelete(self.get_item_url(self.user.username, group.name))
        self.assertFalse(group in
                         self.user.get_profile().starred_groups.all())

    def test_delete_watched_review_group_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API with Does Not Exist error"""
        rsp = self.apiDelete(self.get_item_url(self.user.username,
                                                'invalidgroup'),
                             expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_watched_review_group_with_site(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API with a local site"""
        self.test_post_watched_review_group_with_site()

        user = User.objects.get(username='doc')
        group = Group.objects.get(name='sitegroup',
                                  local_site__name=self.local_site_name)

        self.apiDelete(self.get_item_url(user.username, group.name,
                                          self.local_site_name))
        self.assertFalse(group in user.get_profile().starred_groups.all())

    @add_fixtures(['test_site'])
    def test_delete_watched_review_group_with_site_no_access(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API with a local site and Permission Denied error"""
        rsp = self.apiDelete(self.get_item_url(self.user.username, 'group',
                                                self.local_site_name),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_watched_review_groups(self):
        """Testing the GET users/<username>/watched/review-groups/ API"""
        self.test_post_watched_review_group()

        rsp = self.apiGet(self.get_list_url(self.user.username),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        watched = self.user.get_profile().starred_groups.all()
        apigroups = rsp['watched_review_groups']

        self.assertEqual(len(apigroups), len(watched))

        for id in range(len(watched)):
            self.assertEqual(apigroups[id]['watched_review_group']['name'],
                             watched[id].name)

    @add_fixtures(['test_site'])
    def test_get_watched_review_groups_with_site(self):
        """Testing the GET users/<username>/watched/review-groups/ API with a local site"""
        self.test_post_watched_review_group_with_site()

        rsp = self.apiGet(self.get_list_url('doc', self.local_site_name),
                          expected_mimetype=self.list_mimetype)

        watched = self.user.get_profile().starred_groups.filter(
            local_site__name=self.local_site_name)
        apigroups = rsp['watched_review_groups']

        self.assertEqual(rsp['stat'], 'ok')

        for id in range(len(watched)):
            self.assertEqual(apigroups[id]['watched_review_group']['name'],
                             watched[id].name)

    @add_fixtures(['test_site'])
    def test_get_watched_review_groups_with_site_no_access(self):
        """Testing the GET users/<username>/watched/review-groups/ API with a local site and Permission Denied error"""
        rsp = self.apiGet(self.get_list_url(self.user.username,
                                            self.local_site_name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def get_list_url(self, username, local_site_name=None):
        return local_site_reverse('watched-review-groups-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'username': username,
                                  })

    def get_item_url(self, username, object_id, local_site_name=None):
        return local_site_reverse('watched-review-group-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'username': username,
                                      'watched_obj_id': object_id,
                                  })


class ReviewRequestResourceTests(BaseWebAPITestCase):
    """Testing the ReviewRequestResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('review-requests')
    item_mimetype = _build_mimetype('review-request')

    @add_fixtures(['test_site'])
    def test_get_reviewrequests(self):
        """Testing the GET review-requests/ API"""
        rsp = self.apiGet(self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public().count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_site(self):
        """Testing the GET review-requests/ API with a local site"""
        self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)

        rsp = self.apiGet(self.get_list_url(self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(
                             local_site=local_site).count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_site_no_access(self):
        """Testing the GET review-requests/ API with a local site and Permission Denied error"""
        self.apiGet(self.get_list_url(self.local_site_name),
                    expected_status=403)

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_status(self):
        """Testing the GET review-requests/?status= API"""
        url = self.get_list_url()

        rsp = self.apiGet(url, {'status': 'submitted'},
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='S').count())

        rsp = self.apiGet(url, {'status': 'discarded'},
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='D').count())

        rsp = self.apiGet(url, {'status': 'all'},
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status=None).count())

    def test_get_reviewrequests_with_counts_only(self):
        """Testing the GET review-requests/?counts-only=1 API"""
        rsp = self.apiGet(self.get_list_url(), {
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], ReviewRequest.objects.public().count())

    def test_get_reviewrequests_with_to_groups(self):
        """Testing the GET review-requests/?to-groups= API"""
        rsp = self.apiGet(self.get_list_url(), {
            'to-groups': 'devgroup',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_group("devgroup",
                                                        None).count())

    def test_get_reviewrequests_with_to_groups_and_status(self):
        """Testing the GET review-requests/?to-groups=&status= API"""
        url = self.get_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'to-groups': 'devgroup',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", None,
                                           status='S').count())

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'to-groups': 'devgroup',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", None,
                                           status='D').count())

    def test_get_reviewrequests_with_to_groups_and_counts_only(self):
        """Testing the GET review-requests/?to-groups=&counts-only=1 API"""
        rsp = self.apiGet(self.get_list_url(), {
            'to-groups': 'devgroup',
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_group("devgroup",
                                                        None).count())

    def test_get_reviewrequests_with_to_users(self):
        """Testing the GET review-requests/?to-users= API"""
        rsp = self.apiGet(self.get_list_url(), {
            'to-users': 'grumpy',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user("grumpy").count())

    def test_get_reviewrequests_with_to_users_and_status(self):
        """Testing the GET review-requests/?to-users=&status= API"""
        url = self.get_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'to-users': 'grumpy',
        }, expected_mimetype=self.list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='S').count())

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'to-users': 'grumpy',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='D').count())

    def test_get_reviewrequests_with_to_users_and_counts_only(self):
        """Testing the GET review-requests/?to-users=&counts-only=1 API"""
        rsp = self.apiGet(self.get_list_url(), {
            'to-users': 'grumpy',
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user("grumpy").count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_to_users_directly(self):
        """Testing the GET review-requests/?to-users-directly= API"""
        rsp = self.apiGet(self.get_list_url(), {
            'to-users-directly': 'doc',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_reviewrequests_with_to_users_directly_and_status(self):
        """Testing the GET review-requests/?to-users-directly=&status= API"""
        url = self.get_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'to-users-directly': 'doc'
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='S').count())

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'to-users-directly': 'doc'
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='D').count())

    def test_get_reviewrequests_with_to_users_directly_and_counts_only(self):
        """Testing the GET review-requests/?to-users-directly=&counts-only=1 API"""
        rsp = self.apiGet(self.get_list_url(), {
            'to-users-directly': 'doc',
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_reviewrequests_with_from_user(self):
        """Testing the GET review-requests/?from-user= API"""
        rsp = self.apiGet(self.get_list_url(), {
            'from-user': 'grumpy',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.from_user("grumpy").count())

    def test_get_reviewrequests_with_from_user_and_status(self):
        """Testing the GET review-requests/?from-user=&status= API"""
        url = self.get_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'from-user': 'grumpy',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='S').count())

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'from-user': 'grumpy',
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='D').count())

    def test_get_reviewrequests_with_from_user_and_counts_only(self):
        """Testing the GET review-requests/?from-user=&counts-only=1 API"""
        rsp = self.apiGet(self.get_list_url(), {
            'from-user': 'grumpy',
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.from_user("grumpy").count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_ship_it_0(self):
        """Testing the GET review-requests/?ship-it=0 API"""
        rsp = self.apiGet(self.get_list_url(), {
            'ship-it': 0,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertNotEqual(len(rsp['review_requests']), 0)


        q = ReviewRequest.objects.public(user=self.user,
                                         status='P',
                                         extra_query=Q(shipit_count=0))
        self.assertEqual(len(rsp['review_requests']), q.count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_ship_it_1(self):
        """Testing the GET review-requests/?ship-it=1 API"""
        rsp = self.apiGet(self.get_list_url(), {
            'ship-it': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertNotEqual(len(rsp['review_requests']), 0)

        q = ReviewRequest.objects.public(user=self.user,
                                         status='P',
                                         extra_query=Q(shipit_count__gt=0))
        self.assertEqual(len(rsp['review_requests']), q.count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_time_added_from(self):
        """Testing the GET review-requests/?time-added-from= API"""
        start_index = 3

        public_review_requests = \
            ReviewRequest.objects.public().order_by('time_added')
        r = public_review_requests[start_index]
        timestamp = r.time_added.isoformat()

        rsp = self.apiGet(self.get_list_url(), {
            'time-added-from': timestamp,
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         public_review_requests.count() - start_index)
        self.assertEqual(rsp['count'],
                         public_review_requests.filter(
                            time_added__gte=r.time_added).count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_time_added_to(self):
        """Testing the GET review-requests/?time-added-to= API"""
        start_index = 3

        public_review_requests = \
            ReviewRequest.objects.public().order_by('time_added')
        r = public_review_requests[start_index]
        timestamp = r.time_added.isoformat()

        rsp = self.apiGet(self.get_list_url(), {
            'time-added-to': timestamp,
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         public_review_requests.count() - start_index + 1)
        self.assertEqual(rsp['count'],
                         public_review_requests.filter(
                             time_added__lt=r.time_added).count())

    def test_get_reviewrequests_with_last_updated_from(self):
        """Testing the GET review-requests/?last-updated-from= API"""
        start_index = 3

        public_review_requests = \
            ReviewRequest.objects.public().order_by('last_updated')
        r = public_review_requests[start_index]
        timestamp = r.last_updated.isoformat()

        rsp = self.apiGet(self.get_list_url(), {
            'last-updated-from': timestamp,
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         public_review_requests.count() - start_index)
        self.assertEqual(rsp['count'],
                         public_review_requests.filter(
                             last_updated__gte=r.last_updated).count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequests_with_last_updated_to(self):
        """Testing the GET review-requests/?last-updated-to= API"""
        start_index = 3

        public_review_requests = \
            ReviewRequest.objects.public().order_by('last_updated')
        r = public_review_requests[start_index]
        timestamp = r.last_updated.isoformat()

        rsp = self.apiGet(self.get_list_url(), {
            'last-updated-to': timestamp,
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         public_review_requests.count() - start_index + 1)
        self.assertEqual(rsp['count'],
                         public_review_requests.filter(
                             last_updated__lt=r.last_updated).count())

    @add_fixtures(['test_site'])
    def test_get_reviewrequest_not_modified(self):
        """Testing the GET review-requests/<id>/ API with Not Modified response"""
        review_request = ReviewRequest.objects.public()[0]

        self._testHttpCaching(self.get_item_url(review_request.id),
                              check_last_modified=True)

    def test_post_reviewrequests(self):
        """Testing the POST review-requests/ API"""
        rsp = self.apiPost(self.get_list_url(), {
            'repository': self.repository.path,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['repository']['href'],
            self.base_url +
            RepositoryResourceTests.get_item_url(self.repository.id))

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        return ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def test_post_reviewrequests_with_repository_name(self):
        """Testing the POST review-requests/ API with a repository name"""
        rsp = self.apiPost(self.get_list_url(), {
            'repository': self.repository.name,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['repository']['href'],
            self.base_url +
            RepositoryResourceTests.get_item_url(self.repository.id))

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        return ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def test_post_reviewrequests_with_no_repository(self):
        """Testing the POST review-requests/ API with no repository"""
        rsp = self.apiPost(self.get_list_url(),
                           expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertFalse('repository' in rsp['review_request']['links'])

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])
        self.assertEqual(review_request.repository, None)

    @add_fixtures(['test_site'])
    def test_post_reviewrequests_with_site(self):
        """Testing the POST review-requests/ API with a local site"""
        self._login_user(local_site=True)

        repository = Repository.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self.apiPost(self.get_list_url(self.local_site_name),
                           { 'repository': repository.path, },
                           expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['links']['repository']['title'],
                         repository.name)

    @add_fixtures(['test_site'])
    def test_post_reviewrequests_with_site_no_access(self):
        """Testing the POST review-requests/ API with a local site and Permission Denied error"""
        repository = Repository.objects.filter(
            local_site__name=self.local_site_name)[0]

        self.apiPost(self.get_list_url(self.local_site_name),
                     { 'repository': repository.path, },
                     expected_status=403)

    @add_fixtures(['test_site'])
    def test_post_reviewrequests_with_site_invalid_repository_error(self):
        """Testing the POST review-requests/ API with a local site and Invalid Repository error"""
        self._login_user(local_site=True)
        rsp = self.apiPost(self.get_list_url(self.local_site_name),
                           { 'repository': self.repository.path, },
                           expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    def test_post_reviewrequests_with_invalid_repository_error(self):
        """Testing the POST review-requests/ API with Invalid Repository error"""
        rsp = self.apiPost(self.get_list_url(), {
            'repository': 'gobbledygook',
        }, expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    @add_fixtures(['test_site'])
    def test_post_reviewrequests_with_no_site_invalid_repository_error(self):
        """Testing the POST review-requests/ API with Invalid Repository error from a site-local repository"""
        repository = Repository.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self.apiPost(self.get_list_url(), {
            'repository': repository.path,
        }, expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    def test_post_reviewrequests_with_submit_as(self):
        """Testing the POST review-requests/?submit_as= API"""
        self.user.is_superuser = True
        self.user.save()

        rsp = self.apiPost(self.get_list_url(), {
            'repository': self.repository.path,
            'submit_as': 'doc',
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['repository']['href'],
            self.base_url +
            RepositoryResourceTests.get_item_url(self.repository.id))
        self.assertEqual(
            rsp['review_request']['links']['submitter']['href'],
            self.base_url +
            UserResourceTests.get_item_url('doc'))

        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def test_post_reviewrequests_with_submit_as_and_permission_denied_error(self):
        """Testing the POST review-requests/?submit_as= API with Permission Denied error"""
        rsp = self.apiPost(self.get_list_url(), {
            'repository': self.repository.path,
            'submit_as': 'doc',
        }, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequest_status_discarded(self):
        """Testing the PUT review-requests/<id>/?status=discarded API"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        rsp = self.apiPut(self.get_item_url(r.display_id), {
            'status': 'discarded',
            'description': 'comment',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'D')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'D')

    def test_put_reviewrequest_status_discarded_with_permission_denied(self):
        """Testing the PUT review-requests/<id>/?status=discarded API with Permission Denied"""
        q = ReviewRequest.objects.filter(public=True, status='P')
        r = q.exclude(submitter=self.user)[0]

        rsp = self.apiPut(self.get_item_url(r.display_id), {
            'status': 'discarded',
        }, expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequest_status_pending(self):
        """Testing the PUT review-requests/<id>/?status=pending API"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.close(ReviewRequest.SUBMITTED)
        r.save()

        rsp = self.apiPut(self.get_item_url(r.display_id), {
            'status': 'pending',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'P')

    def test_put_reviewrequest_status_submitted(self):
        """Testing the PUT review-requests/<id>/?status=submitted API"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        rsp = self.apiPut(self.get_item_url(r.display_id), {
            'status': 'submitted',
            'description': 'comment',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'S')

    @add_fixtures(['test_site'])
    def test_put_reviewrequest_status_submitted_with_site(self):
        """Testing the PUT review-requests/<id>/?status=submitted API with a local site"""
        self._login_user(local_site=True)
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter__username='doc',
                                         local_site__name=self.local_site_name)[0]

        rsp = self.apiPut(self.get_item_url(r.display_id,
                                            self.local_site_name),
                          {
                              'status': 'submitted',
                              'description': 'comment'
                          },
                          expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'S')

    @add_fixtures(['test_site'])
    def test_put_reviewrequest_status_submitted_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/?status=submitted API with a local site and Permission Denied error"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter__username='doc',
                                         local_site__name=self.local_site_name)[0]

        self.apiPut(self.get_item_url(r.display_id, self.local_site_name),
                    { 'status': 'submitted' },
                    expected_status=403)

    @add_fixtures(['test_site'])
    def test_get_reviewrequest(self):
        """Testing the GET review-requests/<id>/ API"""
        review_request = ReviewRequest.objects.public()[0]

        rsp = self.apiGet(self.get_item_url(review_request.display_id),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.display_id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    @add_fixtures(['test_site'])
    def test_get_reviewrequest_with_site(self):
        """Testing the GET review-requests/<id>/ API with a local site"""
        self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        rsp = self.apiGet(self.get_item_url(review_request.display_id,
                                            self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    @add_fixtures(['test_site'])
    def test_get_reviewrequest_with_site_no_access(self):
        """Testing the GET review-requests/<id>/ API with a local site and Permission Denied error"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        self.apiGet(self.get_item_url(review_request.display_id,
                                      self.local_site_name),
                    expected_status=403)

    def test_get_reviewrequest_with_non_public_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/ API with non-public and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=False,
            local_site=None).exclude(submitter=self.user)[0]

        rsp = self.apiGet(self.get_item_url(review_request.display_id),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reviewrequest_with_invite_only_group_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/ API with invite-only group and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True,
            local_site=None).exclude(submitter=self.user)[0]
        review_request.target_groups.clear()
        review_request.target_people.clear()

        group = Group(name='test-group', invite_only=True)
        group.save()

        review_request.target_groups.add(group)
        review_request.save()

        rsp = self.apiGet(self.get_item_url(review_request.display_id),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_get_reviewrequest_with_invite_only_group_and_target_user(self):
        """Testing the GET review-requests/<id>/ API with invite-only group and target user"""
        review_request = ReviewRequest.objects.filter(public=True,
            local_site=None).exclude(submitter=self.user)[0]
        review_request.target_groups.clear()
        review_request.target_people.clear()

        group = Group(name='test-group', invite_only=True)
        group.save()

        review_request.target_groups.add(group)
        review_request.target_people.add(self.user)
        review_request.save()

        rsp = self.apiGet(self.get_item_url(review_request.display_id),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.display_id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    def test_get_reviewrequest_reviews_with_invite_only_group_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/reviews/ API with invite-only group and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True,
            local_site=None).exclude(submitter=self.user)[0]
        review_request.target_groups.clear()
        review_request.target_people.clear()

        group = Group(name='test-group', invite_only=True)
        group.save()

        review_request.target_groups.add(group)
        review_request.save()

        rsp = self.apiGet(
            local_site_reverse(
                'reviews-resource',
                local_site_name=None,
                kwargs={'review_request_id': review_request.display_id}),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reviewrequest_with_repository_and_changenum(self):
        """Testing the GET review-requests/?repository=&changenum= API"""
        review_request = \
            ReviewRequest.objects.filter(changenum__isnull=False)[0]

        rsp = self.apiGet(self.get_list_url(), {
            'repository': review_request.repository.id,
            'changenum': review_request.changenum,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)
        self.assertEqual(rsp['review_requests'][0]['id'],
                         review_request.display_id)
        self.assertEqual(rsp['review_requests'][0]['summary'],
                         review_request.summary)
        self.assertEqual(rsp['review_requests'][0]['changenum'],
                         review_request.changenum)

    def test_delete_reviewrequest(self):
        """Testing the DELETE review-requests/<id>/ API"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assert_(self.user.has_perm('reviews.delete_reviewrequest'))

        review_request = ReviewRequest.objects.from_user(self.user.username)[0]

        rsp = self.apiDelete(self.get_item_url(review_request.display_id))
        self.assertEqual(rsp, None)
        self.assertRaises(ReviewRequest.DoesNotExist,
                          ReviewRequest.objects.get,
                          pk=review_request.pk)

    def test_delete_reviewrequest_with_permission_denied_error(self):
        """Testing the DELETE review-requests/<id>/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site=None).exclude(submitter=self.user)[0]

        rsp = self.apiDelete(self.get_item_url(review_request.display_id),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_reviewrequest_with_does_not_exist_error(self):
        """Testing the DELETE review-requests/<id>/ API with Does Not Exist error"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assert_(self.user.has_perm('reviews.delete_reviewrequest'))

        rsp = self.apiDelete(self.get_item_url(999), expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_reviewrequest_with_site(self):
        """Testing the DELETE review-requests/<id>/ API with a lotal site"""
        user = User.objects.get(username='doc')
        user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        user.save()

        self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.filter(local_site=local_site,
            submitter__username='doc')[0]

        rsp = self.apiDelete(self.get_item_url(review_request.display_id,
                                                self.local_site_name))
        self.assertEqual(rsp, None)
        self.assertRaises(ReviewRequest.DoesNotExist,
                          ReviewRequest.objects.get, pk=review_request.pk)

    @classmethod
    def get_list_url(cls, local_site_name=None):
        return local_site_reverse('review-requests-resource',
                                  local_site_name=local_site_name)

    @classmethod
    def get_item_url(self, review_request_id, local_site_name=None):
        return local_site_reverse('review-request-resource',
                                  local_site_name=local_site_name,
                                  kwargs={
                                      'review_request_id': review_request_id,
                                  })


class ReviewRequestDraftResourceTests(BaseWebAPITestCase):
    """Testing the ReviewRequestDraftResource API tests."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    item_mimetype = _build_mimetype('review-request-draft')

    def _create_update_review_request(self, apiFunc, expected_status,
                                      review_request=None,
                                      local_site_name=None):
        summary = "My Summary"
        description = "My Description"
        testing_done = "My Testing Done"
        branch = "My Branch"
        bugs = "#123,456"

        if review_request is None:
            review_request = \
                ReviewRequest.objects.from_user(self.user.username)[0]

        func_kwargs = {
            'summary': summary,
            'description': description,
            'testing_done': testing_done,
            'branch': branch,
            'bugs_closed': bugs,
        }

        if expected_status >= 400:
            expected_mimetype = None
        else:
            expected_mimetype = self.item_mimetype

        rsp = apiFunc(self.get_url(review_request, local_site_name),
                      func_kwargs,
                      expected_status=expected_status,
                      expected_mimetype=expected_mimetype)

        if expected_status >= 200 and expected_status < 300:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertEqual(rsp['draft']['summary'], summary)
            self.assertEqual(rsp['draft']['description'], description)
            self.assertEqual(rsp['draft']['testing_done'], testing_done)
            self.assertEqual(rsp['draft']['branch'], branch)
            self.assertEqual(rsp['draft']['bugs_closed'], ['123', '456'])

            draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
            self.assertEqual(draft.summary, summary)
            self.assertEqual(draft.description, description)
            self.assertEqual(draft.testing_done, testing_done)
            self.assertEqual(draft.branch, branch)
            self.assertEqual(draft.get_bug_list(), ['123', '456'])

        return rsp

    def _create_update_review_request_with_site(self, apiFunc, expected_status,
                                                relogin=True,
                                                review_request=None):
        if relogin:
            self._login_user(local_site=True)

        if review_request is None:
            review_request = ReviewRequest.objects.from_user('doc',
                local_site=LocalSite.objects.get(name=self.local_site_name))[0]

        return self._create_update_review_request(
            apiFunc, expected_status, review_request, self.local_site_name)

    def test_put_reviewrequestdraft(self):
        """Testing the PUT review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPut, 200)

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_site(self):
        """Testing the PUT review-requests/<id>/draft/ API with a local site"""
        self._create_update_review_request_with_site(self.apiPut, 200)

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/draft/ API with a local site and Permission Denied error"""
        rsp = self._create_update_review_request_with_site(
            self.apiPut, 403, relogin=False)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_reviewrequestdraft(self):
        """Testing the POST review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPost, 201)

    @add_fixtures(['test_site'])
    def test_post_reviewrequestdraft_with_site(self):
        """Testing the POST review-requests/<id>/draft/ API with a local site"""
        self._create_update_review_request_with_site(self.apiPost, 201)

    @add_fixtures(['test_site'])
    def test_post_reviewrequestdraft_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/ API with a local site and Permission Denied error"""
        rsp = self._create_update_review_request_with_site(
            self.apiPost, 403, relogin=False)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequestdraft_with_changedesc(self):
        """Testing the PUT review-requests/<id>/draft/ API with a change description"""
        changedesc = 'This is a test change description.'
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.publish(self.user)

        rsp = self.apiPost(self.get_url(review_request), {
            'changedescription': changedesc,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['changedescription'], changedesc)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertNotEqual(draft.changedesc, None)
        self.assertEqual(draft.changedesc.text, changedesc)

    def test_put_reviewrequestdraft_with_depends_on(self):
        """Testing the PUT review-requests/<id>/draft/ API with depends_on field"""
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.publish(self.user)

        rsp = self.apiPut(self.get_url(review_request), {
            'depends_on': '1, 3',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        depends_1 = ReviewRequest.objects.get(pk=1)
        depends_2 = ReviewRequest.objects.get(pk=3)

        depends_on = rsp['draft']['depends_on']
        self.assertEqual(len(depends_on), 2)
        self.assertEqual(rsp['draft']['depends_on'][0]['title'],
                         depends_1.summary)
        self.assertEqual(rsp['draft']['depends_on'][1]['title'],
                         depends_2.summary)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertEqual(list(draft.depends_on.all()), [depends_1, depends_2])
        self.assertEqual(list(depends_1.draft_blocks.all()), [draft])
        self.assertEqual(list(depends_2.draft_blocks.all()), [draft])

    @add_fixtures(['test_site'])
    def test_put_reviewrequestdraft_with_depends_on_and_site(self):
        """Testing the PUT review-requests/<id>/draft/ API with depends_on field and local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.from_user(
            'doc', local_site=local_site)[0]

        self._login_user(local_site=True)

        depends_1 = ReviewRequest.objects.create(self.user, self.repository)
        depends_1.summary = "Test review request"
        depends_1.local_site = local_site
        depends_1.local_id = 3
        depends_1.public = True
        depends_1.save()

        # This isn't the review request we want to match.
        bad_depends = ReviewRequest.objects.get(pk=3)

        rsp = self.apiPut(self.get_url(review_request, self.local_site_name), {
            'depends_on': '3',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        depends_on = rsp['draft']['depends_on']
        self.assertEqual(len(depends_on), 1)
        self.assertNotEqual(rsp['draft']['depends_on'][0]['title'],
                            bad_depends.summary)
        self.assertEqual(rsp['draft']['depends_on'][0]['title'],
                         depends_1.summary)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertEqual(list(draft.depends_on.all()), [depends_1])
        self.assertEqual(list(depends_1.draft_blocks.all()), [draft])
        self.assertEqual(bad_depends.draft_blocks.count(), 0)

    def test_put_reviewrequestdraft_with_depends_on_invalid_id(self):
        """Testing the PUT review-requests/<id>/draft/ API with depends_on field and invalid ID"""
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.publish(self.user)

        rsp = self.apiPut(self.get_url(review_request), {
            'depends_on': '10000',
        }, expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')

        draft = review_request.get_draft()
        self.assertEqual(draft.depends_on.count(), 0)

    def test_put_reviewrequestdraft_with_invalid_field_name(self):
        """Testing the PUT review-requests/<id>/draft/ API with Invalid Form Data error"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]

        rsp = self.apiPut(self.get_url(review_request), {
            'foobar': 'foo',
        }, 400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('foobar' in rsp['fields'])

    def test_put_reviewrequestdraft_with_permission_denied_error(self):
        """Testing the PUT review-requests/<id>/draft/ API with Permission Denied error"""
        bugs_closed = '123,456'
        review_request = ReviewRequest.objects.from_user('admin')[0]

        rsp = self.apiPut(self.get_url(review_request), {
            'bugs_closed': bugs_closed,
        }, 403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequestdraft_publish(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API"""
        # Set some data first.
        self.test_put_reviewrequestdraft()

        review_request = ReviewRequest.objects.from_user(self.user.username)[0]

        rsp = self.apiPut(self.get_url(review_request), {
            'public': True,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")
        self.assertTrue(review_request.public)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Review Request 4: My Summary")
        self.assertValidRecipients(["doc", "grumpy"], [])

    def test_put_reviewrequestdraft_publish_with_new_review_request(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API with a new review request"""
        # Set some data first.
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.target_people = [
            User.objects.get(username='doc')
        ]
        review_request.save()

        self._create_update_review_request(self.apiPut, 200, review_request)

        rsp = self.apiPut(self.get_url(review_request), {
            'public': True,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")
        self.assertTrue(review_request.public)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Review Request 10: My Summary")
        self.assertValidRecipients(["doc", "grumpy"], [])

    def test_delete_reviewrequestdraft(self):
        """Testing the DELETE review-requests/<id>/draft/ API"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]
        summary = review_request.summary
        description = review_request.description

        # Set some data.
        self.test_put_reviewrequestdraft()

        self.apiDelete(self.get_url(review_request))

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    @add_fixtures(['test_site'])
    def test_delete_reviewrequestdraft_with_site(self):
        """Testing the DELETE review-requests/<id>/draft/ API with a local site"""
        review_request = ReviewRequest.objects.from_user('doc',
            local_site=LocalSite.objects.get(name=self.local_site_name))[0]
        summary = review_request.summary
        description = review_request.description

        self.test_put_reviewrequestdraft_with_site()

        self.apiDelete(self.get_url(review_request, self.local_site_name))

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    @add_fixtures(['test_site'])
    def test_delete_reviewrequestdraft_with_site_no_access(self):
        """Testing the DELETE review-requests/<id>/draft/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.from_user('doc',
            local_site=LocalSite.objects.get(name=self.local_site_name))[0]
        rsp = self.apiDelete(
            self.get_url(review_request, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def get_url(self, review_request, local_site_name=None):
        return local_site_reverse(
            'draft-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })


class ReviewResourceTests(BaseWebAPITestCase):
    """Testing the ReviewResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('reviews')
    item_mimetype = _build_mimetype('review')

    def test_get_reviews(self):
        """Testing the GET review-requests/<id>/reviews/ API"""
        review_request = Review.objects.filter()[0].review_request
        rsp = self.apiGet(self.get_list_url(review_request),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['reviews']), review_request.reviews.count())

    @add_fixtures(['test_site'])
    def test_get_reviews_with_site(self):
        """Testing the GET review-requests/<id>/reviews/ API with a local site"""
        self.test_post_reviews_with_site(public=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        rsp = self.apiGet(self.get_list_url(review_request,
                                            self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['reviews']), review_request.reviews.count())

    @add_fixtures(['test_site'])
    def test_get_reviews_with_site_no_access(self):
        """Testing the GET review-requests/<id>/reviews/ API with a local site and Permission Denied error"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        rsp = self.apiGet(self.get_list_url(review_request,
                                            self.local_site_name),
                          expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reviews_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/?counts-only=1 API"""
        review_request = Review.objects.all()[0].review_request
        rsp = self.apiGet(self.get_list_url(review_request), {
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review_request.reviews.count())

    def test_get_review_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/ API with Not Modified response"""
        review = Review.objects.all()[0]
        self._testHttpCaching(
            self.get_item_url(review.review_request, review.id),
            check_last_modified=True)

    @add_fixtures(['test_site'])
    def test_post_reviews(self):
        """Testing the POST review-requests/<id>/reviews/ API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public(local_site=None)[0]
        review_request.reviews = []
        review_request.save()

        rsp, response = self.api_post_with_response(
            self.get_list_url(review_request),
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
                         self.get_item_url(review_request, review.id))

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, False)

        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_reviews_with_site(self, public=False):
        """Testing the POST review-requests/<id>/reviews/ API with a local site"""
        self._login_user(local_site=True)

        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        local_site = LocalSite.objects.get(name=self.local_site_name)

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        review_request.reviews = []
        review_request.save()

        post_data = {
            'ship_it': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
            'public': public,
        }

        rsp, response = self.api_post_with_response(
            self.get_list_url(review_request, self.local_site_name),
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
        """Testing the POST review-requests/<id>/reviews/ API with a local site and Permission Denied error"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        rsp = self.apiPost(self.get_list_url(review_request,
                                             self.local_site_name),
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_put_review(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public(local_site=None)[0]
        review_request.reviews = []
        review_request.save()

        rsp, response = self.api_post_with_response(
            self.get_list_url(review_request),
            expected_mimetype=self.item_mimetype)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        review_url = response['Location']

        rsp = self.apiPut(review_url, {
            'ship_it': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        }, expected_mimetype=self.item_mimetype)

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
        """Testing the PUT review-requests/<id>/reviews/<id>/ API with a local site"""
        self._login_user(local_site=True)

        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        # Clear out any reviews on the first review request we find.
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        review_request.reviews = []
        review_request.save()

        rsp, response = self.api_post_with_response(
            self.get_list_url(review_request, self.local_site_name),
            expected_mimetype=self.item_mimetype)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        review_url = response['Location']

        rsp = self.apiPut(review_url, {
            'ship_it': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        }, expected_mimetype=self.item_mimetype)

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
        """Testing the PUT review-requests/<id>/reviews/<id>/ API with a local site and Permission Denied error"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.save()

        rsp = self.apiPut(self.get_item_url(review_request, review.id,
                                            self.local_site_name),
                          { 'ship_it': True, },
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_review_with_published_review(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API with pre-published review"""
        review = Review.objects.filter(user=self.user, public=True,
                                       base_reply_to__isnull=True)[0]

        self.apiPut(self.get_item_url(review.review_request, review.id), {
            'ship_it': True,
        }, expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_review_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/?public=1 API"""
        body_top = "My Body Top"
        body_bottom = ""
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp, response = \
            self.api_post_with_response(self.get_list_url(review_request),
                                        expected_mimetype=self.item_mimetype)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        review_url = response['Location']

        rsp = self.apiPut(review_url, {
            'public': True,
            'ship_it': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        }, expected_mimetype=self.item_mimetype)

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, True)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request 8: Interdiff Revision Test")
        self.assertValidRecipients(["admin", "grumpy"], [])

    @add_fixtures(['test_site'])
    def test_delete_review(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API"""
        # Set up the draft to delete.
        review = self.test_put_review()
        review_request = review.review_request

        self.apiDelete(self.get_item_url(review_request, review.id))
        self.assertEqual(review_request.reviews.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_review_with_permission_denied(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with Permission Denied error"""
        # Set up the draft to delete.
        review = self.test_put_review()
        review.user = User.objects.get(username='doc')
        review.save()

        review_request = review.review_request
        old_count = review_request.reviews.count()

        self.apiDelete(self.get_item_url(review_request, review.id),
                       expected_status=403)
        self.assertEqual(review_request.reviews.count(), old_count)

    def test_delete_review_with_published_review(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with pre-published review"""
        review = Review.objects.filter(user=self.user, public=True,
                                       base_reply_to__isnull=True)[0]
        review_request = review.review_request
        old_count = review_request.reviews.count()

        self.apiDelete(self.get_item_url(review_request, review.id),
                       expected_status=403)
        self.assertEqual(review_request.reviews.count(), old_count)

    def test_delete_review_with_does_not_exist(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with Does Not Exist error"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiDelete(self.get_item_url(review_request, 919239),
                             expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_review_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with a local site"""
        review = self.test_put_review_with_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]

        self.apiDelete(self.get_item_url(review_request, review.id,
                                          self.local_site_name))
        self.assertEqual(review_request.reviews.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_review_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with a local site and Permission Denied error"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.save()

        rsp = self.apiDelete(self.get_item_url(review_request, review.id,
                                                self.local_site_name),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @classmethod
    def get_list_url(cls, review_request, local_site_name=None):
        return local_site_reverse(
            'reviews-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })

    def get_item_url(self, review_request, review_id, local_site_name=None):
        return local_site_reverse(
            'review-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'review_id': review_id,
            })


class ReviewCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('review-diff-comments')
    item_mimetype = _build_mimetype('review-diff-comment')

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff_comments(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), review.comments.count())

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff_comments_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/?counts-only=1 API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet(self.get_list_url(review), {
            'counts-only': 1,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.comments.count())

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diff_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API with a local site"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), review.comments.count())

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diff_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API with a local site and Permission Denied error"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)

        self._login_user()

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff_comment_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with Not Modified response"""
        comment = Comment.objects.all()[0]
        self._testHttpCaching(
            self.get_item_url(comment.review.get(), comment.id),
            check_last_modified=True)

    def test_post_diff_comments(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API"""
        diff_comment_text = "Test diff comment"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        DiffSet.objects.get(pk=rsp['diff']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)
        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_diff_comments_with_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with a local site"""
        diff_comment_text = "Test diff comment"
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        self._login_user(local_site=True)

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)
        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)

        return review_id

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_diff_comments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.save()

        rsp = self.apiPost(self.get_list_url(review, self.local_site_name),
                           {},
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    def test_post_diff_comments_with_interdiff(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with interdiff"""
        comment_text = "Test diff comment"

        rsp, review_request_id, review_id, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    def test_get_diff_comments_with_interdiff(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/ API with interdiff"""
        comment_text = "Test diff comment"

        rsp, review_request_id, review_id, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(self.get_list_url(review), {
            'interdiff-revision': interdiff_revision,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    def test_delete_diff_comment_with_interdiff(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API"""
        comment_text = "This is a test comment."

        rsp, review_request_id, review_id, interdiff_revision = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiDelete(rsp['diff_comment']['links']['self']['href'])

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_diff_comment_with_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with a local site"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)
        comment = review.comments.all()[0]
        comment_count = review.comments.count()

        self.apiDelete(self.get_item_url(review, comment.id,
                                         self.local_site_name))

        self.assertEqual(review.comments.count(), comment_count - 1)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_diff_comment_with_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API with a local site and Permission Denied error"""
        review_id = self.test_post_diff_comments_with_site()
        review = Review.objects.get(pk=review_id)
        comment = review.comments.all()[0]

        self._login_user()

        rsp = self.apiDelete(
            self.get_item_url(review, comment.id, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_diff_comments_with_issue(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with an issue"""
        diff_comment_text = "Test diff comment with an opened issue"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        DiffSet.objects.get(pk=rsp['diff']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text,
                                 issue_opened=True)

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)
        self.assertTrue(rsp['diff_comments'][0]['issue_opened'])

    def test_update_diff_comment_with_issue(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id> API with an issue"""
        diff_comment_text = "Test diff comment with an opened issue"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        DiffSet.objects.get(pk=rsp['diff']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        review_id = rsp['review']['id']

        rsp = self._postNewDiffComment(review_request, review_id,
                                       diff_comment_text, issue_opened=True)

        rsp = self.apiPut(rsp['diff_comment']['links']['self']['href'], {
            'issue_opened': False,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertFalse(rsp['diff_comment']['issue_opened'])

    def test_update_diff_comment_issue_status(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/diff-comments/<id> API with an issue"""
        diff_comment_text = "Test diff comment with an opened issue"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        DiffSet.objects.get(pk=rsp['diff']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        rsp = self._postNewDiffComment(review_request, review_id,
                                       diff_comment_text, issue_opened=True)

        # First, let's ensure that the user that has created the comment
        # cannot alter the issue_status while the review is unpublished.

        rsp = self.apiPut(rsp['diff_comment']['links']['self']['href'], {
            'issue_status': 'resolved',
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        # The issue_status should still be "open"
        self.assertEqual(rsp['diff_comment']['issue_status'], 'open')

        # Next, let's publish the review, and try altering the issue_status.
        # This should be allowed, since the review request was made by the
        # current user.
        review.public = True
        review.save()

        rsp = self.apiPut(rsp['diff_comment']['links']['self']['href'], {
            'issue_status': 'resolved',
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff_comment']['issue_status'], 'resolved')

        # Finally, let's make sure that this user cannot alter the issue_status
        # on a diff-comment for a review request that they didn't make.
        review_request.submitter = User.objects.get(username='doc')
        review_request.save()

        rsp = self.apiPut(rsp['diff_comment']['links']['self']['href'], {
            'issue_status': 'dropped',
        }, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _common_post_interdiff_comments(self, comment_text):
        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        review_request.publish(self.user)
        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        filediff = diffset.files.all()[0]

        # Post the second diff.
        rsp = self._postNewDiff(review_request)
        review_request.publish(self.user)
        interdiffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        interfilediff = interdiffset.files.all()[0]

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        rsp = self._postNewDiffComment(review_request, review_id,
                                       comment_text,
                                       filediff_id=filediff.id,
                                       interfilediff_id=interfilediff.id)

        return rsp, review_request.id, review_id, interdiffset.revision

    @classmethod
    def get_list_url(cls, review, local_site_name=None):
        return local_site_reverse(
            'diff-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
            })

    def get_item_url(self, review, comment_id, local_site_name=None):
        return local_site_reverse(
            'diff-comment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
                'comment_id': comment_id,
            })


class DraftReviewScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('screenshot-comments')
    item_mimetype = _build_mimetype('screenshot-comment')

    def test_get_review_screenshot_comments(self):
        """Testing the GET review-requests/<id>/reviews/draft/screenshot-comments/ API"""
        screenshot_comment_text = "Test screenshot comment"
        x, y, w, h = 2, 2, 10, 10

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewScreenshotComment(review_request, review_id, screenshot,
                                       screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_review_screenshot_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/draft/screenshot-comments/ APIs with a local site"""
        screenshot_comment_text = "Test screenshot comment"
        x, y, w, h = 2, 2, 10, 10

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        review_request.publish(User.objects.get(username='doc'))

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewScreenshotComment(review_request, review_id, screenshot,
                                       screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)

    @classmethod
    def get_list_url(self, review, local_site_name=None):
        return local_site_reverse(
            'screenshot-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
            })

    def get_item_url(self, review, comment_id, local_site_name=None):
        return local_site_reverse(
            'screenshot-comment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
                'comment_id': comment_id,
            })


class ReviewReplyResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('review-replies')
    item_mimetype = _build_mimetype('review-reply')

    def test_get_replies(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.test_put_reply()

        public_replies = review.public_replies()

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), public_replies.count())

        for i in range(public_replies.count()):
            reply = public_replies[i]
            self.assertEqual(rsp['replies'][i]['id'], reply.id)
            self.assertEqual(rsp['replies'][i]['body_top'], reply.body_top)
            self.assertEqual(rsp['replies'][i]['body_bottom'],
                             reply.body_bottom)

    def test_get_replies_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies/?counts-only=1 API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.test_put_reply()

        rsp = self.apiGet('%s?counts-only=1' % self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.public_replies().count())

    @add_fixtures(['test_site'])
    def test_get_replies_with_site(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = True
        reply.base_reply_to = review
        reply.save()

        self._login_user(local_site=True)

        public_replies = review.public_replies()

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), public_replies.count())

        for i in range(public_replies.count()):
            reply = public_replies[i]
            self.assertEqual(rsp['replies'][i]['id'], reply.id)
            self.assertEqual(rsp['replies'][i]['body_top'], reply.body_top)
            self.assertEqual(rsp['replies'][i]['body_bottom'],
                             reply.body_bottom)

    @add_fixtures(['test_site'])
    def test_get_replies_with_site_no_access(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reply_not_modified(self):
        """Testing the GET review-requests/<id>/reviews/<id>/ with Not Modified response"""
        reply = \
            Review.objects.filter(base_reply_to__isnull=False, public=True)[0]
        self._testHttpCaching(self.get_item_url(reply.base_reply_to, reply.id),
                              check_last_modified=True)

    def test_post_replies(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost(self.get_list_url(review), {
            'body_top': 'Test',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_replies_with_site(self):
        """Testing the POST review-requsets/<id>/reviews/<id>/replies/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        self._login_user(local_site=True)

        rsp = self.apiPost(self.get_list_url(review, self.local_site_name),
                           { 'body_top': 'Test', },
                           expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(mail.outbox), 0)

    @add_fixtures(['test_site'])
    def test_post_replies_with_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        rsp = self.apiPost(self.get_list_url(review, self.local_site_name),
                           { 'body_top': 'Test', },
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_replies_with_body_top(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with body_top"""
        body_top = 'My Body Top'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost(self.get_list_url(review), {
            'body_top': body_top,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_top, body_top)

    def test_post_replies_with_body_bottom(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with body_bottom"""
        body_bottom = 'My Body Bottom'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost(self.get_list_url(review), {
            'body_bottom': body_bottom,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_bottom, body_bottom)

    def test_put_reply(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp, response = self.api_post_with_response(
            self.get_list_url(review),
            expected_mimetype=self.item_mimetype)

        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(response['Location'], {
            'body_top': 'Test',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_put_reply_with_site(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        self._login_user(local_site=True)

        rsp, response = self.api_post_with_response(
            self.get_list_url(review, self.local_site_name),
            expected_mimetype=self.item_mimetype)
        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(response['Location'],
                          { 'body_top': 'Test', },
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_put_reply_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = True
        reply.base_reply_to = review
        reply.save()

        rsp = self.apiPut(self.get_item_url(review, reply.id,
                                            self.local_site_name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reply_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/?public=1 API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp, response = self.api_post_with_response(
            self.get_list_url(review),
            expected_mimetype=self.item_mimetype)

        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(response['Location'], {
            'body_top': 'Test',
            'public': True,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.public, True)

        self.assertEqual(len(mail.outbox), 1)

    def test_delete_reply(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost(self.get_list_url(review), {
            'body_top': 'Test',
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_id = rsp['reply']['id']
        rsp = self.apiDelete(rsp['reply']['links']['self']['href'])

        self.assertEqual(Review.objects.filter(pk=reply_id).count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_reply_with_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = False
        reply.base_reply_to = review
        reply.save()

        self._login_user(local_site=True)
        self.apiDelete(self.get_item_url(review, reply.id,
                                         self.local_site_name))
        self.assertEqual(review.replies.count(), 0)

    @add_fixtures(['test_site'])
    def test_delete_reply_with_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API with a local site and Permission Denied error"""
        review_request = \
            ReviewRequest.objects.filter(local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.public = True
        review.save()

        reply = Review()
        reply.review_request = review_request
        reply.user = review.user
        reply.public = False
        reply.base_reply_to = review
        reply.save()

        rsp = self.apiDelete(self.get_item_url(review, reply.id,
                                               self.local_site_name),
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @classmethod
    def get_list_url(cls, review, local_site_name=None):
        return local_site_reverse(
            'replies-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
            })

    def get_item_url(self, review, reply_id, local_site_name=None):
        return local_site_reverse(
            'reply-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
                'reply_id': reply_id,
            })


class ReviewReplyDiffCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyDiffCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('review-reply-diff-comments')
    item_mimetype = _build_mimetype('review-reply-diff-comment')

    def test_post_reply_with_diff_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API"""
        comment_text = "My Comment Text"

        comment = Comment.objects.all()[0]
        review = comment.review.get()

        # Create the reply
        rsp = self.apiPost(
            ReviewReplyResourceTests.get_list_url(review),
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        diff_comments_url = rsp['reply']['links']['diff_comments']['href']

        rsp = self.apiPost(diff_comments_url, {
            'reply_to_id': comment.id,
            'text': comment_text,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, diff_comments_url

    @add_fixtures(['test_site'])
    def test_post_reply_with_diff_comment_and_local_site(self, badlogin=False):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API with a local site"""
        comment_text = 'My Comment Text'

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        review = Review()
        review.review_request = review_request
        review.user = User.objects.get(username='doc')
        review.save()

        self._login_user(local_site=True)

        rsp = self._postNewDiffComment(review_request, review.id, 'Comment')
        review = Review.objects.get(pk=review.id)
        review.public = True
        review.save()

        self.assertTrue('diff_comment' in rsp)
        self.assertTrue('id' in rsp['diff_comment'])
        comment_id = rsp['diff_comment']['id']
        comment = Comment.objects.get(pk=comment_id)

        rsp = self.apiPost(
            ReviewReplyResourceTests.get_list_url(review, self.local_site_name),
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        diff_comments_url = rsp['reply']['links']['diff_comments']['href']

        post_data = {
            'reply_to_id': comment_id,
            'text': comment_text,
        }

        if badlogin:
            self._login_user()
            rsp = self.apiPost(diff_comments_url,
                               post_data,
                               expected_status=403)
            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
        else:
            rsp = self.apiPost(diff_comments_url,
                               post_data,
                               expected_mimetype=self.item_mimetype)
            self.assertEqual(rsp['stat'], 'ok')

            reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
            self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, diff_comments_url

    @add_fixtures(['test_site'])
    def test_post_reply_with_diff_comment_and_local_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API with a local site and Permission Denied error"""
        self.test_post_reply_with_diff_comment_and_local_site(True)

    def test_post_reply_with_diff_comment_http_303(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API and 303 See Other"""
        comment_text = "My New Comment Text"

        rsp, comment, comments_url = self.test_post_reply_with_diff_comment()

        # Now do it again.
        rsp = self.apiPost(comments_url, {
                'reply_to_id': comment.pk,
                'text': comment_text
            },
            expected_status=303,
            expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def test_put_reply_with_diff_comment(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API"""
        new_comment_text = 'My new comment text'

        # First, create a comment that we can update.
        rsp = self.test_post_reply_with_diff_comment()[0]

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])

        rsp = self.apiPut(rsp['diff_comment']['links']['self']['href'], {
            'text': new_comment_text,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, new_comment_text)

    @add_fixtures(['test_site'])
    def test_put_reply_with_diff_comment_and_local_site(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API with a local site"""
        new_comment_text = 'My new comment text'

        rsp = self.test_post_reply_with_diff_comment_and_local_site()[0]

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])

        rsp = self.apiPut(rsp['diff_comment']['links']['self']['href'],
                          { 'text': new_comment_text, },
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, new_comment_text)

    @add_fixtures(['test_site'])
    def test_put_reply_with_diff_comment_and_local_site_no_access(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API with a local site and Permission Denied error"""
        new_comment_text = 'My new comment text'

        rsp = self.test_post_reply_with_diff_comment_and_local_site()[0]

        self._login_user()
        rsp = self.apiPut(rsp['diff_comment']['links']['self']['href'],
                          { 'text': new_comment_text, },
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_diff_comment(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API"""
        rsp, comment, diff_comments_url = \
            self.test_post_reply_with_diff_comment()

        self.apiDelete(rsp['diff_comment']['links']['self']['href'])

        rsp = self.apiGet(diff_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_diff_comment_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API with a local site"""
        rsp, comment, diff_comments_url = \
            self.test_post_reply_with_diff_comment_and_local_site()

        self.apiDelete(rsp['diff_comment']['links']['self']['href'])

        rsp = self.apiGet(diff_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

    def test_delete_diff_comment_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API and Permission Denied"""
        rsp, comment, diff_comments_url = \
            self.test_post_reply_with_diff_comment()

        self.client.login(username="doc", password="doc")

        self.apiDelete(rsp['diff_comment']['links']['self']['href'],
                       expected_status=403)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_diff_comment_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/<id>/ API with a local site and Permission Denied"""
        rsp, comment, diff_comments_url = \
            self.test_post_reply_with_diff_comment_and_local_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        local_site.users.add(User.objects.get(username='grumpy'))

        self.client.login(username="grumpy", password="grumpy")

        self.apiDelete(rsp['diff_comment']['links']['self']['href'],
                       expected_status=403)


class ReviewReplyScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('review-reply-screenshot-comments')
    item_mimetype = _build_mimetype('review-reply-screenshot-comment')

    def test_post_reply_with_screenshot_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API"""
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        rsp = self._postNewReviewRequest()
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        review_request.publish(self.user)

        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])
        replies_url = rsp['review']['links']['replies']['href']

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertTrue('screenshot_comment' in rsp)
        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

        comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])

        rsp = self.apiPost(
            replies_url,
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('screenshot_comments' in rsp['reply']['links'])

        screenshot_comments_url = \
            rsp['reply']['links']['screenshot_comments']['href']

        rsp = self.apiPost(screenshot_comments_url, {
            'reply_to_id': comment.id,
            'text': comment_text,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)
        self.assertEqual(reply_comment.reply_to, comment)

        return rsp, comment, screenshot_comments_url

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_reply_with_screenshot_comment_and_local_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API with a local site"""
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        user = self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        review_request.publish(user)

        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])
        replies_url = rsp['review']['links']['replies']['href']

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertTrue('screenshot_comment' in rsp)
        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

        comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])

        rsp = self.apiPost(
            replies_url,
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('screenshot_comments' in rsp['reply']['links'])

        screenshot_comments_url = \
            rsp['reply']['links']['screenshot_comments']['href']

        post_data = {
            'reply_to_id': comment.id,
            'text': comment_text,
        }

        rsp = self.apiPost(screenshot_comments_url, post_data,
                           expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, screenshot_comments_url

    def test_post_reply_with_screenshot_comment_http_303(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API"""
        comment_text = "My Comment Text"


        rsp, comment, comments_url = \
            self.test_post_reply_with_screenshot_comment()

        # Now do it again.
        rsp = self.apiPost(comments_url, {
                'reply_to_id': comment.pk,
                'text': comment_text
            },
            expected_status=303,
            expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def test_delete_screenshot_comment(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment()

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(screenshot_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_screenshot_comment_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API with a local site"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment_and_local_site()

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(screenshot_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    def test_delete_screenshot_comment_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API and Permission Denied"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment()

        self.client.login(username="doc", password="doc")

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                       expected_status=403)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_screenshot_comment_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/<id>/ API with a local site and Permission Denied"""
        rsp, comment, screenshot_comments_url = \
            self.test_post_reply_with_screenshot_comment_and_local_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        local_site.users.add(User.objects.get(username='grumpy'))

        self.client.login(username="grumpy", password="grumpy")

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                       expected_status=403)


class ChangeResourceTests(BaseWebAPITestCase):
    """Testing the ChangeResourceAPIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('review-request-changes')
    item_mimetype = _build_mimetype('review-request-change')

    def test_get_changes(self):
        """Testing the GET review-requests/<id>/changes/ API"""
        rsp = self._postNewReviewRequest()
        self.assertTrue('changes' in rsp['review_request']['links'])

        r = ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        now = timezone.now()
        change1 = ChangeDescription(public=True,
                                    timestamp=now)
        change1.record_field_change('summary', 'foo', 'bar')
        change1.save()
        r.changedescs.add(change1)

        change2 = ChangeDescription(public=True,
                                    timestamp=now + timedelta(seconds=1))
        change2.record_field_change('description', 'foo', 'bar')
        change2.save()
        r.changedescs.add(change2)

        rsp = self.apiGet(rsp['review_request']['links']['changes']['href'],
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 2)

        self.assertEqual(rsp['changes'][0]['id'], change2.pk)
        self.assertEqual(rsp['changes'][1]['id'], change1.pk)

    def test_get_change(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API"""
        def write_fields(obj, index):
            for field, data in test_data.iteritems():
                value = data[index]

                if isinstance(value, list) and field not in model_fields:
                    value = ','.join(value)

                if field == 'diff':
                    field = 'diffset'

                setattr(obj, field, value)

        changedesc_text = 'Change description text'
        user1, user2 = User.objects.all()[:2]
        group1, group2 = Group.objects.all()[:2]
        diff1, diff2 = DiffSet.objects.all()[:2]
        old_screenshot_caption = 'old screenshot'
        new_screenshot_caption = 'new screenshot'
        screenshot1 = Screenshot.objects.create()
        screenshot2 = Screenshot.objects.create()
        screenshot3 = Screenshot.objects.create(caption=old_screenshot_caption)

        for screenshot in [screenshot1, screenshot2, screenshot3]:
            f = open(self._getTrophyFilename(), 'r')
            screenshot.image.save('foo.png', File(f), save=True)
            f.close()

        test_data = {
            'summary': ('old summary', 'new summary', None, None),
            'description': ('old description', 'new description', None, None),
            'testing_done': ('old testing done', 'new testing done',
                             None, None),
            'branch': ('old branch', 'new branch', None, None),
            'bugs_closed': (['1', '2', '3'], ['2', '3', '4'], ['1'], ['4']),
            'target_people': ([user1], [user2], [user1], [user2]),
            'target_groups': ([group1], [group2], [group1], [group2]),
            'screenshots': ([screenshot1, screenshot3],
                            [screenshot2, screenshot3],
                            [screenshot1],
                            [screenshot2]),
            'diff': (diff1, diff2, None, diff2),
        }
        model_fields = ('target_people', 'target_groups', 'screenshots', 'diff')

        rsp = self._postNewReviewRequest()
        self.assertTrue('changes' in rsp['review_request']['links'])

        # Set the initial data on the review request.
        r = ReviewRequest.objects.get(pk=rsp['review_request']['id'])
        write_fields(r, 0)
        r.publish(self.user)

        # Create some draft data that will end up in the change description.
        draft = ReviewRequestDraft.create(r)
        write_fields(draft, 1)

        # Special-case screenshots
        draft.inactive_screenshots = test_data['screenshots'][2]
        screenshot3.draft_caption = new_screenshot_caption
        screenshot3.save()

        draft.changedesc.text = changedesc_text
        draft.changedesc.save()
        draft.save()
        r.publish(self.user)

        # Sanity check the ChangeDescription
        self.assertEqual(r.changedescs.count(), 1)
        change = r.changedescs.get()
        self.assertEqual(change.text, changedesc_text)

        for field, data in test_data.iteritems():
            old, new, removed, added = data
            field_data = change.fields_changed[field]

            if field == 'diff':
                # Diff fields are special. They only have "added".
                self.assertEqual(len(field_data['added']), 1)
                self.assertEqual(field_data['added'][0][2], added.pk)
            elif field in model_fields:
                self.assertEqual([item[2] for item in field_data['old']],
                                 [obj.pk for obj in old])
                self.assertEqual([item[2] for item in field_data['new']],
                                 [obj.pk for obj in new])
                self.assertEqual([item[2] for item in field_data['removed']],
                                 [obj.pk for obj in removed])
                self.assertEqual([item[2] for item in field_data['added']],
                                 [obj.pk for obj in added])
            elif isinstance(old, list):
                self.assertEqual(field_data['old'],
                                 [[value] for value in old])
                self.assertEqual(field_data['new'],
                                 [[value] for value in new])
                self.assertEqual(field_data['removed'],
                                 [[value] for value in removed])
                self.assertEqual(field_data['added'],
                                 [[value] for value in added])
            else:
                self.assertEqual(field_data['old'], [old])
                self.assertEqual(field_data['new'], [new])
                self.assertTrue('removed' not in field_data)
                self.assertTrue('added' not in field_data)

        self.assertTrue('screenshot_captions' in change.fields_changed)
        field_data = change.fields_changed['screenshot_captions']
        screenshot_id = str(screenshot3.pk)
        self.assertTrue(screenshot_id in field_data)
        self.assertTrue('old' in field_data[screenshot_id])
        self.assertTrue('new' in field_data[screenshot_id])
        self.assertEqual(field_data[screenshot_id]['old'][0],
                         old_screenshot_caption)
        self.assertEqual(field_data[screenshot_id]['new'][0],
                         new_screenshot_caption)

        # Now confirm with the API
        rsp = self.apiGet(rsp['review_request']['links']['changes']['href'],
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 1)

        self.assertEqual(rsp['changes'][0]['id'], change.pk)
        rsp = self.apiGet(rsp['changes'][0]['links']['self']['href'],
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['change']['text'], changedesc_text)

        fields_changed = rsp['change']['fields_changed']

        for field, data in test_data.iteritems():
            old, new, removed, added = data

            self.assertTrue(field in fields_changed)
            field_data = fields_changed[field]

            if field == 'diff':
                self.assertTrue('added' in field_data)
                self.assertEqual(field_data['added']['id'], added.pk)
            elif field in model_fields:
                self.assertTrue('old' in field_data)
                self.assertTrue('new' in field_data)
                self.assertTrue('added' in field_data)
                self.assertTrue('removed' in field_data)
                self.assertEqual([item['id'] for item in field_data['old']],
                                 [obj.pk for obj in old])
                self.assertEqual([item['id'] for item in field_data['new']],
                                 [obj.pk for obj in new])
                self.assertEqual([item['id'] for item in field_data['removed']],
                                 [obj.pk for obj in removed])
                self.assertEqual([item['id'] for item in field_data['added']],
                                 [obj.pk for obj in added])
            else:
                self.assertTrue('old' in field_data)
                self.assertTrue('new' in field_data)
                self.assertEqual(field_data['old'], old)
                self.assertEqual(field_data['new'], new)

                if isinstance(old, list):
                    self.assertTrue('added' in field_data)
                    self.assertTrue('removed' in field_data)

                    self.assertEqual(field_data['added'], added)
                    self.assertEqual(field_data['removed'], removed)

        self.assertTrue('screenshot_captions' in fields_changed)
        field_data = fields_changed['screenshot_captions']
        self.assertEqual(len(field_data), 1)
        screenshot_data = field_data[0]
        self.assertTrue('old' in screenshot_data)
        self.assertTrue('new' in screenshot_data)
        self.assertTrue('screenshot' in screenshot_data)
        self.assertEqual(screenshot_data['old'], old_screenshot_caption)
        self.assertEqual(screenshot_data['new'], new_screenshot_caption)
        self.assertEqual(screenshot_data['screenshot']['id'], screenshot3.pk)

    @add_fixtures(['test_site'])
    def test_get_change_not_modified(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API with Not Modified response"""
        review_request = ReviewRequest.objects.public()[0]

        changedesc = ChangeDescription(public=True)
        changedesc.save()
        review_request.changedescs.add(changedesc)

        self._testHttpCaching(self.get_item_url(changedesc),
                              check_last_modified=True)

    def get_item_url(self, changedesc, local_site_name=None):
        return local_site_reverse(
            'change-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': changedesc.review_request.get().display_id,
                'change_id': changedesc.id,
            })


class DiffResourceTests(BaseWebAPITestCase):
    """Testing the DiffResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('diffs')
    item_mimetype = _build_mimetype('diff')

    def test_post_diffs(self):
        """Testing the POST review-requests/<id>/diffs/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scmtools", "testdata", "svn_makefile.diff")
        f = open(diff_filename, "r")
        rsp = self.apiPost(rsp['review_request']['links']['diffs']['href'], {
            'path': f,
            'basedir': '/trunk',
            'base_commit_id': '1234',
        }, expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['basedir'], '/trunk')
        self.assertEqual(rsp['diff']['base_commit_id'], '1234')

        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        self.assertEqual(diffset.basedir, '/trunk')
        self.assertEqual(diffset.base_commit_id, '1234')

    def test_post_diffs_with_missing_data(self):
        """Testing the POST review-requests/<id>/diffs/ API with Invalid Form Data"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        rsp = self.apiPost(rsp['review_request']['links']['diffs']['href'],
                           expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assert_('path' in rsp['fields'])

        # Now test with a valid path and an invalid basedir.
        # This is necessary because basedir is "optional" as defined by
        # the resource, but may be required by the form that processes the
        # diff.
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scmtools", "testdata", "svn_makefile.diff")
        f = open(diff_filename, "r")
        rsp = self.apiPost(rsp['review_request']['links']['diffs']['href'], {
            'path': f,
        }, expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assert_('basedir' in rsp['fields'])

    def test_post_diffs_too_big(self):
        """Testing the POST review-requests/<id>/diffs/ API with diff exceeding max size"""
        self.siteconfig.set('diffviewer_max_diff_size', 2)
        self.siteconfig.save()

        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scmtools", "testdata", "svn_makefile.diff")
        f = open(diff_filename, "r")

        rsp = self.apiPost(rsp['review_request']['links']['diffs']['href'], {
            'path': f,
            'basedir': "/trunk",
        }, expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_TOO_BIG.code)
        self.assertTrue('reason' in rsp)
        self.assertTrue('max_size' in rsp)
        self.assertEqual(rsp['max_size'],
                         self.siteconfig.get('diffviewer_max_diff_size'))

    @add_fixtures(['test_site'])
    def test_post_diffs_with_site(self):
        """Testing the POST review-requests/<id>/diffs/ API with a local site"""
        self._login_user(local_site=True)

        repo = self.repository
        self.repository.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        self.repository.save()

        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)

        self.assertEqual(rsp['stat'], 'ok')

        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'scmtools', 'testdata', 'svn_makefile.diff')
        f = open(diff_filename, 'r')
        rsp = self.apiPost(rsp['review_request']['links']['diffs']['href'], {
            'path': f,
            'basedir': '/trunk',
        }, expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['name'],
                         'svn_makefile.diff')

    @add_fixtures(['test_reviewrequests'])
    def test_get_diffs(self):
        """Testing the GET review-requests/<id>/diffs/ API"""
        review_request = ReviewRequest.objects.get(pk=2)
        rsp = self.apiGet(self.get_list_url(review_request),
                          expected_mimetype=self.list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diffs'][0]['id'], 2)
        self.assertEqual(rsp['diffs'][0]['name'], 'cleaned_data.diff')

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diffs_with_site(self):
        """Testing the GET review-requests/<id>/diffs API with a local site"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        self._login_user(local_site=True)

        rsp = self.apiGet(self.get_list_url(review_request,
                                            self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diffs'][0]['id'],
                         review_request.diffset_history.diffsets.latest().id)
        self.assertEqual(rsp['diffs'][0]['name'],
                         review_request.diffset_history.diffsets.latest().name)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diffs_with_site_no_access(self):
        """Testing the GET review-requests/<id>/diffs API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        self.apiGet(self.get_list_url(review_request, self.local_site_name),
                    expected_status=403)

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API"""
        review_request = ReviewRequest.objects.get(pk=2)
        rsp = self.apiGet(self.get_item_url(review_request, 1),
                          expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['id'], 2)
        self.assertEqual(rsp['diff']['name'], 'cleaned_data.diff')

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diff_with_site(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API with a local site"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        diff = review_request.diffset_history.diffsets.latest()
        self._login_user(local_site=True)

        rsp = self.apiGet(self.get_item_url(review_request, diff.revision,
                                            self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['id'], diff.id)
        self.assertEqual(rsp['diff']['name'], diff.name)

    @add_fixtures(['test_reviewrequests'])
    def test_get_diff_not_modified(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API with Not Modified response"""
        review_request = ReviewRequest.objects.get(pk=2)
        self._testHttpCaching(self.get_item_url(review_request, 1),
                              check_last_modified=True)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_diff_with_site_no_access(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        diff = review_request.diffset_history.diffsets.latest()
        self.apiGet(self.get_item_url(review_request, diff.revision,
                                      self.local_site_name),
                    expected_status=403)

    @classmethod
    def get_list_url(cls, review_request, local_site_name=None):
        return local_site_reverse(
            'diffs-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })

    def get_item_url(self, review_request, diff_revision, local_site_name=None):
        return local_site_reverse(
            'diff-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'diff_revision': diff_revision,
            })


class ScreenshotDraftResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotDraftResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    item_mimetype = _build_mimetype('draft-screenshot')
    list_mimetype = _build_mimetype('draft-screenshots')

    def test_post_screenshots(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        screenshots_url = rsp['review_request']['links']['screenshots']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(screenshots_url, {
            'path': f,
        }, expected_mimetype=ScreenshotResourceTests.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_reviewrequests'])
    def test_post_screenshots_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True,
            local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(self.get_list_url(review_request), {
            'caption': 'Trophy',
            'path': f,
        }, expected_status=403)
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

        rsp = self.apiPost(self.get_list_url(review_request,
                                             self.local_site_name),
                           post_data,
                           expected_mimetype=self.item_mimetype)
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
        rsp = self.apiPost(self.get_list_url(review_request,
                                             self.local_site_name),
                           { 'path': f, },
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
        rsp = self.apiPost(self.get_list_url(review_request), {
            'caption': 'Trophy',
            'path': f,
        }, expected_mimetype=self.item_mimetype)
        f.close()
        review_request.publish(self.user)

        screenshot = Screenshot.objects.get(pk=rsp['draft_screenshot']['id'])

        # Now modify the caption.
        rsp = self.apiPut(self.get_item_url(review_request, screenshot.id), {
            'caption': draft_caption,
        }, expected_mimetype=self.item_mimetype)

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

        rsp = self.apiPut(self.get_item_url(review_request, screenshot_id,
                                            self.local_site_name),
                          { 'caption': draft_caption, },
                          expected_mimetype=self.item_mimetype)
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

        rsp = self.apiPut(self.get_item_url(review_request, screenshot_id,
                                            self.local_site_name),
                          { 'caption': 'test', },
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def get_list_url(self, review_request, local_site_name=None):
        return local_site_reverse(
            'draft-screenshots-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })

    def get_item_url(self, review_request, screenshot_id, local_site_name=None):
        return local_site_reverse(
            'draft-screenshot-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'screenshot_id': screenshot_id,
            })


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
        rsp = self.apiPost(screenshots_url, {
            'path': f,
        }, expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_reviewrequests'])
    def test_post_screenshots_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/screenshots/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True,
            local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(self.get_list_url(review_request), {
            'caption': 'Trophy',
            'path': f,
        }, expected_status=403)
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
        rsp = self.apiPost(screenshots_url, { 'path': f, },
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
        rsp = self.apiPost(screenshots_url,
                           { 'path': f, },
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


class FileDiffCommentResourceTests(BaseWebAPITestCase):
    """Testing the FileDiffCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests',
                'test_site']

    list_mimetype = _build_mimetype('file-diff-comments')
    item_mimetype = _build_mimetype('file-diff-comment')

    def test_get_comments(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API"""
        diff_comment_text = 'Sample comment.'

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        rsp = self.apiGet(self.get_list_url(filediff),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)

    def test_get_comments_as_anonymous(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API as an anonymous user"""
        diff_comment_text = 'Sample comment.'

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)
        review = Review.objects.get(pk=review_id)
        review.publish()

        self.client.logout()

        rsp = self.apiGet(self.get_list_url(filediff),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)

    def test_get_comments_with_site(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API with a local site"""
        diff_comment_text = 'Sample comment.'

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        rsp = self.apiGet(self.get_list_url(filediff, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)

    def test_get_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API with a local site and Permission Denied error"""
        diff_comment_text = 'Sample comment.'

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        self._login_user()

        rsp = self.apiGet(self.get_list_url(filediff, self.local_site_name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_comments_with_line(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/?line= API"""
        diff_comment_text = 'Sample comment.'
        diff_comment_line = 10

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text,
                                 first_line=diff_comment_line)

        self._postNewDiffComment(review_request, review_id, diff_comment_text,
                                 first_line=diff_comment_line + 1)

        rsp = self.apiGet(self.get_list_url(filediff), {
            'line': diff_comment_line,
        }, expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff,
                                          first_line=diff_comment_line)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)
            self.assertEqual(rsp['diff_comments'][i]['first_line'],
                             comments[i].first_line)

    def get_list_url(self, filediff, local_site_name=None):
        diffset = filediff.diffset
        review_request = diffset.history.review_request.get()

        return local_site_reverse(
            'diff-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'diff_revision': filediff.diffset.revision,
                'filediff_id': filediff.pk,
            })


class ScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('screenshot-comments')
    item_mimetype = _build_mimetype('screenshot-comment')

    def test_get_screenshot_comments(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API"""
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        self.assertTrue('links' in rsp['screenshot'])
        self.assertTrue('screenshot_comments' in rsp['screenshot']['links'])
        comments_url = rsp['screenshot']['links']['screenshot_comments']['href']

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                      comment_text, x, y, w, h)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
        rsp_comments = rsp['screenshot_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)
            self.assertEqual(rsp_comments[i]['x'], comments[i].x)
            self.assertEqual(rsp_comments[i]['y'], comments[i].y)
            self.assertEqual(rsp_comments[i]['w'], comments[i].w)
            self.assertEqual(rsp_comments[i]['h'], comments[i].h)

    @add_fixtures(['test_site'])
    def test_get_screenshot_comments_with_site(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API with a local site"""
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        self.assertTrue('links' in rsp['screenshot'])
        self.assertTrue('screenshot_comments' in rsp['screenshot']['links'])
        comments_url = rsp['screenshot']['links']['screenshot_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
        rsp_comments = rsp['screenshot_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)
            self.assertEqual(rsp_comments[i]['x'], comments[i].x)
            self.assertEqual(rsp_comments[i]['y'], comments[i].y)
            self.assertEqual(rsp_comments[i]['w'], comments[i].w)
            self.assertEqual(rsp_comments[i]['h'], comments[i].h)

    @add_fixtures(['test_site'])
    def test_get_screenshot_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/screenshots/<id>/comments/ API with a local site and Permission Denied error"""
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])
        self.assertTrue('links' in rsp['screenshot'])
        self.assertTrue('screenshot_comments' in rsp['screenshot']['links'])
        comments_url = rsp['screenshot']['links']['screenshot_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                       comment_text, x, y, w, h)

        self._login_user()

        rsp = self.apiGet(comments_url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ReviewScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewScreenshotCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('review-screenshot-comments')
    item_mimetype = _build_mimetype('review-screenshot-comment')

    def test_post_screenshot_comments(self):
        """Testing the POST review-requests/<id>/reviews/<id>/screenshot-comments/ API"""
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

    @add_fixtures(['test_site'])
    def test_post_screenshot_comments_with_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/screenshot-comments/ API with a local site"""
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

    @add_fixtures(['test_site'])
    def test_post_screenshot_comments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/reviews/<id>/screenshot-comments/ API with a local site and Permission Denied error"""
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._login_user()

        rsp = self.apiPost(self.get_list_url(review, self.local_site_name),
                           { 'screenshot_id': screenshot.id, },
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_screenshot_comment(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API"""
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])
        screenshot_comments_url = \
            rsp['review']['links']['screenshot_comments']['href']

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(
            screenshot_comments_url,
            expected_mimetype=ScreenshotCommentResourceTests.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_site'])
    def test_delete_screenshot_comment_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id> API with a local site"""
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        screenshot_comments_url = \
            rsp['review']['links']['screenshot_comments']['href']

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.apiDelete(rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(
            screenshot_comments_url,
            expected_mimetype=ScreenshotCommentResourceTests.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    @add_fixtures(['test_site'])
    def test_delete_screenshot_comment_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id> API with a local site and Permission Denied error"""
        comment_text = 'This is a test comment.'
        x, y, w, h = (2, 2, 10, 10)

        self._login_user(local_site=True)

        # Post the review request
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self._login_user()

        rsp = self.apiDelete(rsp['screenshot_comment']['links']['self']['href'],
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_screenshot_comment_with_does_not_exist_error(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API with Does Not Exist error"""
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self.apiDelete(self.get_item_url(review, 123), expected_status=404)

    def test_post_screenshot_comment_with_issue(self):
        """Testing the POST review-requests/<id>/reviews/<id>/screenshot-comments/ API with an issue"""
        comment_text = "Test screenshot comment with an opened issue"
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        rsp = self._postNewScreenshotComment(review_request, review_id,
                                             screenshot, comment_text, x,
                                             y, w, h, issue_opened=True)

        review = Review.objects.get(pk=review_id)

        rsp = self.apiGet(
            self.get_list_url(review),
            expected_mimetype=ScreenshotCommentResourceTests.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'], comment_text)
        self.assertTrue(rsp['screenshot_comments'][0]['issue_opened'])

    def test_update_screenshot_comment_with_issue(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id> API with an issue"""
        comment_text = "Test screenshot comment with an opened issue"
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        review_id = rsp['review']['id']
        Review.objects.get(pk=review_id)

        rsp = self._postNewScreenshotComment(review_request, review_id,
                                             screenshot, comment_text,
                                             x, y, w, h, issue_opened=True)

        rsp = self.apiPut(rsp['screenshot_comment']['links']['self']['href'], {
            'issue_opened': False,
        }, expected_mimetype=ScreenshotCommentResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertFalse(rsp['screenshot_comment']['issue_opened'])

    def test_update_screenshot_comment_issue_status(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id> API with an issue"""
        comment_text = "Test screenshot comment with an opened issue"
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        rsp = self._postNewScreenshotComment(review_request, review_id,
                                             screenshot, comment_text,
                                             x, y, w, h, issue_opened=True)

        # First, let's ensure that the user that has created the comment
        # cannot alter the issue_status while the review is unpublished.
        rsp = self.apiPut(rsp['screenshot_comment']['links']['self']['href'], {
            'issue_status': 'resolved',
        }, expected_mimetype=ScreenshotCommentResourceTests.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')

        # Next, let's publish the review, and try altering the issue_status.
        # This should be allowed, since the review request was made by the
        # current user.
        review.public = True
        review.save()

        rsp = self.apiPut(rsp['screenshot_comment']['links']['self']['href'], {
            'issue_status': 'resolved',
        }, expected_mimetype=ScreenshotCommentResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'resolved')

        # Finally, let's make sure that this user cannot alter the issue_status
        # on a screenshot-comment for a review request that they didn't make.
        review_request.submitter = User.objects.get(username='doc')
        review_request.save()

        rsp = self.apiPut(rsp['screenshot_comment']['links']['self']['href'], {
            'issue_status': 'dropped',
        }, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_update_deleted_screenshot_comment_issue_status(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/screenshot-comments/<id>
        API with an issue and a deleted screenshot
        """
        comment_text = "Test screenshot comment with an opened issue"
        x, y, w, h = (2, 2, 10, 10)

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the screenshot.
        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        rsp = self._postNewScreenshotComment(review_request, review_id,
                                             screenshot, comment_text,
                                             x, y, w, h, issue_opened=True)

        # First, let's ensure that the user that has created the comment
        # cannot alter the issue_status while the review is unpublished.
        rsp = self.apiPut(rsp['screenshot_comment']['links']['self']['href'], {
            'issue_status': 'resolved',
        }, expected_mimetype=ScreenshotCommentResourceTests.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        # The issue_status should still be "open"
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')

        # Next, let's publish the review, and try altering the issue_status.
        # This should be allowed, since the review request was made by the
        # current user.
        review.public = True
        review.save()

        rsp = self.apiPut(rsp['screenshot_comment']['links']['self']['href'], {
            'issue_status': 'resolved',
        }, expected_mimetype=ScreenshotCommentResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'resolved')

        # Delete the screenshot.
        self._delete_screenshot(review_request, screenshot)
        review_request.publish(review_request.submitter)

        # Try altering the issue_status. This should be allowed.
        rsp = self.apiPut(rsp['screenshot_comment']['links']['self']['href'], {
            'issue_status': 'open',
        }, expected_mimetype=ScreenshotCommentResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['screenshot_comment']['issue_status'], 'open')

    @classmethod
    def get_list_url(cls, review, local_site_name=None):
        return local_site_reverse(
            'screenshot-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
            })

    def get_item_url(cls, review, comment_id, local_site_name=None):
        return local_site_reverse(
            'screenshot-comment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
                'comment_id': comment_id,
            })


class FileAttachmentResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('file-attachments')
    item_mimetype = _build_mimetype('file-attachment')

    def test_get_file_attachment_not_modified(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/ API with Not Modified response"""
        self.test_post_file_attachments()

        file_attachment = FileAttachment.objects.all()[0]
        self._testHttpCaching(self.get_item_url(file_attachment),
                              check_etags=True)

    def test_post_file_attachments(self):
        """Testing the POST review-requests/<id>/file-attachments/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        file_attachments_url = \
            rsp['review_request']['links']['file_attachments']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(file_attachments_url, {
            'path': f,
        }, expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        review_request.publish(review_request.submitter)

    @add_fixtures(['test_reviewrequests'])
    def test_post_file_attachments_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True,
            local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(self.get_list_url(review_request), {
            'caption': 'Trophy',
            'path': f,
        }, expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _test_review_request_with_site(self):
        self._login_user(local_site=True)

        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')

        return rsp['review_request']['links']['file_attachments']['href']

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with a local site"""
        file_attachments_url = self._test_review_request_with_site()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(file_attachments_url, { 'path': f, },
                           expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with a local site and Permission Denied error"""
        file_attachments_url = self._test_review_request_with_site()
        self._login_user()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(file_attachments_url,
                           { 'path': f, },
                           expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @classmethod
    def get_list_url(cls, review_request, local_site_name=None):
        return local_site_reverse(
            'file-attachments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })

    def get_item_url(self, file_attachment, local_site_name=None):
        return local_site_reverse(
            'file-attachment-resource',
            local_site_name=local_site_name,
            kwargs={
                'file_attachment_id': file_attachment.id,
                'review_request_id':
                    file_attachment.review_request.get().display_id,
            })


class FileAttachmentDraftResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentDraftResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('draft-file-attachments')
    item_mimetype = _build_mimetype('draft-file-attachment')

    def test_post_file_attachments(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        file_attachments_url = \
            rsp['review_request']['links']['file_attachments']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(file_attachments_url, {
            'path': f,
        }, expected_mimetype=FileAttachmentResourceTests.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_reviewrequests'])
    def test_post_file_attachments_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True,
            local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(self.get_list_url(review_request), {
            'caption': 'Trophy',
            'path': f,
        }, expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with a local site"""
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

        rsp = self.apiPost(self.get_list_url(review_request,
                                             self.local_site_name),
                           post_data,
                           expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft_file_attachment']['caption'], 'Trophy')

        draft = review_request.get_draft(User.objects.get(username='doc'))
        self.assertNotEqual(draft, None)

        return review_request, rsp['draft_file_attachment']['id']

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_file_attachments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(self.get_list_url(review_request,
                                             self.local_site_name),
                           { 'path': f, },
                           expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_file_attachment(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/ API"""
        draft_caption = 'The new caption'

        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(self.get_list_url(review_request), {
            'caption': 'Trophy',
            'path': f,
        }, expected_mimetype=self.item_mimetype)
        f.close()
        review_request.publish(self.user)

        file_attachment = FileAttachment.objects.get(pk=rsp['draft_file_attachment']['id'])

        # Now modify the caption.
        rsp = self.apiPut(self.get_item_url(review_request,
                                            file_attachment.id), {
            'caption': draft_caption,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(self.user)
        self.assertNotEqual(draft, None)

        file_attachment = FileAttachment.objects.get(pk=file_attachment.id)
        self.assertEqual(file_attachment.draft_caption, draft_caption)

    @add_fixtures(['test_site'])
    def test_put_file_attachment_with_site(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/ API with a local site"""
        draft_caption = 'The new caption'
        user = User.objects.get(username='doc')

        review_request, file_attachment_id = \
            self.test_post_file_attachments_with_site()
        review_request.publish(user)

        rsp = self.apiPut(self.get_item_url(review_request, file_attachment_id,
                                            self.local_site_name),
                          { 'caption': draft_caption, },
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(user)
        self.assertNotEqual(draft, None)

        file_attachment = FileAttachment.objects.get(pk=file_attachment_id)
        self.assertEqual(file_attachment.draft_caption, draft_caption)

    @add_fixtures(['test_site'])
    def test_put_file_attachment_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/ API with a local site and Permission Denied error"""
        review_request, file_attachment_id = \
            self.test_post_file_attachments_with_site()
        review_request.publish(User.objects.get(username='doc'))

        self._login_user()

        rsp = self.apiPut(self.get_item_url(review_request, file_attachment_id,
                                            self.local_site_name),
                          { 'caption': 'test', },
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def get_list_url(self, review_request, local_site_name=None):
        return local_site_reverse(
            'draft-file-attachments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })

    def get_item_url(self, review_request, file_attachment_id,
                     local_site_name=None):
        return local_site_reverse(
            'draft-file-attachment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'file_attachment_id': file_attachment_id,
            })


class FileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('file-attachment-comments')
    item_mimetype = _build_mimetype('file-attachment-comment')

    def test_get_file_attachment_comments(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/comments/ API"""
        comment_text = "This is a test comment."

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])
        comments_url = \
            rsp['file_attachment']['links']['file_attachment_comments']['href']

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewFileAttachmentComment(review_request, review.id,
                                           file_attachment, comment_text)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = FileAttachmentComment.objects.filter(
            file_attachment=file_attachment)
        rsp_comments = rsp['file_attachment_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)

    @add_fixtures(['test_site'])
    def test_get_file_attachment_comments_with_site(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/comments/ API with a local site"""
        comment_text = 'This is a test comment.'

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])
        comments_url = \
            rsp['file_attachment']['links']['file_attachment_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewFileAttachmentComment(review_request, review.id,
                                           file_attachment, comment_text)

        rsp = self.apiGet(comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comments = FileAttachmentComment.objects.filter(
            file_attachment=file_attachment)
        rsp_comments = rsp['file_attachment_comments']
        self.assertEqual(len(rsp_comments), comments.count())

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)

    @add_fixtures(['test_site'])
    def test_get_file_attachment_comments_with_site_no_access(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/comments/ API with a local site and Permission Denied error"""
        comment_text = 'This is a test comment.'

        self._login_user(local_site=True)

        # Post the review request.
        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])
        comments_url = \
            rsp['file_attachment']['links']['file_attachment_comments']['href']

        # Make these public.
        review_request.publish(User.objects.get(username='doc'))

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewFileAttachmentComment(review_request, review.id,
                                           file_attachment, comment_text)

        self._login_user()

        rsp = self.apiGet(comments_url, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_file_attachment_comments_with_extra_fields(self):
        """Testing the POST review-requests/<id>/file-attachments/<id>/comments/ API with extra fields"""
        comment_text = "This is a test comment."
        extra_fields = {
            'extra_data.foo': '123',
            'extra_data.bar': '456',
            'extra_data.baz': '',
            'ignored': 'foo',
        }

        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = FileAttachment.objects.get(
            pk=rsp['file_attachment']['id'])
        self.assertTrue('links' in rsp['file_attachment'])
        self.assertTrue('file_attachment_comments' in
                        rsp['file_attachment']['links'])

        # Make these public.
        review_request.publish(self.user)

        # Post the review.
        rsp = self._postNewReview(review_request)
        review = Review.objects.get(pk=rsp['review']['id'])

        rsp = self._postNewFileAttachmentComment(review_request, review.id,
                                                 file_attachment, comment_text,
                                                 extra_fields=extra_fields)

        comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        self.assertTrue('foo' in comment.extra_data)
        self.assertTrue('bar' in comment.extra_data)
        self.assertFalse('baz' in comment.extra_data)
        self.assertFalse('ignored' in comment.extra_data)
        self.assertEqual(comment.extra_data['foo'],
                         extra_fields['extra_data.foo'])
        self.assertEqual(comment.extra_data['bar'],
                         extra_fields['extra_data.bar'])

        return rsp

    def test_put_file_attachment_comments_with_extra_fields(self):
        """Testing the PUT review-requests/<id>/file-attachments/<id>/comments/<id>/ API with extra fields"""
        extra_fields = {
            'extra_data.foo': 'abc',
            'extra_data.bar': '',
            'ignored': 'foo',
        }

        rsp = self.test_post_file_attachment_comments_with_extra_fields()

        rsp = self.apiPut(
            rsp['file_attachment_comment']['links']['self']['href'],
            extra_fields,
            expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        self.assertTrue('foo' in comment.extra_data)
        self.assertFalse('bar' in comment.extra_data)
        self.assertFalse('ignored' in comment.extra_data)
        self.assertEqual(len(comment.extra_data.keys()), 1)
        self.assertEqual(comment.extra_data['foo'],
                         extra_fields['extra_data.foo'])


class DraftReviewFileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewFileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('file-attachment-comments')
    item_mimetype = _build_mimetype('file-attachment-comment')

    def test_get_review_file_attachment_comments(self):
        """Testing the GET review-requests/<id>/reviews/draft/file-attachment-comments/ API"""
        file_attachment_comment_text = "Test file attachment comment"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the file_attachment.
        rsp = self._postNewFileAttachment(review_request)
        file_attachment = \
            FileAttachment.objects.get(pk=rsp['file_attachment']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost(ReviewResourceTests.get_list_url(review_request),
                           expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewFileAttachmentComment(review_request, review_id,
                                           file_attachment,
                                           file_attachment_comment_text)

        rsp = self.apiGet(self.get_list_url(review),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 1)
        self.assertEqual(rsp['file_attachment_comments'][0]['text'],
                         file_attachment_comment_text)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_get_review_file_attachment_comments_with_site(self):
        """Testing the GET review-requests/<id>/reviews/draft/file-attachment-comments/ APIs with a local site"""
        file_attachment_comment_text = "Test file_attachment comment"

        self._login_user(local_site=True)

        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        rsp = self._postNewFileAttachment(review_request)
        file_attachment = \
            FileAttachment.objects.get(pk=rsp['file_attachment']['id'])
        review_request.publish(User.objects.get(username='doc'))

        rsp = self.apiPost(
            ReviewResourceTests.get_list_url(review_request,
                                             self.local_site_name),
            expected_mimetype=ReviewResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']
        review = Review.objects.get(pk=review_id)

        self._postNewFileAttachmentComment(review_request, review_id,
                                           file_attachment,
                                           file_attachment_comment_text)

        rsp = self.apiGet(self.get_list_url(review, self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 1)
        self.assertEqual(rsp['file_attachment_comments'][0]['text'],
                         file_attachment_comment_text)

    @classmethod
    def get_list_url(self, review, local_site_name=None):
        return local_site_reverse(
            'file-attachment-comments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
            })

    def get_item_url(self, review, comment_id, local_site_name=None):
        return local_site_reverse(
            'file-attachment-comment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review.review_request.display_id,
                'review_id': review.pk,
                'comment_id': comment_id,
            })


class ReviewReplyFileAttachmentCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyFileAttachmentCommentResource APIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    list_mimetype = _build_mimetype('review-reply-file-attachment-comments')
    item_mimetype = _build_mimetype('review-reply-file-attachment-comment')

    def test_post_reply_with_file_attachment_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API"""
        comment_text = "My Comment Text"

        comment = FileAttachmentComment.objects.all()[0]
        review = comment.review.get()

        # Create the reply
        rsp = self.apiPost(
            ReviewReplyResourceTests.get_list_url(review),
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        comments_url = rsp['reply']['links']['file_attachment_comments']['href']

        rsp = self.apiPost(comments_url, {
            'reply_to_id': comment.id,
            'text': comment_text,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, comments_url

    @add_fixtures(['test_site'])
    def test_post_reply_with_file_attachment_comment_and_local_site(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API with a local site"""
        comment_text = "My Comment Text"

        comment = FileAttachmentComment.objects.all()[0]
        review = comment.review.get()
        review_request = review.review_request

        review.user = User.objects.get(username='doc')
        review.save()

        review_request.local_site = \
            LocalSite.objects.get(name=self.local_site_name)
        review_request.local_id = 42
        review_request.save()

        self._login_user(local_site=True)

        # Create the reply
        rsp = self.apiPost(
            ReviewReplyResourceTests.get_list_url(review,
                                                  self.local_site_name),
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        comments_url = rsp['reply']['links']['file_attachment_comments']['href']

        rsp = self.apiPost(comments_url, {
            'reply_to_id': comment.id,
            'text': comment_text,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, comments_url

    def test_post_reply_with_inactive_file_attachment_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API with inactive file attachment"""
        comment_text = "My Comment Text"

        comment = FileAttachmentComment.objects.all()[0]
        review = comment.review.get()

        # Create the reply
        rsp = self.apiPost(
            ReviewReplyResourceTests.get_list_url(review),
            expected_mimetype=ReviewReplyResourceTests.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])
        comments_url = \
            rsp['reply']['links']['file_attachment_comments']['href']

        # Make the file attachment inactive.
        file_attachment = comment.file_attachment
        review_request = file_attachment.review_request.get()
        review_request.inactive_file_attachments.add(file_attachment)
        review_request.file_attachments.remove(file_attachment)

        # Now make the reply.
        rsp = self.apiPost(comments_url, {
            'reply_to_id': comment.id,
            'text': comment_text,
        }, expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

        return rsp, comment, comments_url

    def test_post_reply_with_file_attachment_comment_http_303(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API and 303 See Other"""
        comment_text = "My New Comment Text"

        rsp, comment, comments_url = \
            self.test_post_reply_with_file_attachment_comment()

        # Now do it again.
        rsp = self.apiPost(comments_url, {
                'reply_to_id': comment.pk,
                'text': comment_text
            },
            expected_status=303,
            expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def test_put_reply_with_file_attachment_comment(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/ API"""
        new_comment_text = 'My new comment text'

        # First, create a comment that we can update.
        rsp = self.test_post_reply_with_file_attachment_comment()[0]

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])

        rsp = self.apiPut(
            rsp['file_attachment_comment']['links']['self']['href'], {
                'text': new_comment_text,
            },
            expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = FileAttachmentComment.objects.get(
            pk=rsp['file_attachment_comment']['id'])
        self.assertEqual(reply_comment.text, new_comment_text)

    def test_delete_file_attachment_comment(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment()

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'])

        rsp = self.apiGet(file_attachment_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 0)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_file_attachment_comment_with_local_site(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API with a local site"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment_and_local_site()

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'])

        rsp = self.apiGet(file_attachment_comments_url,
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('file_attachment_comments' in rsp)
        self.assertEqual(len(rsp['file_attachment_comments']), 0)

    def test_delete_file_attachment_comment_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API and Permission Denied"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment()

        self.client.login(username="doc", password="doc")

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'],
                       expected_status=403)

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_delete_file_attachment_comment_with_local_site_no_access(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/file-attachment-comments/<id>/ API with a local site and Permission Denied"""
        rsp, comment, file_attachment_comments_url = \
            self.test_post_reply_with_file_attachment_comment_and_local_site()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        local_site.users.add(User.objects.get(username='grumpy'))

        self.client.login(username="grumpy", password="grumpy")

        self.apiDelete(rsp['file_attachment_comment']['links']['self']['href'],
                       expected_status=403)


class DefaultReviewerResourceTests(BaseWebAPITestCase):
    """Testing the DefaultReviewerResource APIs."""
    list_mimetype = _build_mimetype('default-reviewers')
    item_mimetype = _build_mimetype('default-reviewer')

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_post_default_reviewer(self, local_site=None):
        """Testing the POST default-reviewers/ API"""
        self._login_user(admin=True)

        name = 'default1'
        file_regex = '.*'

        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')
        group1 = Group.objects.create(name='group1', local_site=local_site)
        group2 = Group.objects.create(name='group2', local_site=local_site)
        repo1 = Repository.objects.get(name='Review Board SVN')
        repo2 = Repository.objects.get(name='Review Board Git')

        # For the tests, make sure these are what we expect.
        if local_site:
            local_site.users.add(user1)
            local_site.users.add(user2)

        repo1.local_site = local_site
        repo2.local_site = local_site
        repo1.save()
        repo2.save()

        rsp = self.apiPost(self.get_list_url(local_site), {
            'name': name,
            'file_regex': file_regex,
            'users': ','.join([user1.username, user2.username]),
            'groups': ','.join([group1.name, group2.name]),
            'repositories': ','.join([str(repo1.pk), str(repo2.pk)]),
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(
            pk=rsp['default_reviewer']['id'])
        self.assertEqual(default_reviewer.local_site, local_site)
        self.assertEqual(default_reviewer.name, name)
        self.assertEqual(default_reviewer.file_regex, file_regex)

        people = list(default_reviewer.people.all())
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0], user1)
        self.assertEqual(people[1], user2)

        groups = list(default_reviewer.groups.all())
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], group1)
        self.assertEqual(groups[1], group2)

        repos = list(default_reviewer.repository.all())
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0], repo1)
        self.assertEqual(repos[1], repo2)

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_defaults(self):
        """Testing the POST default-reviewers/ API with field defaults"""
        self._login_user(admin=True)

        name = 'default1'
        file_regex = '.*'

        rsp = self.apiPost(self.get_list_url(), {
            'name': name,
            'file_regex': file_regex,
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(
            pk=rsp['default_reviewer']['id'])
        self.assertEqual(default_reviewer.local_site, None)
        self.assertEqual(default_reviewer.name, name)
        self.assertEqual(default_reviewer.file_regex, file_regex)

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_permission_denied(self):
        """Testing the POST default-reviewers/ API with Permission Denied error"""
        self._login_user()

        self.apiPost(self.get_list_url(), {
            'name': 'default1',
            'file_regex': '.*',
        }, expected_status=403)

    @add_fixtures(['test_users', 'test_site'])
    def test_post_default_reviewer_with_permission_denied(self):
        """Testing the POST default-reviewers/ API with a local site and Permission Denied error"""
        self._login_user()

        self.apiPost(self.get_list_url(self.local_site_name), {
            'name': 'default1',
            'file_regex': '.*',
        }, expected_status=403)

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_invalid_username(self):
        """Testing the POST default-reviewers/ API with invalid username"""
        self._login_user(admin=True)

        rsp = self.apiPost(self.get_list_url(), {
            'name': 'default1',
            'file_regex': '.*',
            'users': 'foo'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_post_default_reviewer_with_user_invalid_site(self):
        """Testing the POST default-reviewers/ API with user and invalid site"""
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)

        rsp = self.apiPost(self.get_list_url(local_site), {
            'name': 'default1',
            'file_regex': '.*',
            'users': 'grumpy'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_invalid_group(self):
        """Testing the POST default-reviewers/ API with invalid group"""
        self._login_user(admin=True)

        rsp = self.apiPost(self.get_list_url(), {
            'name': 'default1',
            'file_regex': '.*',
            'groups': 'foo'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_post_default_reviewer_with_group_invalid_site(self):
        """Testing the POST default-reviewers/ API with group and invalid site"""
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        Group.objects.create(name='group1', local_site=local_site)

        rsp = self.apiPost(self.get_list_url(), {
            'name': 'default1',
            'file_regex': '.*',
            'groups': 'group1'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_invalid_repository(self):
        """Testing the POST default-reviewers/ API with invalid repository"""
        self._login_user(admin=True)

        rsp = self.apiPost(self.get_list_url(), {
            'name': 'default1',
            'file_regex': '.*',
            'repositories': '12345'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_post_default_reviewer_with_repository_invalid_site(self):
        """Testing the POST default-reviewers/ API with repository and invalid site"""
        repository = Repository.objects.filter(local_site__pk__gt=0)[0]

        self._login_user(admin=True)

        rsp = self.apiPost(self.get_list_url(), {
            'name': 'default1',
            'file_regex': '.*',
            'repositories': str(repository.pk),
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_post_default_reviewer_with_site(self, local_site=None):
        """Testing the POST default-reviewers/ API with a local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        self.test_post_default_reviewer(local_site)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_put_default_reviewer(self, local_site=None):
        """Testing the PUT default-reviewers/<id>/ API"""
        name = 'my-default-reviewer'
        file_regex = '/foo/'

        old_user = User.objects.get(username='admin')
        old_group = Group.objects.create(name='group3', local_site=local_site)
        old_repo = Repository.objects.get(name='Test HG')

        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')
        group1 = Group.objects.create(name='group1', local_site=local_site)
        group2 = Group.objects.create(name='group2', local_site=local_site)
        repo1 = Repository.objects.get(name='Review Board SVN')
        repo2 = Repository.objects.get(name='Review Board Git')

        # For the tests, make sure these are what we expect.
        if local_site:
            local_site.users.add(user1)
            local_site.users.add(user2)
            local_site.users.add(old_user)

        old_repo.local_site = local_site
        old_repo.save()

        repo1.local_site = local_site
        repo1.save()

        repo2.local_site = local_site
        repo2.save()

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)
        default_reviewer.groups.add(old_group)
        default_reviewer.repository.add(old_repo)
        default_reviewer.people.add(old_user)

        self._login_user(admin=True)
        rsp = self.apiPut(self.get_item_url(default_reviewer.pk, local_site), {
            'name': name,
            'file_regex': file_regex,
            'users': ','.join([user1.username, user2.username]),
            'groups': ','.join([group1.name, group2.name]),
            'repositories': ','.join([str(repo1.pk), str(repo2.pk)]),
        }, expected_mimetype=self.item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(default_reviewer.local_site, local_site)
        self.assertEqual(default_reviewer.name, name)
        self.assertEqual(default_reviewer.file_regex, file_regex)

        people = list(default_reviewer.people.all())
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0], user1)
        self.assertEqual(people[1], user2)

        groups = list(default_reviewer.groups.all())
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], group1)
        self.assertEqual(groups[1], group2)

        repos = list(default_reviewer.repository.all())
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0], repo1)
        self.assertEqual(repos[1], repo2)

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_put_default_reviewer_with_site(self):
        """Testing the PUT default-reviewers/<id>/ API with a local site"""
        self.test_put_default_reviewer(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_permission_denied(self):
        """Testing the POST default-reviewers/ API with Permission Denied error"""
        self._login_user()

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self.apiPut(self.get_item_url(default_reviewer.pk), {
            'name': 'default2',
        }, expected_status=403)

    @add_fixtures(['test_users', 'test_site'])
    def test_put_default_reviewer_with_permission_denied(self):
        """Testing the PUT default-reviewers/<id>/ API with a local site and Permission Denied error"""
        self._login_user()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiPut(self.get_item_url(default_reviewer.pk,
                                      self.local_site_name), {
            'name': 'default2',
        }, expected_status=403)

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_invalid_username(self):
        """Testing the PUT default-reviewers/<id>/ API with invalid username"""
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.apiPut(self.get_item_url(default_reviewer.pk), {
            'users': 'foo'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_put_default_reviewer_with_user_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API with user and invalid site"""
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        rsp = self.apiPut(self.get_item_url(default_reviewer.pk,
                                            self.local_site_name), {
            'users': 'grumpy'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_invalid_group(self):
        """Testing the PUT default-reviewers/<id>/ API with invalid group"""
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.apiPut(self.get_item_url(default_reviewer.pk), {
            'groups': 'foo'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_put_default_reviewer_with_group_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API with group and invalid site"""
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        Group.objects.create(name='group1', local_site=local_site)

        rsp = self.apiPut(self.get_item_url(default_reviewer.pk), {
            'groups': 'group1'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_invalid_repository(self):
        """Testing the PUT default-reviewers/<id>/ API with invalid repository"""
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.apiPut(self.get_item_url(default_reviewer.pk), {
            'repositories': '12345'
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_put_default_reviewer_with_repository_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API with repository and invalid site"""
        repository = Repository.objects.filter(local_site__pk__gt=0)[0]

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self._login_user(admin=True)

        rsp = self.apiPut(self.get_item_url(default_reviewer.pk), {
            'repositories': str(repository.pk),
        }, expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_get_default_reviewers(self):
        """Testing the GET default-reviewers/ API"""
        user = User.objects.get(username='doc')
        group = Group.objects.create(name='group1')
        repository = Repository.objects.get(pk=1)

        DefaultReviewer.objects.create(name='default1', file_regex='.*')

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.people.add(user)
        default_reviewer.groups.add(group)
        default_reviewer.repository.add(repository)

        rsp = self.apiGet(self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[0]['file_regex'], '.*')
        self.assertEqual(default_reviewers[1]['name'], 'default2')
        self.assertEqual(default_reviewers[1]['file_regex'], '/foo')

        users = default_reviewers[1]['users']
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['title'], user.username)

        groups = default_reviewers[1]['groups']
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['title'], group.name)

        repos = default_reviewers[1]['repositories']
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]['title'], repository.name)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewers_with_site(self):
        """Testing the GET default-reviewers/ API with a local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        DefaultReviewer.objects.create(name='default1', file_regex='.*',
                                       local_site=local_site)
        DefaultReviewer.objects.create(name='default2', file_regex='/foo')

        # Test for non-LocalSite ones.
        rsp = self.apiGet(self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default2')
        self.assertEqual(default_reviewers[0]['file_regex'], '/foo')

        # Now test for the ones in the LocalSite.
        self._login_user(local_site=True)
        rsp = self.apiGet(self.get_list_url(self.local_site_name),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[0]['file_regex'], '.*')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewers_with_site_no_access(self):
        """Testing the GET default-reviewers/ API with a local site and Permission Denied error"""
        rsp = self.apiGet(self.get_list_url(self.local_site_name),
                          expected_status=403)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_get_default_reviewers_with_repositories(self):
        """Testing the GET default-reviewers/?repositories= API"""
        repositories = list(Repository.objects.all())
        repository1 = repositories[0]
        repository2 = repositories[1]

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.repository.add(repository1)
        default_reviewer.repository.add(repository2)

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.repository.add(repository2)

        # Test singling out one repository.
        rsp = self.apiGet('%s?repositories=%s'
                          % (self.get_list_url(), repository2.pk),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.apiGet('%s?repositories=%s,%s'
                          % (self.get_list_url(), repository1.pk,
                             repository2.pk),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    @add_fixtures(['test_users'])
    def test_get_default_reviewers_with_users(self):
        """Testing the GET default-reviewers/?users= API"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.people.add(user1)
        default_reviewer.people.add(user2)

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.people.add(user2)

        # Test singling out one user.
        rsp = self.apiGet('%s?users=dopey' % self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.apiGet('%s?users=doc,dopey' % self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    def test_get_default_reviewers_with_groups(self):
        """Testing the GET default-reviewers/?groups= API"""
        group1 = Group.objects.create(name='group1')
        group2 = Group.objects.create(name='group2')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.groups.add(group1)
        default_reviewer.groups.add(group2)

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.groups.add(group2)

        # Test singling out one group.
        rsp = self.apiGet('%s?groups=group2' % self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.apiGet('%s?groups=group1,group2' % self.get_list_url(),
                          expected_mimetype=self.list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_get_default_reviewer(self):
        """Testing the GET default-reviewers/<id>/ API"""
        user = User.objects.get(username='doc')
        group = Group.objects.create(name='group1')
        repository = Repository.objects.get(pk=1)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.people.add(user)
        default_reviewer.groups.add(group)
        default_reviewer.repository.add(repository)

        rsp = self.apiGet(self.get_item_url(default_reviewer.pk),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['default_reviewer']['name'], 'default1')
        self.assertEqual(rsp['default_reviewer']['file_regex'], '.*')

        users = rsp['default_reviewer']['users']
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['title'], user.username)

        groups = rsp['default_reviewer']['groups']
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['title'], group.name)

        repos = rsp['default_reviewer']['repositories']
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]['title'], repository.name)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewer_with_site(self):
        """Testing the GET default-reviewers/<id>/ API with a local site"""
        self._login_user(local_site=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        rsp = self.apiGet(self.get_item_url(default_reviewer.pk,
                                            self.local_site_name),
                          expected_mimetype=self.item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['default_reviewer']['name'], 'default1')
        self.assertEqual(rsp['default_reviewer']['file_regex'], '.*')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewer_with_site_no_access(self):
        """Testing the GET default-reviewers/<id>/ API with a local site and Permission Denied error"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiGet(self.get_item_url(default_reviewer.pk,
                                      self.local_site_name),
                    expected_status=403)

    def test_get_default_reviewer_not_modified(self):
        """Testing the GET default-reviewers/<id>/ API with Not Modified response"""
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self._testHttpCaching(self.get_item_url(default_reviewer.pk),
                              check_etags=True)

    @add_fixtures(['test_users'])
    def test_delete_default_reviewer(self):
        """Testing the DELETE default-reviewers/<id>/ API"""
        self._login_user(admin=True)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self.apiDelete(self.get_item_url(default_reviewer.pk),
                       expected_status=204)
        self.assertFalse(
            DefaultReviewer.objects.filter(name='default1').exists())

    @add_fixtures(['test_users'])
    def test_delete_default_reviewer_with_permission_denied_error(self):
        """Testing the DELETE default-reviewers/<id>/ API with Permission Denied error"""
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self.apiDelete(self.get_item_url(default_reviewer.pk),
                       expected_status=403)
        self.assertTrue(
            DefaultReviewer.objects.filter(name='default1').exists())

    @add_fixtures(['test_users', 'test_site'])
    def test_delete_default_reviewer_with_site(self):
        """Testing the DELETE default-reviewers/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiDelete(self.get_item_url(default_reviewer.pk,
                                         self.local_site_name),
                       expected_status=204)
        self.assertFalse(
            DefaultReviewer.objects.filter(name='default1').exists())

    @add_fixtures(['test_users', 'test_site'])
    def test_delete_default_reviewer_with_site_and_permission_denied_error(self):
        """Testing the DELETE default-reviewers/<id>/ API with a local site and Permission Denied error"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiDelete(self.get_item_url(default_reviewer.pk,
                                         self.local_site_name),
                       expected_status=403)
        self.assertTrue(
            DefaultReviewer.objects.filter(name='default1').exists())

    def get_list_url(self, local_site_name=None):
        return local_site_reverse(
            'default-reviewers-resource',
            local_site_name=local_site_name)

    def get_item_url(self, default_reviewer_id, local_site_name=None):
        return local_site_reverse(
            'default-reviewer-resource',
            local_site_name=local_site_name,
            kwargs={
                'default_reviewer_id': default_reviewer_id,
            })
