import os

from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.errors import DOES_NOT_EXIST, INVALID_ATTRIBUTE, \
                                  INVALID_FORM_DATA, PERMISSION_DENIED

from reviewboard import initialize
from reviewboard.diffviewer.models import DiffSet
from reviewboard.notifications.tests import EmailTestHelper
from reviewboard.reviews.models import Group, ReviewRequest, \
                                       ReviewRequestDraft, Review, \
                                       Comment, Screenshot, ScreenshotComment
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.webapi.errors import INVALID_REPOSITORY


class BaseWebAPITestCase(TestCase, EmailTestHelper):
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def setUp(self):
        initialize()

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("mail_send_review_mail", True)
        siteconfig.save()
        mail.outbox = []

        svn_repo_path = os.path.join(os.path.dirname(__file__),
                                     '../scmtools/testdata/svn_repo')
        self.repository = Repository(name='Subversion SVN',
                                     path='file://' + svn_repo_path,
                                     tool=Tool.objects.get(name='Subversion'))
        self.repository.save()

        self.client.login(username="grumpy", password="grumpy")
        self.user = User.objects.get(username="grumpy")

        self.reviewrequests_url = reverse('review-requests-resource')

        self.base_url = 'http://testserver'

    def tearDown(self):
        self.client.logout()

    def api_func_wrapper(self, api_func, path, query, expected_status,
                         follow_redirects, expected_redirects):
        response = api_func(path, query, follow=follow_redirects)
        self.assertEqual(response.status_code, expected_status)

        if expected_redirects:
            self.assertEqual(len(response.redirect_chain),
                             len(expected_redirects))

            for redirect in expected_redirects:
                self.assertEqual(response.redirect_chain[0][0],
                                 self.base_url + expected_redirects[0])

        return response

    def apiGet(self, path, query={}, follow_redirects=False,
               expected_status=200, expected_redirects=[]):
        path = self._normalize_path(path)

        print 'GETing %s' % path
        print "Query data: %s" % query

        response = self.api_func_wrapper(self.client.get, path, query,
                                         expected_status, follow_redirects,
                                         expected_redirects)

        print "Raw response: %s" % response.content

        rsp = simplejson.loads(response.content)
        print "Response: %s" % rsp

        return rsp

    def api_post_with_response(self, path, query={}, expected_status=201):
        path = self._normalize_path(path)

        print 'POSTing to %s' % path
        print "Post data: %s" % query
        response = self.client.post(path, query)
        print "Raw response: %s" % response.content
        self.assertEqual(response.status_code, expected_status)

        return self._get_result(response, expected_status), response

    def apiPost(self, *args, **kwargs):
        rsp, result = self.api_post_with_response(*args, **kwargs)

        return rsp

    def apiPut(self, path, query={}, expected_status=200,
               follow_redirects=False, expected_redirects=[]):
        path = self._normalize_path(path)

        print 'PUTing to %s' % path
        print "Post data: %s" % query
        response = self.api_func_wrapper(self.client.put, path, query,
                                         expected_status, follow_redirects,
                                         expected_redirects)
        print "Raw response: %s" % response.content
        self.assertEqual(response.status_code, expected_status)

        return self._get_result(response, expected_status)

    def apiDelete(self, path, expected_status=204):
        path = self._normalize_path(path)

        print 'DELETEing %s' % path
        response = self.client.delete(path)
        print "Raw response: %s" % response.content
        self.assertEqual(response.status_code, expected_status)

        return self._get_result(response, expected_status)

    def _normalize_path(self, path):
        if path.startswith(self.base_url):
            return path[len(self.base_url):]
        elif path.startswith('/api'):
            return path
        else:
            return '/api/%s/' % path

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
    def _postNewReviewRequest(self):
        """Creates a review request and returns the payload response."""
        rsp = self.apiPost("review-requests", {
            'repository': self.repository.path,
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['links']['repository']['href'],
                         self.base_url + reverse('repository-resource', kwargs={
                             'repository_id': self.repository.id,
                         }))

        return rsp

    def _postNewReview(self, review_request_id, body_top="",
                       body_bottom=""):
        """Creates a review and returns the payload response."""
        rsp = self.apiPost("review-requests/%s/reviews" % review_request_id, {
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review']['body_top'], body_top)
        self.assertEqual(rsp['review']['body_bottom'], body_bottom)

        return rsp

    def _postNewDiffComment(self, review_request, review_id, comment_text,
                            filediff_id=None, interfilediff_id=None,
                            first_line=10, num_lines=5):
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

        rsp = self.apiPost("review-requests/%s/reviews/%s/diff-comments" %
                           (review_request.id, review_id),
                           data)
        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewScreenshotComment(self, review_request, review_id, screenshot,
                                  comment_text, x, y, w, h):
        """Creates a screenshot comment and returns the payload response."""
        rsp = self.apiPost(
            "review-requests/%s/reviews/%s/screenshot-comments" %
            (review_request.id, review_id),
            {
                'screenshot_id': screenshot.id,
                'text': comment_text,
                'x': x,
                'y': y,
                'w': w,
                'h': h,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewScreenshot(self, review_request):
        """Creates a screenshot and returns the payload response."""
        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost("review-requests/%s/screenshots" %
                           review_request.id, {
            'path': f,
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _postNewDiff(self, review_request):
        """Creates a diff and returns the payload response."""
        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scmtools", "testdata", "svn_makefile.diff")

        f = open(diff_filename, "r")
        rsp = self.apiPost("review-requests/%s/diffs" % review_request.id, {
            'path': f,
            'basedir': "/trunk",
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def _getTrophyFilename(self):
        return os.path.join(settings.HTDOCS_ROOT,
                            "media", "rb", "images", "trophy.png")


class ServerInfoResourceTests(BaseWebAPITestCase):
    """Testing the ServerInfoResource APIs."""
    def test_get_server_info(self):
        """Testing the GET info/ API"""
        rsp = self.apiGet('info')
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('info' in rsp)
        self.assertTrue('product' in rsp['info'])
        self.assertTrue('site' in rsp['info'])


class RepositoryResourceTests(BaseWebAPITestCase):
    """Testing the RepositoryResource APIs."""
    def test_get_repositories(self):
        """Testing the GET repositories/ API"""
        rsp = self.apiGet("repositories")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), Repository.objects.count())

    def test_get_repository_info(self):
        """Testing the GET repositories/<id>/info API"""
        rsp = self.apiGet("repositories/%d/info" % self.repository.pk)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['info'],
                         self.repository.get_scmtool().get_repository_info())


class ReviewGroupResourceTests(BaseWebAPITestCase):
    """Testing the ReviewGroupResource APIs."""
    def test_get_groups(self):
        """Testing the GET groups/ API"""
        rsp = self.apiGet("groups")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), Group.objects.count())

    def test_get_groups_with_q(self):
        """Testing the GET groups/?q= API"""
        rsp = self.apiGet("groups", {'q': 'dev'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), 1) #devgroup


class UserResourceTests(BaseWebAPITestCase):
    """Testing the UserResource API tests."""
    def test_get_users(self):
        """Testing the GET users/ API"""
        rsp = self.apiGet("users")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), User.objects.count())

    def test_get_users_with_q(self):
        """Testing the GET users/?q= API"""
        rsp = self.apiGet("users", {'q': 'gru'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 1) # grumpy


class WatchedReviewRequestResourceTests(BaseWebAPITestCase):
    """Testing the WatchedReviewRequestResource API tests."""
    def setUp(self):
        super(WatchedReviewRequestResourceTests, self).setUp()
        self.watched_url = reverse('watched-review-requests-resource',
                                   kwargs={
                                       'username': self.user.username,
                                   })

    def test_post_watched_review_request(self):
        """Testing the POST users/<username>/watched/review_request/ API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiPost(self.watched_url, {
            'object_id': review_request.id,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(review_request in
                     self.user.get_profile().starred_review_requests.all())

    def test_post_watched_review_request_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review_request/ with Does Not Exist error"""
        rsp = self.apiPost(self.watched_url, {
            'object_id': 999,
        }, expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_delete_watched_review_request(self):
        """Testing the DELETE users/<username>/watched/review_request/ API"""
        # First, star it.
        self.test_post_watched_review_request()

        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiDelete("%s%s/" % (self.watched_url, review_request.id))
        self.assert_(review_request not in
                     self.user.get_profile().starred_review_requests.all())

    def test_delete_watched_review_request_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review_request/ API with Does Not Exist error"""
        rsp = self.apiDelete("%s%s/" % (self.watched_url, 999),
                             expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)


class WatchedReviewGroupResourceTests(BaseWebAPITestCase):
    """Testing the WatchedReviewGroupResource API tests."""
    def setUp(self):
        super(WatchedReviewGroupResourceTests, self).setUp()
        self.watched_url = reverse('watched-review-groups-resource',
                                   kwargs={
                                       'username': self.user.username,
                                   })

    def test_post_watched_review_group(self):
        """Testing the POST users/<username>/watched/review-groups/ API"""
        group = Group.objects.get(name='devgroup')

        rsp = self.apiPost(self.watched_url, {
            'object_id': group.name,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(group in self.user.get_profile().starred_groups.all())

    def test_post_watched_review_group_with_does_not_exist_error(self):
        """Testing the POST users/<username>/watched/review-groups/ API with Does Not Exist error"""
        rsp = self.apiPost(self.watched_url, {
            'object_id': 'invalidgroup',
        }, expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def test_delete_watched_review_group(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API"""
        # First, star it.
        self.test_post_watched_review_group()

        group = Group.objects.get(name='devgroup')

        rsp = self.apiDelete('%s%s/' % (self.watched_url, group.name))
        self.assertTrue(group not in
                        self.user.get_profile().starred_groups.all())

    def test_delete_watched_review_group_with_does_not_exist_error(self):
        """Testing the DELETE users/<username>/watched/review-groups/<id>/ API with Does Not Exist error"""
        rsp = self.apiDelete('%s%s/' % (self.watched_url, 'invalidgroup'),
                             expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)


class ReviewRequestResourceTests(BaseWebAPITestCase):
    """Testing the ReviewRequestResource API tests."""
    def test_get_reviewrequests(self):
        """Testing the GET review-requests/ API"""
        rsp = self.apiGet("review-requests")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public().count())

    def test_get_reviewrequests_with_status(self):
        """Testing the GET review-requests/?status= API"""
        rsp = self.apiGet("review-requests", {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='S').count())

        rsp = self.apiGet("review-requests", {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='D').count())

        rsp = self.apiGet("review-requests", {'status': 'all'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status=None).count())

    def test_get_reviewrequests_with_counts_only(self):
        """Testing the GET review-requests/?counts-only=1 API"""
        rsp = self.apiGet('review-requests', {
            'counts-only': 1,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], ReviewRequest.objects.public().count())

    def test_get_reviewrequests_with_to_groups(self):
        """Testing the GET review-requests/?to-groups= API"""
        rsp = self.apiGet("review-requests", {
            'to-groups': 'devgroup',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_group("devgroup").count())

    def test_get_reviewrequests_with_to_groups_and_status(self):
        """Testing the GET review-requests/?to-groups=&status= API"""
        rsp = self.apiGet('review-requests', {
            'status': 'submitted',
            'to-groups': 'devgroup',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", status='S').count())

        rsp = self.apiGet('review-requests', {
            'status': 'discarded',
            'to-groups': 'devgroup',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", status='D').count())

    def test_get_reviewrequests_with_to_groups_and_counts_only(self):
        """Testing the GET review-requests/?to-groups=&counts-only=1 API"""
        rsp = self.apiGet('review-requests', {
            'to-groups': 'devgroup',
            'counts-only': 1,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_group("devgroup").count())

    def test_get_reviewrequests_with_to_users(self):
        """Testing the GET review-requests/?to-users= API"""
        rsp = self.apiGet('review-requests', {
            'to-users': 'grumpy',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user("grumpy").count())

    def test_get_reviewrequests_with_to_users_and_status(self):
        """Testing the GET review-requests/?to-users=&status= API"""
        rsp = self.apiGet("review-requests", {
            'status': 'submitted',
            'to-users': 'grumpy',
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='S').count())

        rsp = self.apiGet("review-requests", {
            'status': 'discarded',
            'to-users': 'grumpy',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='D').count())

    def test_get_reviewrequests_with_to_users_and_counts_only(self):
        """Testing the GET review-requests/?to-users=&counts-only=1 API"""
        rsp = self.apiGet('review-requests', {
            'to-users': 'grumpy',
            'counts-only': 1,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user("grumpy").count())

    def test_get_reviewrequests_with_to_users_directly(self):
        """Testing the GET review-requests/?to-users-directly= API"""
        rsp = self.apiGet('review-requests', {
            'to-users-directly': 'doc',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_reviewrequests_with_to_users_directly_and_status(self):
        """Testing the GET review-requests/?to-users-directly=&status= API"""
        rsp = self.apiGet('review-requests', {
            'status': 'submitted',
            'to-users-directly': 'doc'
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='S').count())

        rsp = self.apiGet('review-requests', {
            'status': 'discarded',
            'to-users-directly': 'doc'
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='D').count())

    def test_get_reviewrequests_with_to_users_directly_and_counts_only(self):
        """Testing the GET review-requests/?to-users-directly=&counts-only=1 API"""
        rsp = self.apiGet('review-requests', {
            'to-users-directly': 'doc',
            'counts-only': 1,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_reviewrequests_with_from_user(self):
        """Testing the GET review-requests/?from-user= API"""
        rsp = self.apiGet('review-requests', {
            'from-user': 'grumpy',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.from_user("grumpy").count())

    def test_get_reviewrequests_with_from_user_and_status(self):
        """Testing the GET review-requests/?from-user=&status= API"""
        rsp = self.apiGet('review-requests', {
            'status': 'submitted',
            'from-user': 'grumpy',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='S').count())

        rsp = self.apiGet('review-requests', {
            'status': 'discarded',
            'from-user': 'grumpy',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='D').count())

    def test_get_reviewrequests_with_from_user_and_counts_only(self):
        """Testing the GET review-requests/?from-user=&counts-only=1 API"""
        rsp = self.apiGet('review-requests', {
            'from-user': 'grumpy',
            'counts-only': 1,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.from_user("grumpy").count())

    def test_post_reviewrequests(self):
        """Testing the POST review-requests/ API"""
        rsp = self.apiPost("review-requests", {
            'repository': self.repository.path,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['links']['repository']['href'],
                         self.base_url + reverse('repository-resource', kwargs={
                             'repository_id': self.repository.id,
                         }))

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        return ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def test_post_reviewrequests_with_invalid_repository_error(self):
        """Testing the POST review-requests/ API with Invalid Repository error"""
        rsp = self.apiPost("review-requests", {
            'repository': 'gobbledygook',
        }, expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    def test_post_reviewrequests_with_submit_as(self):
        """Testing the POST review-requests/?submit_as= API"""
        self.user.is_superuser = True
        self.user.save()

        rsp = self.apiPost("review-requests", {
            'repository': self.repository.path,
            'submit_as': 'doc',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['links']['repository']['href'],
                         self.base_url + reverse('repository-resource', kwargs={
                             'repository_id': self.repository.id,
                         }))
        self.assertEqual(rsp['review_request']['links']['submitter']['href'],
                         self.base_url + reverse('user-resource', kwargs={
                             'username': 'doc',
                         }))

        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def test_post_reviewrequests_with_submit_as_and_permission_denied_error(self):
        """Testing the POST review-requests/?submit_as= API with Permission Denied error"""
        rsp = self.apiPost("review-requests", {
            'repository': self.repository.path,
            'submit_as': 'doc',
        }, expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequest_status_discarded(self):
        """Testing the PUT review-requests/<id>/?status=discarded API"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        rsp = self.apiPut('review-requests/%s' % r.id, {
            'status': 'discarded',
        })

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'D')

    def test_put_reviewrequest_status_pending(self):
        """Testing the PUT review-requests/<id>/?status=pending API"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.close(ReviewRequest.SUBMITTED)
        r.save()

        rsp = self.apiPut('review-requests/%s' % r.id, {
            'status': 'pending',
        })

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'P')

    def test_put_reviewrequest_status_submitted(self):
        """Testing the PUT review-requests/<id>/?status=submitted API"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        rsp = self.apiPut('review-requests/%s' % r.id, {
            'status': 'submitted',
        })

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

    def test_get_reviewrequest(self):
        """Testing the GET review-requests/<id>/ API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiGet("review-requests/%s" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    def test_get_reviewrequest_with_permission_denied_error(self):
        """Testing the GET review-requests/<id>/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=False).\
            exclude(submitter=self.user)[0]
        rsp = self.apiGet("review-requests/%s" % review_request.id,
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_reviewrequest_with_repository_and_changenum(self):
        """Testing the GET review-requests/?repository=&changenum= API"""
        review_request = \
            ReviewRequest.objects.filter(changenum__isnull=False)[0]
        rsp = self.apiGet('review-requests', {
            'repository': review_request.repository.id,
            'changenum': review_request.changenum,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)
        self.assertEqual(rsp['review_requests'][0]['id'],
                         review_request.id)
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

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiDelete("review-requests/%s" % review_request_id)
        self.assertEqual(rsp, None)
        self.assertRaises(ReviewRequest.DoesNotExist,
                          ReviewRequest.objects.get, pk=review_request_id)

    def test_delete_reviewrequest_with_permission_denied_error(self):
        """Testing the DELETE review-requests/<id>/ API with Permission Denied error"""
        review_request_id = \
            ReviewRequest.objects.exclude(submitter=self.user)[0].id
        rsp = self.apiDelete("review-requests/%s" % review_request_id,
                             expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_reviewrequest_with_does_not_exist_error(self):
        """Testing the DELETE review-requests/<id>/ API with Does Not Exist error"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assert_(self.user.has_perm('reviews.delete_reviewrequest'))

        rsp = self.apiDelete("review-requests/999", expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)


class ReviewRequestDraftResourceTests(BaseWebAPITestCase):
    """Testing the ReviewRequestDraftResource API tests."""
    def _create_update_review_request(self, apiFunc, review_request_id=None):
        summary = "My Summary"
        description = "My Description"
        testing_done = "My Testing Done"
        branch = "My Branch"
        bugs = "#123,456"

        if review_request_id is None:
            review_request_id = \
                ReviewRequest.objects.from_user(self.user.username)[0].id

        rsp = apiFunc("review-requests/%s/draft" % review_request_id, {
            'summary': summary,
            'description': description,
            'testing_done': testing_done,
            'branch': branch,
            'bugs_closed': bugs,
        })

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

    def test_put_reviewrequestdraft(self):
        """Testing the PUT review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPut)

    def test_post_reviewrequestdraft(self):
        """Testing the POST review-requests/<id>/draft/ API"""
        self._create_update_review_request(self.apiPost)

    def test_put_reviewrequestdraft_with_changedesc(self):
        """Testing the PUT review-requests/<id>/draft/ API with a change description"""
        changedesc = 'This is a test change description.'
        review_request = ReviewRequest.objects.create(self.user,
                                                      self.repository)
        review_request.publish(self.user)

        rsp = self.apiPost("review-requests/%s/draft" % review_request.id, {
            'changedescription': changedesc,
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['changedescription'], changedesc)

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertNotEqual(draft.changedesc, None)
        self.assertEqual(draft.changedesc.text, changedesc)

    def test_put_reviewrequestdraft_with_invalid_field_name(self):
        """Testing the PUT review-requests/<id>/draft/ API with Invalid Form Data error"""
        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPut("review-requests/%s/draft" % review_request_id, {
            'foobar': 'foo',
        }, 400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('foobar' in rsp['fields'])

    def test_put_reviewrequestdraft_with_permission_denied_error(self):
        """Testing the PUT review-requests/<id>/draft/ API with Permission Denied error"""
        bugs_closed = '123,456'
        review_request_id = ReviewRequest.objects.from_user('admin')[0].id
        rsp = self.apiPut("review-requests/%s/draft" % review_request_id, {
            'bugs_closed': bugs_closed,
        }, 403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_reviewrequestdraft_publish(self):
        """Testing the PUT review-requests/<id>/draft/?public=1 API"""
        # Set some data first.
        self.test_put_reviewrequestdraft()

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPut("review-requests/%s/draft" % review_request_id, {
            'public': True,
        }, follow_redirects=True, expected_redirects=[
            reverse('review-request-resource', kwargs={
                'review_request_id': review_request_id,
            })
        ])

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request_id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")
        self.assertTrue(review_request.public)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Review Request: My Summary")
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

        self._create_update_review_request(self.apiPut, review_request.id)

        rsp = self.apiPut("review-requests/%s/draft" % review_request.id, {
            'public': True,
        }, follow_redirects=True, expected_redirects=[
            reverse('review-request-resource', kwargs={
                'review_request_id': review_request.id,
            })
        ])

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")
        self.assertTrue(review_request.public)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Review Request: My Summary")
        self.assertValidRecipients(["doc", "grumpy"], [])

    def test_delete_reviewrequestdraft(self):
        """Testing the DELETE review-requests/<id>/draft/ API"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]
        summary = review_request.summary
        description = review_request.description

        # Set some data.
        self.test_put_reviewrequestdraft()

        rsp = self.apiDelete("review-requests/%s/draft" % review_request.id)

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)


class ReviewResourceTests(BaseWebAPITestCase):
    """Testing the ReviewResource APIs."""
    def test_get_reviews(self):
        """Testing the GET review-requests/<id>/reviews/ API"""
        review_request = Review.objects.filter()[0].review_request
        rsp = self.apiGet("review-requests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['reviews']), review_request.reviews.count())

    def test_get_reviews_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/?counts-only=1 API"""
        review_request = Review.objects.all()[0].review_request
        rsp = self.apiGet("review-requests/%s/reviews" % review_request.id, {
            'counts-only': 1,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review_request.reviews.count())

    def test_post_reviews(self):
        """Testing the POST review-requests/<id>/reviews/ API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp, response = self.api_post_with_response(
            'review-requests/%s/reviews' % review_request.id,
            {
                'ship_it': ship_it,
                'body_top': body_top,
                'body_bottom': body_bottom,
            })

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(response['Location'],
                         self.base_url + reverse('review-resource', kwargs={
                             'review_request_id': review_request.id,
                             'review_id': review.id,
                         }))

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, False)

        self.assertEqual(len(mail.outbox), 0)

    def test_put_review(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp, response = self.api_post_with_response(
            'review-requests/%s/reviews' % review_request.id)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        review_url = response['Location']

        rsp = self.apiPut(review_url, {
            'ship_it': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

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

    def test_put_review_with_published_review(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/ API with pre-published review"""
        review = Review.objects.filter(user=self.user, public=True,
                                       base_reply_to__isnull=True)[0]

        rsp = self.apiPut(
            'review-requests/%s/reviews/%s' % (review.review_request.id,
                                              review.id),
            {
                'ship_it': True,
            },
            expected_status=403)

    def test_put_review_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/?public=1 API"""
        body_top = "My Body Top"
        body_bottom = ""
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp, response = self.api_post_with_response(
            'review-requests/%s/reviews' % review_request.id)

        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('Location' in response)

        review_url = response['Location']

        rsp = self.apiPut(review_url, {
            'public': True,
            'ship_it': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, True)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Interdiff Revision Test")
        self.assertValidRecipients(["admin", "grumpy"], [])

    def test_delete_review(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API"""
        # Set up the draft to delete.
        review = self.test_put_review()
        review_request = review.review_request

        rsp = self.apiDelete("review-requests/%s/reviews/%s" %
                             (review_request.id, review.id))
        self.assertEqual(review_request.reviews.count(), 0)

    def test_delete_review_with_permission_denied(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with Permission Denied error"""
        # Set up the draft to delete.
        review = self.test_put_review()
        review.user = User.objects.get(username='doc')
        review.save()

        review_request = review.review_request
        old_count = review_request.reviews.count()

        rsp = self.apiDelete("review-requests/%s/reviews/%s" %
                             (review_request.id, review.id),
                             expected_status=403)
        self.assertEqual(review_request.reviews.count(), old_count)

    def test_delete_review_with_published_review(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with pre-published review"""
        review = Review.objects.filter(user=self.user, public=True,
                                       base_reply_to__isnull=True)[0]
        review_request = review.review_request
        old_count = review_request.reviews.count()

        rsp = self.apiDelete("review-requests/%s/reviews/%s" %
                             (review_request.id, review.id),
                             expected_status=403)
        self.assertEqual(review_request.reviews.count(), old_count)

    def test_delete_review_with_does_not_exist(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/ API with Does Not Exist error"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiDelete("review-requests/%s/reviews/919239" %
                             review_request.id, expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)


class ReviewCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewCommentResource APIs."""
    def test_get_diff_comments(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet("review-requests/%s/reviews/%s/diff-comments" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), review.comments.count())

    def test_get_diff_comments_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/<id>/diff-comments/?counts-only=1 API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet("review-requests/%s/reviews/%s/diff-comments" %
                          (review.review_request.id, review.id), {
            'counts-only': 1,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.comments.count())

    def test_post_diff_comments(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API"""
        diff_comment_text = "Test diff comment"

        # Post the review request
        rsp = self._postNewReviewRequest()
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])

        # Post the diff.
        rsp = self._postNewDiff(review_request)
        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])

        # Make these public.
        review_request.publish(self.user)

        rsp = self.apiPost("review-requests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        rsp = self.apiGet("review-requests/%s/reviews/%s/diff-comments" %
                          (review_request.id, review_id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)

    def test_post_diff_comments_with_interdiff(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with interdiff"""
        comment_text = "Test diff comment"

        rsp, review_request_id, review_id, interfilediff_id = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiGet("review-requests/%s/reviews/%s/diff-comments" %
                          (review_request_id, review_id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    def test_delete_diff_comment_with_interdiff(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API"""
        comment_text = "This is a test comment."

        rsp, review_request_id, review_id = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiDelete(rsp['diff_comment']['links']['self']['href'])

        rsp = self.apiGet("review-requests/%s/reviews/%s/diff-comments" %
                          (review_request_id, review_id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

    def test_get_diff_comments_with_interdiff(self):
        """Testing the POST review-requests/<id>/reviews/<id>/diff-comments/ API with interdiff"""
        comment_text = "Test diff comment"

        rsp, review_request_id, review_id, interfilediff_id = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiGet("review-requests/%s/reviews/%s/diff-comments" %
                          (review_request_id, review_id), {
            'interdiff_fileid': interfilediff_id,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment_text)

    def test_delete_diff_comment_with_interdiff(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/diff-comments/<id>/ API"""
        comment_text = "This is a test comment."

        rsp, review_request_id, review_id, interfilediff_id = \
            self._common_post_interdiff_comments(comment_text)

        rsp = self.apiDelete(rsp['diff_comment']['links']['self']['href'])

        rsp = self.apiGet("review-requests/%s/reviews/%s/diff-comments" %
                          (review_request_id, review_id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('diff_comments' in rsp)
        self.assertEqual(len(rsp['diff_comments']), 0)

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

        rsp = self.apiPost("review-requests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        rsp = self._postNewDiffComment(review_request, review_id,
                                       comment_text,
                                       filediff_id=filediff.id,
                                       interfilediff_id=interfilediff.id)

        return rsp, review_request.id, review_id, interfilediff.id


class ReviewScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewScreenshotCommentResource APIs."""
    def test_get_review_screenshot_comments(self):
        """Testing the GET review-requests/<id>/reviews/draft/screenshot-comments API"""
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

        rsp = self.apiPost("review-requests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewScreenshotComment(review_request, review_id, screenshot,
                                       screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet(
            "review-requests/%s/reviews/%s/screenshot-comments" %
            (review_request.id, review_id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)


class ReviewReplyResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyResource APIs."""
    def test_get_replies(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.test_put_reply()

        rsp = self.apiGet("review-requests/%s/reviews/%s/replies" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), len(review.public_replies()))

        for reply in review.public_replies():
            self.assertEqual(rsp['replies'][0]['id'], reply.id)
            self.assertEqual(rsp['replies'][0]['body_top'], reply.body_top)
            self.assertEqual(rsp['replies'][0]['body_bottom'],
                             reply.body_bottom)

    def test_get_replies_with_counts_only(self):
        """Testing the GET review-requests/<id>/reviews/<id>/replies/?counts-only=1 API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.test_put_reply()

        rsp = self.apiGet(
            'review-requests/%s/reviews/%s/replies/?counts-only=1' %
            (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], len(review.public_replies()))

    def test_post_replies(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("review-requests/%s/reviews/%s/replies" %
                           (review.review_request.id, review.id), {
            'body_top': 'Test',
        })

        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(len(mail.outbox), 0)

    def test_post_replies_with_body_top(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with body_top"""
        body_top = 'My Body Top'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("review-requests/%s/reviews/%s/replies" %
                           (review.review_request.id, review.id), {
            'body_top': body_top,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_top, body_top)

    def test_post_replies_with_body_bottom(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/ API with body_bottom"""
        body_bottom = 'My Body Bottom'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("review-requests/%s/reviews/%s/replies" %
                           (review.review_request.id, review.id), {
            'body_bottom': body_bottom,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_bottom, body_bottom)

    def test_put_reply(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id> API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp, response = self.api_post_with_response(
            'review-requests/%s/reviews/%s/replies' %
            (review.review_request.id, review.id))

        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(response['Location'], {
            'body_top': 'Test',
        })

        self.assertEqual(rsp['stat'], 'ok')

    def test_put_reply_publish(self):
        """Testing the PUT review-requests/<id>/reviews/<id>/replies/<id>/?public=1 API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp, response = self.api_post_with_response(
            'review-requests/%s/reviews/%s/replies' %
            (review.review_request.id, review.id))

        self.assertTrue('Location' in response)
        self.assertTrue('stat' in rsp)
        self.assertEqual(rsp['stat'], 'ok')

        rsp = self.apiPut(response['Location'], {
            'body_top': 'Test',
            'public': True,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.public, True)

        self.assertEqual(len(mail.outbox), 1)

    def test_put_reply_with_diff_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/diff-comments/ API"""
        comment_text = "My Comment Text"

        comment = Comment.objects.all()[0]
        review = comment.review.get()

        # Create the reply
        rsp = self.apiPost("review-requests/%s/reviews/%s/replies" %
                           (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')

        self.assertTrue('reply' in rsp)
        self.assertNotEqual(rsp['reply'], None)
        self.assertTrue('links' in rsp['reply'])
        self.assertTrue('diff_comments' in rsp['reply']['links'])

        rsp = self.apiPost(rsp['reply']['links']['diff_comments']['href'], {
            'reply_to_id': comment.id,
            'text': comment_text,
        })
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['diff_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def test_delete_reply(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/replies/<id>/ API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost('review-requests/%s/reviews/%s/replies' %
                           (review.review_request.id, review.id), {
            'body_top': 'Test',
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply_id = rsp['reply']['id']
        rsp = self.apiDelete(rsp['reply']['links']['self']['href'])

        self.assertEqual(Review.objects.filter(pk=reply_id).count(), 0)


class ReviewReplyScreenshotCommentResourceTests(BaseWebAPITestCase):
    """Testing the ReviewReplyScreenshotCommentResource APIs."""
    def test_post_reply_with_screenshot_comment(self):
        """Testing the POST review-requests/<id>/reviews/<id>/replies/<id>/screenshot-comments/ API"""
        comment_text = "My Comment Text"
        x, y, w, h = 10, 10, 20, 20

        rsp = self._postNewReviewRequest()
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        rsp = self._postNewScreenshot(review_request)
        screenshot = Screenshot.objects.get(pk=rsp['screenshot']['id'])

        rsp = self._postNewReview(review_request.id)
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

        rsp = self.apiPost(replies_url)
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
        })
        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)


class FileDiffResourceTests(BaseWebAPITestCase):
    """Testing the FileDiffResource APIs."""
    def test_post_diffs(self):
        """Testing the POST review-requests/<id>/diffs/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scmtools", "testdata", "svn_makefile.diff")
        f = open(diff_filename, "r")
        rsp = self.apiPost(rsp['review_request']['links']['diffs']['href'], {
            'path': f,
            'basedir': "/trunk",
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_diffs_with_missing_data(self):
        """Testing the POST review-requests/<id>/diffs/ API with Invalid Form Data"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        rsp = self.apiPost(rsp['review_request']['links']['diffs']['href'],
                           expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assert_('path' in rsp['fields'])
        self.assert_('basedir' in rsp['fields'])

    def test_get_diffs(self):
        """Testing the GET review-requests/<id>/diffs/ API"""
        rsp = self.apiGet("review-requests/2/diffs")

        self.assertEqual(rsp['diffs'][0]['id'], 2)
        self.assertEqual(rsp['diffs'][0]['name'], 'cleaned_data.diff')

    def test_get_diff(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API"""
        rsp = self.apiGet("review-requests/2/diffs/1")

        self.assertEqual(rsp['diff']['id'], 2)
        self.assertEqual(rsp['diff']['name'], 'cleaned_data.diff')


class ScreenshotDraftResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotDraftResource APIs."""
    def test_post_screenshots(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        screenshots_url = rsp['review_request']['links']['screenshots']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(screenshots_url, {
            'path': f,
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_screenshots_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/screenshots/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True).\
            exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost('review-requests/%s/draft/screenshots' %
                           review_request.id, {
            'caption': 'Trophy',
            'path': f,
        }, expected_status=403)
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
        rsp = self.apiPost('review-requests/%s/draft/screenshots' %
                            review_request.id, {
            'caption': 'Trophy',
            'path': f,
        })
        f.close()
        review_request.publish(self.user)

        screenshot = Screenshot.objects.get(pk=rsp['draft-screenshot']['id'])

        # Now modify the caption.
        rsp = self.apiPut('review-requests/%s/draft/screenshots/%s' %
                          (review_request.id, screenshot.id), {
            'caption': draft_caption,
        })

        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(self.user)
        self.assertNotEqual(draft, None)

        screenshot = Screenshot.objects.get(pk=screenshot.id)
        self.assertEqual(screenshot.draft_caption, draft_caption)


class ScreenshotResourceTests(BaseWebAPITestCase):
    """Testing the ScreenshotResource APIs."""
    def test_post_screenshots(self):
        """Testing the POST review-requests/<id>/screenshots/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        screenshots_url = rsp['review_request']['links']['screenshots']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(screenshots_url, {
            'path': f,
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_screenshots_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/screenshots/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True).\
            exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost('review-requests/%s/screenshots' %
                           review_request.id, {
            'caption': 'Trophy',
            'path': f,
        }, expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class FileDiffCommentResourceTests(BaseWebAPITestCase):
    """Testing the FileDiffCommentResource APIs."""
    def test_get_comments(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API"""
        diff_comment_text = 'Sample comment.'

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost("review-requests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text)

        rsp = self.apiGet(
            'review-requests/%s/diffs/%s/files/%s/diff-comments' %
            (review_request.id, diffset.revision, filediff.id))
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)

    def test_get_comments_with_line(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/?line= API"""
        diff_comment_text = 'Sample comment.'
        diff_comment_line = 10

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost("review-requests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('review' in rsp)
        review_id = rsp['review']['id']

        self._postNewDiffComment(review_request, review_id, diff_comment_text,
                                 first_line=diff_comment_line)

        self._postNewDiffComment(review_request, review_id, diff_comment_text,
                                 first_line=diff_comment_line + 1)

        url = 'review-requests/%s/diffs/%s/files/%s/diff-comments' % \
              (review_request.id, diffset.revision, filediff.id)
        rsp = self.apiGet(url, {
            'line': diff_comment_line,
        })
        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff,
                                          first_line=diff_comment_line)
        self.assertEqual(len(rsp['diff_comments']), comments.count())

        for i in range(0, len(rsp['diff_comments'])):
            self.assertEqual(rsp['diff_comments'][i]['text'], comments[i].text)
            self.assertEqual(rsp['diff_comments'][i]['first_line'],
                             comments[i].first_line)


class ScreenshotCommentResource(BaseWebAPITestCase):
    """Testing the ScreenshotCommentResource APIs."""
    def test_get_screenshot_comments(self):
        """Testing the GET review-requests/<id>/screenshos/<id>/comments/ API"""
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
        rsp = self._postNewReview(review_request.id)
        review = Review.objects.get(pk=rsp['review']['id'])

        self._postNewScreenshotComment(review_request, review.id, screenshot,
                                      comment_text, x, y, w, h)

        rsp = self.apiGet(comments_url)
        self.assertEqual(rsp['stat'], 'ok')

        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
        self.assertEqual(len(rsp['screenshot_comments']), comments.count())

        rsp_comments = rsp['screenshot_comments']

        for i in range(0, len(comments)):
            self.assertEqual(rsp_comments[i]['text'], comments[i].text)
            self.assertEqual(rsp_comments[i]['x'], comments[i].x)
            self.assertEqual(rsp_comments[i]['y'], comments[i].y)
            self.assertEqual(rsp_comments[i]['w'], comments[i].w)
            self.assertEqual(rsp_comments[i]['h'], comments[i].h)


class ReviewScreenshotCommentResource(BaseWebAPITestCase):
    """Testing the ScreenshotCommentResource APIs."""
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
        rsp = self._postNewReview(review_request.id)
        review = Review.objects.get(pk=rsp['review']['id'])

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        self.assertEqual(rsp['screenshot_comment']['text'], comment_text)
        self.assertEqual(rsp['screenshot_comment']['x'], x)
        self.assertEqual(rsp['screenshot_comment']['y'], y)
        self.assertEqual(rsp['screenshot_comment']['w'], w)
        self.assertEqual(rsp['screenshot_comment']['h'], h)

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
        rsp = self._postNewReview(review_request.id)
        review = Review.objects.get(pk=rsp['review']['id'])
        screenshot_comments_url = \
            rsp['review']['links']['screenshot_comments']['href']

        rsp = self._postNewScreenshotComment(review_request, review.id,
                                             screenshot, comment_text,
                                             x, y, w, h)

        rsp = self.apiDelete(
            rsp['screenshot_comment']['links']['self']['href'])

        rsp = self.apiGet(screenshot_comments_url)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue('screenshot_comments' in rsp)
        self.assertEqual(len(rsp['screenshot_comments']), 0)

    def test_delete_screenshot_comment_with_does_not_exist_error(self):
        """Testing the DELETE review-requests/<id>/reviews/<id>/screenshot-comments/<id>/ API with Does Not Exist error"""
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
        rsp = self._postNewReview(review_request.id)
        review = Review.objects.get(pk=rsp['review']['id'])

        self.apiDelete('review-requests/%s/reviews/%s/screenshot-comments/123' %
                       (review_request.id, review.id),
                       expected_status=404)


class DeprecatedWebAPITests(TestCase, EmailTestHelper):
    """Testing the deprecated webapi support."""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def setUp(self):
        initialize()

        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("mail_send_review_mail", True)
        siteconfig.save()
        mail.outbox = []

        svn_repo_path = os.path.join(os.path.dirname(__file__),
                                     '../scmtools/testdata/svn_repo')
        self.repository = Repository(name='Subversion SVN',
                                     path='file://' + svn_repo_path,
                                     tool=Tool.objects.get(name='Subversion'))
        self.repository.save()

        self.client.login(username="grumpy", password="grumpy")
        self.user = User.objects.get(username="grumpy")

    def tearDown(self):
        self.client.logout()

    def apiGet(self, path, query={}, expected_status=200):
        print "Getting /api/json/%s/" % path
        print "Query data: %s" % query
        response = self.client.get("/api/json/%s/" % path, query)
        self.assertEqual(response.status_code, expected_status)
        print "Raw response: %s" % response.content
        rsp = simplejson.loads(response.content)
        print "Response: %s" % rsp
        return rsp

    def apiPost(self, path, query={}, expected_status=200):
        print "Posting to /api/json/%s/" % path
        print "Post data: %s" % query
        response = self.client.post("/api/json/%s/" % path, query)
        self.assertEqual(response.status_code, expected_status)
        print "Raw response: %s" % response.content
        rsp = simplejson.loads(response.content)
        print "Response: %s" % rsp
        return rsp

    def testRepositoryList(self):
        """Testing the deprecated repositories API"""
        rsp = self.apiGet("repositories")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), Repository.objects.count())

    def testUserList(self):
        """Testing the deprecated users API"""
        rsp = self.apiGet("users")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), User.objects.count())

    def testUserListQuery(self):
        """Testing the deprecated users API with custom query"""
        rsp = self.apiGet("users", {'query': 'gru'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 1) # grumpy

    def testGroupList(self):
        """Testing the deprecated groups API"""
        rsp = self.apiGet("groups")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), Group.objects.count())

    def testGroupListQuery(self):
        """Testing the deprecated groups API with custom query"""
        rsp = self.apiGet("groups", {'query': 'dev'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), 1) #devgroup

    def testGroupStar(self):
        """Testing the deprecated groups/star API"""
        rsp = self.apiGet("groups/devgroup/star")
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(Group.objects.get(name="devgroup") in
                     self.user.get_profile().starred_groups.all())

    def testGroupStarDoesNotExist(self):
        """Testing the deprecated groups/star API with Does Not Exist error"""
        rsp = self.apiGet("groups/invalidgroup/star")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testGroupUnstar(self):
        """Testing the deprecated groups/unstar API"""
        # First, star it.
        self.testGroupStar()

        rsp = self.apiGet("groups/devgroup/unstar")
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(Group.objects.get(name="devgroup") not in
                     self.user.get_profile().starred_groups.all())

    def testGroupUnstarDoesNotExist(self):
        """Testing the deprecated groups/unstar API with Does Not Exist error"""
        rsp = self.apiGet("groups/invalidgroup/unstar")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testReviewRequestList(self):
        """Testing the deprecated reviewrequests/all API"""
        rsp = self.apiGet("reviewrequests/all")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public().count())

    def testReviewRequestListWithStatus(self):
        """Testing the deprecated reviewrequests/all API with custom status"""
        rsp = self.apiGet("reviewrequests/all", {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='S').count())

        rsp = self.apiGet("reviewrequests/all", {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='D').count())

        rsp = self.apiGet("reviewrequests/all", {'status': 'all'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status=None).count())

    def testReviewRequestListCount(self):
        """Testing the deprecated reviewrequests/all/count API"""
        rsp = self.apiGet("reviewrequests/all/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], ReviewRequest.objects.public().count())

    def testReviewRequestsToGroup(self):
        """Testing the deprecated reviewrequests/to/group API"""
        rsp = self.apiGet("reviewrequests/to/group/devgroup")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_group("devgroup").count())

    def testReviewRequestsToGroupWithStatus(self):
        """Testing the deprecated reviewrequests/to/group API with custom status"""
        rsp = self.apiGet("reviewrequests/to/group/devgroup",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", status='S').count())

        rsp = self.apiGet("reviewrequests/to/group/devgroup",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", status='D').count())

    def testReviewRequestsToGroupCount(self):
        """Testing the deprecated reviewrequests/to/group/count API"""
        rsp = self.apiGet("reviewrequests/to/group/devgroup/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_group("devgroup").count())

    def testReviewRequestsToUser(self):
        """Testing the deprecated reviewrequests/to/user API"""
        rsp = self.apiGet("reviewrequests/to/user/grumpy")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user("grumpy").count())

    def testReviewRequestsToUserWithStatus(self):
        """Testing the deprecated reviewrequests/to/user API with custom status"""
        rsp = self.apiGet("reviewrequests/to/user/grumpy",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='S').count())

        rsp = self.apiGet("reviewrequests/to/user/grumpy",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='D').count())

    def testReviewRequestsToUserCount(self):
        """Testing the deprecated reviewrequests/to/user/count API"""
        rsp = self.apiGet("reviewrequests/to/user/grumpy/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user("grumpy").count())

    def testReviewRequestsToUserDirectly(self):
        """Testing the deprecated reviewrequests/to/user/directly API"""
        rsp = self.apiGet("reviewrequests/to/user/doc/directly")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user_directly("doc").count())

    def testReviewRequestsToUserDirectlyWithStatus(self):
        """Testing the deprecated reviewrequests/to/user/directly API with custom status"""
        rsp = self.apiGet("reviewrequests/to/user/doc/directly",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='S').count())

        rsp = self.apiGet("reviewrequests/to/user/doc/directly",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='D').count())

    def testReviewRequestsToUserDirectlyCount(self):
        """Testing the deprecated reviewrequests/to/user/directly/count API"""
        rsp = self.apiGet("reviewrequests/to/user/doc/directly/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user_directly("doc").count())

    def testReviewRequestsFromUser(self):
        """Testing the deprecated reviewrequests/from/user API"""
        rsp = self.apiGet("reviewrequests/from/user/grumpy")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.from_user("grumpy").count())

    def testReviewRequestsFromUserWithStatus(self):
        """Testing the deprecated reviewrequests/from/user API with custom status"""
        rsp = self.apiGet("reviewrequests/from/user/grumpy",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='S').count())

        rsp = self.apiGet("reviewrequests/from/user/grumpy",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='D').count())

    def testReviewRequestsFromUserCount(self):
        """Testing the deprecated reviewrequests/from/user/count API"""
        rsp = self.apiGet("reviewrequests/from/user/grumpy/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.from_user("grumpy").count())

    def testNewReviewRequest(self):
        """Testing the deprecated reviewrequests/new API"""
        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': self.repository.path,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['repository']['id'],
                         self.repository.id)

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        return ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def testNewReviewRequestWithInvalidRepository(self):
        """Testing the deprecated reviewrequests/new API with Invalid Repository error"""
        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': 'gobbledygook',
        })
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    def testNewReviewRequestAsUser(self):
        """Testing the deprecated reviewrequests/new API with submit_as"""
        self.user.is_superuser = True
        self.user.save()

        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': self.repository.path,
            'submit_as': 'doc',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['repository']['id'],
                         self.repository.id)
        self.assertEqual(rsp['review_request']['submitter']['username'], 'doc')

        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def testNewReviewRequestAsUserPermissionDenied(self):
        """Testing the deprecated reviewrequests/new API with submit_as and Permission Denied error"""
        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': self.repository.path,
            'submit_as': 'doc',
        })
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def testReviewRequest(self):
        """Testing the deprecated reviewrequests/<id> API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiGet("reviewrequests/%s" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    def testReviewRequestPermissionDenied(self):
        """Testing the deprecated reviewrequests/<id> API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=False).\
            exclude(submitter=self.user)[0]
        rsp = self.apiGet("reviewrequests/%s" % review_request.id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def testReviewRequestByChangenum(self):
        """Testing the deprecated reviewrequests/repository/changenum API"""
        review_request = \
            ReviewRequest.objects.filter(changenum__isnull=False)[0]
        rsp = self.apiGet("reviewrequests/repository/%s/changenum/%s" %
                          (review_request.repository.id,
                           review_request.changenum))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)
        self.assertEqual(rsp['review_request']['changenum'],
                         review_request.changenum)

    def testReviewRequestStar(self):
        """Testing the deprecated reviewrequests/star API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiGet("reviewrequests/%s/star" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(review_request in
                     self.user.get_profile().starred_review_requests.all())

    def testReviewRequestStarDoesNotExist(self):
        """Testing the deprecated reviewrequests/star API with Does Not Exist error"""
        rsp = self.apiGet("reviewrequests/999/star")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testReviewRequestUnstar(self):
        """Testing the deprecated reviewrequests/unstar API"""
        # First, star it.
        self.testReviewRequestStar()

        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiGet("reviewrequests/%s/unstar" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(review_request not in
                     self.user.get_profile().starred_review_requests.all())

    def testReviewRequestUnstarWithDoesNotExist(self):
        """Testing the deprecated reviewrequests/unstar API with Does Not Exist error"""
        rsp = self.apiGet("reviewrequests/999/unstar")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testReviewRequestDelete(self):
        """Testing the deprecated reviewrequests/delete API"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assert_(self.user.has_perm('reviews.delete_reviewrequest'))

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiGet("reviewrequests/%s/delete" % review_request_id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertRaises(ReviewRequest.DoesNotExist,
                          ReviewRequest.objects.get, pk=review_request_id)

    def testReviewRequestDeletePermissionDenied(self):
        """Testing the deprecated reviewrequests/delete API with Permission Denied error"""
        review_request_id = \
            ReviewRequest.objects.exclude(submitter=self.user)[0].id
        rsp = self.apiGet("reviewrequests/%s/delete" % review_request_id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def testReviewRequestDeleteDoesNotExist(self):
        """Testing the deprecated reviewrequests/delete API with Does Not Exist error"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assert_(self.user.has_perm('reviews.delete_reviewrequest'))

        rsp = self.apiGet("reviewrequests/999/delete")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testReviewRequestDraftSet(self):
        """Testing the deprecated reviewrequests/draft/set API"""
        summary = "My Summary"
        description = "My Description"
        testing_done = "My Testing Done"
        branch = "My Branch"
        bugs = ""

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/set" % review_request_id, {
            'summary': summary,
            'description': description,
            'testing_done': testing_done,
            'branch': branch,
            'bugs_closed': bugs,
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['summary'], summary)
        self.assertEqual(rsp['draft']['description'], description)
        self.assertEqual(rsp['draft']['testing_done'], testing_done)
        self.assertEqual(rsp['draft']['branch'], branch)
        self.assertEqual(rsp['draft']['bugs_closed'], [])

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertEqual(draft.summary, summary)
        self.assertEqual(draft.description, description)
        self.assertEqual(draft.testing_done, testing_done)
        self.assertEqual(draft.branch, branch)
        self.assertEqual(draft.get_bug_list(), [])

    def testReviewRequestDraftSetField(self):
        """Testing the deprecated reviewrequests/draft/set/<field> API"""
        bugs_closed = '123,456'
        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/set/bugs_closed" %
                           review_request_id, {
            'value': bugs_closed,
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['bugs_closed'], bugs_closed.split(","))

    def testReviewRequestDraftSetFieldInvalidName(self):
        """Testing the deprecated reviewrequests/draft/set/<field> API with invalid name"""
        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/set/foobar" %
                           review_request_id, {
            'value': 'foo',
        })

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_ATTRIBUTE.code)
        self.assertEqual(rsp['attribute'], 'foobar')

    def testReviewRequestPublishSendsEmail(self):
        """Testing the deprecated reviewrequests/publish API"""
        # Set some data first.
        self.testReviewRequestDraftSet()

        review_request = ReviewRequest.objects.from_user(self.user.username)[0]

        rsp = self.apiPost("reviewrequests/%s/publish" % review_request.id)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(mail.outbox), 1)

    def testReviewRequestDraftSetFieldNoPermission(self):
        """Testing the deprecated reviewrequests/draft/set/<field> API without valid permissions"""
        bugs_closed = '123,456'
        review_request_id = ReviewRequest.objects.from_user('admin')[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/set/bugs_closed" %
                           review_request_id, {
            'value': bugs_closed,
        })

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    # draft/save is deprecated. Tests were copied to *DraftPublish*().
    # This is still here only to make sure we don't break backwards
    # compatibility.
    def testReviewRequestDraftSave(self):
        """Testing the deprecated reviewrequests/draft/save API"""
        # Set some data first.
        self.testReviewRequestDraftSet()

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request_id)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request_id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")

    def testReviewRequestDraftSaveDoesNotExist(self):
        """Testing the deprecated reviewrequests/draft/save API with Does Not Exist error"""
        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request_id)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testReviewRequestDraftPublish(self):
        """Testing the deprecated reviewrequests/draft/publish API"""
        # Set some data first.
        self.testReviewRequestDraftSet()

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/publish" % review_request_id)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request_id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Review Request: My Summary")
        self.assertValidRecipients(["doc", "grumpy"], [])


    def testReviewRequestDraftPublishDoesNotExist(self):
        """Testing the deprecated reviewrequests/draft/publish API with Does Not Exist error"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]
        rsp = self.apiPost("reviewrequests/%s/draft/publish" %
                           review_request.id)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testReviewRequestDraftDiscard(self):
        """Testing the deprecated reviewrequests/draft/discard API"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]
        summary = review_request.summary
        description = review_request.description

        # Set some data.
        self.testReviewRequestDraftSet()

        rsp = self.apiPost("reviewrequests/%s/draft/discard" %
                           review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    def testReviewDraftSave(self):
        """Testing the deprecated reviewrequests/reviews/draft/save API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp = self.apiPost("reviewrequests/%s/reviews/draft/save" %
                           review_request.id, {
            'shipit': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, False)

        self.assertEqual(len(mail.outbox), 0)

    def testReviewDraftPublish(self):
        """Testing the deprecated reviewrequests/reviews/draft/publish API"""
        body_top = "My Body Top"
        body_bottom = ""
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp = self.apiPost("reviewrequests/%s/reviews/draft/publish" %
                           review_request.id, {
            'shipit': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, True)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         "Re: Review Request: Interdiff Revision Test")
        self.assertValidRecipients(["admin", "grumpy"], [])


    def testReviewDraftDelete(self):
        """Testing the deprecated reviewrequests/reviews/draft/delete API"""
        # Set up the draft to delete.
        self.testReviewDraftSave()

        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiPost("reviewrequests/%s/reviews/draft/delete" %
                           review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(review_request.reviews.count(), 0)

    def testReviewDraftDeleteDoesNotExist(self):
        """Testing the deprecated reviewrequests/reviews/draft/delete API with Does Not Exist error"""
        # Set up the draft to delete
        self.testReviewDraftPublish()

        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiPost("reviewrequests/%s/reviews/draft/delete" %
                           review_request.id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    def testReviewDraftComments(self):
        """Testing the deprecated reviewrequests/reviews/draft/comments API"""
        diff_comment_text = "Test diff comment"
        screenshot_comment_text = "Test screenshot comment"
        x, y, w, h = 2, 2, 10, 10

        screenshot = self.testNewScreenshot()
        review_request = screenshot.review_request.get()
        diffset = self.testNewDiff(review_request)
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        self.postNewDiffComment(review_request, diff_comment_text)
        self.postNewScreenshotComment(review_request, screenshot,
                                      screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet("reviewrequests/%s/reviews/draft/comments" %
                          review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], diff_comment_text)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)

    def testReviewsList(self):
        """Testing the deprecated reviewrequests/reviews API"""
        review_request = Review.objects.all()[0].review_request
        rsp = self.apiGet("reviewrequests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['reviews']), review_request.reviews.count())

    def testReviewsListCount(self):
        """Testing the deprecated reviewrequests/reviews/count API"""
        review_request = Review.objects.all()[0].review_request
        rsp = self.apiGet("reviewrequests/%s/reviews/count" %
                          review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['reviews'], review_request.reviews.count())

    def testReviewCommentsList(self):
        """Testing the deprecated reviewrequests/reviews/comments API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/comments" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), review.comments.count())

    def testReviewCommentsCount(self):
        """Testing the deprecated reviewrequests/reviews/comments/count API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/comments/count" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.comments.count())

    def testReplyDraftComment(self):
        """Testing the deprecated reviewrequests/reviews/replies/draft API with comment"""
        comment_text = "My Comment Text"

        comment = Comment.objects.all()[0]
        review = comment.review.get()

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'comment',
            'id': comment.id,
            'value': comment_text
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def testReplyDraftScreenshotComment(self):
        """Testing the deprecated reviewrequests/reviews/replies/draft API with screenshot_comment"""
        comment_text = "My Comment Text"

        comment = self.testScreenshotCommentsSet()
        review = comment.review.get()

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'screenshot_comment',
            'id': comment.id,
            'value': comment_text,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def testReplyDraftBodyTop(self):
        """Testing the deprecated reviewrequests/reviews/replies/draft API with body_top"""
        body_top = 'My Body Top'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_top',
            'value': body_top,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_top, body_top)

    def testReplyDraftBodyBottom(self):
        """Testing the deprecated reviewrequests/reviews/replies/draft API with body_bottom"""
        body_bottom = 'My Body Bottom'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_bottom',
            'value': body_bottom,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_bottom, body_bottom)

    def testReplyDraftSave(self):
        """Testing the deprecated reviewrequests/reviews/replies/draft/save API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_top',
            'value': 'Test',
        })

        self.assertEqual(rsp['stat'], 'ok')
        reply_id = rsp['reply']['id']

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft/save" %
                           (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=reply_id)
        self.assertEqual(reply.public, True)

        self.assertEqual(len(mail.outbox), 1)

    def testReplyDraftDiscard(self):
        """Testing the deprecated reviewrequests/reviews/replies/draft/discard API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_top',
            'value': 'Test',
        })

        self.assertEqual(rsp['stat'], 'ok')
        reply_id = rsp['reply']['id']

        rsp = self.apiPost(
            "reviewrequests/%s/reviews/%s/replies/draft/discard" %
            (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(Review.objects.filter(pk=reply_id).count(), 0)

    def testRepliesList(self):
        """Testing the deprecated reviewrequests/reviews/replies API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.testReplyDraftSave()

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/replies" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), len(review.public_replies()))

        for reply in review.public_replies():
            self.assertEqual(rsp['replies'][0]['id'], reply.id)
            self.assertEqual(rsp['replies'][0]['body_top'], reply.body_top)
            self.assertEqual(rsp['replies'][0]['body_bottom'],
                             reply.body_bottom)

    def testRepliesListCount(self):
        """Testing the deprecated reviewrequests/reviews/replies/count API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.testReplyDraftSave()

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/replies/count" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], len(review.public_replies()))

    def testNewDiff(self, review_request=None):
        """Testing the deprecated reviewrequests/diff/new API"""

        if review_request is None:
            review_request = self.testNewReviewRequest()

        diff_filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scmtools", "testdata", "svn_makefile.diff")
        f = open(diff_filename, "r")
        rsp = self.apiPost("reviewrequests/%s/diff/new" % review_request.id, {
            'path': f,
            'basedir': "/trunk",
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        # Return this so it can be used in other tests.
        return DiffSet.objects.get(pk=rsp['diffset_id'])

    def testNewDiffInvalidFormData(self):
        """Testing the deprecated reviewrequests/diff/new API with Invalid Form Data"""
        review_request = self.testNewReviewRequest()

        rsp = self.apiPost("reviewrequests/%s/diff/new" % review_request.id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assert_('path' in rsp['fields'])
        self.assert_('basedir' in rsp['fields'])

    def testNewScreenshot(self):
        """Testing the deprecated reviewrequests/screenshot/new API"""
        review_request = self.testNewReviewRequest()

        f = open(self.__getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost("reviewrequests/%s/screenshot/new" %
                           review_request.id, {
            'path': f,
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        # Return the screenshot so we can use it in other tests.
        return Screenshot.objects.get(pk=rsp['screenshot_id'])

    def testNewScreenshotPermissionDenied(self):
        """Testing the deprecated reviewrequests/screenshot/new API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True).\
            exclude(submitter=self.user)[0]

        f = open(self.__getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost("reviewrequests/%s/screenshot/new" %
                           review_request.id, {
            'caption': 'Trophy',
            'path': f,
        })
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def postNewDiffComment(self, review_request, comment_text):
        """Utility function for posting a new diff comment."""
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s/file/%s/line/%s/comments" %
            (review_request.id, diffset.revision, filediff.id, 10),
            {
                'action': 'set',
                'text': comment_text,
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def testReviewRequestDiffsets(self):
        """Testing the deprecated reviewrequests/diffsets API"""
        rsp = self.apiGet("reviewrequests/2/diff")

        self.assertEqual(rsp['diffsets'][0]["id"], 2)
        self.assertEqual(rsp['diffsets'][0]["name"], 'cleaned_data.diff')

    def testDiffCommentsSet(self):
        """Testing the deprecated reviewrequests/diff/file/line/comments set API"""
        comment_text = "This is a test comment."

        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []

        rsp = self.postNewDiffComment(review_request, comment_text)

        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], comment_text)

    def testDiffCommentsDelete(self):
        """Testing the deprecated reviewrequests/diff/file/line/comments delete API"""
        comment_text = "This is a test comment."

        self.testDiffCommentsSet()

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s/file/%s/line/%s/comments" %
            (review_request.id, diffset.revision, filediff.id, 10),
            {
                'action': 'delete',
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testDiffCommentsList(self):
        """Testing the deprecated reviewrequests/diff/file/line/comments list API"""
        self.testDiffCommentsSet()

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiGet(
            "reviewrequests/%s/diff/%s/file/%s/line/%s/comments" %
            (review_request.id, diffset.revision, filediff.id, 10))

        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['comments']), comments.count())

        for i in range(0, len(rsp['comments'])):
            self.assertEqual(rsp['comments'][i]['text'], comments[i].text)


    def testInterDiffCommentsSet(self):
        """Testing the deprecated reviewrequests/diff/file/line/comments interdiff set API"""
        comment_text = "This is a test comment."

        # Create a review request for this test.
        review_request = self.testNewReviewRequest()

        # Upload the first diff and publish the draft.
        diffset_id = self.testNewDiff(review_request).id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        # Upload the second diff and publish the draft.
        interdiffset_id = self.testNewDiff(review_request).id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        # Reload the diffsets, now that they've been modified.
        diffset = DiffSet.objects.get(pk=diffset_id)
        interdiffset = DiffSet.objects.get(pk=interdiffset_id)

        # Get the interdiffs
        filediff = diffset.files.all()[0]
        interfilediff = interdiffset.files.all()[0]

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s-%s/file/%s-%s/line/%s/comments" %
            (review_request.id, diffset.revision, interdiffset.revision,
             filediff.id, interfilediff.id, 10),
            {
                'action': 'set',
                'text': comment_text,
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], comment_text)

        # Return some information for use in other tests.
        return (review_request, diffset, interdiffset, filediff, interfilediff)

    def testInterDiffCommentsDelete(self):
        """Testing the deprecated reviewrequests/diff/file/line/comments interdiff delete API"""
        comment_text = "This is a test comment."

        review_request, diffset, interdiffset, filediff, interfilediff = \
            self.testInterDiffCommentsSet()

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s-%s/file/%s-%s/line/%s/comments" %
            (review_request.id, diffset.revision, interdiffset.revision,
             filediff.id, interfilediff.id, 10),
            {
                'action': 'delete',
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testInterDiffCommentsList(self):
        """Testing the deprecated reviewrequests/diff/file/line/comments interdiff list API"""
        review_request, diffset, interdiffset, filediff, interfilediff = \
            self.testInterDiffCommentsSet()

        rsp = self.apiGet(
            "reviewrequests/%s/diff/%s-%s/file/%s-%s/line/%s/comments" %
            (review_request.id, diffset.revision, interdiffset.revision,
             filediff.id, interfilediff.id, 10))

        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff,
                                          interfilediff=interfilediff)
        self.assertEqual(len(rsp['comments']), comments.count())

        for i in range(0, len(rsp['comments'])):
            self.assertEqual(rsp['comments'][i]['text'], comments[i].text)

    def postNewScreenshotComment(self, review_request, screenshot,
                                 comment_text, x, y, w, h):
        """Utility function for posting a new screenshot comment."""
        rsp = self.apiPost(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, w, h, x, y),
            {
                'action': 'set',
                'text': comment_text,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        return rsp

    def testScreenshotCommentsSet(self):
        """Testing the deprecated reviewrequests/s/comments set API"""
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        screenshot = self.testNewScreenshot()
        review_request = screenshot.review_request.get()

        rsp = self.postNewScreenshotComment(review_request, screenshot,
                                            comment_text, x, y, w, h)

        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], comment_text)
        self.assertEqual(rsp['comments'][0]['x'], x)
        self.assertEqual(rsp['comments'][0]['y'], y)
        self.assertEqual(rsp['comments'][0]['w'], w)
        self.assertEqual(rsp['comments'][0]['h'], h)

        # Return this so it can be used in other tests.
        return ScreenshotComment.objects.get(pk=rsp['comments'][0]['id'])

    def testScreenshotCommentsDelete(self):
        """Testing the deprecated reviewrequests/s/comments delete API"""
        comment = self.testScreenshotCommentsSet()
        screenshot = comment.screenshot
        review_request = screenshot.review_request.get()

        rsp = self.apiPost(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, comment.w, comment.h,
             comment.x, comment.y),
            {
                'action': 'delete',
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testScreenshotCommentsDeleteNonExistant(self):
        """Testing the deprecated reviewrequests/s/comments delete API with non-existant comment"""
        comment = self.testScreenshotCommentsSet()
        screenshot = comment.screenshot
        review_request = screenshot.review_request.get()

        rsp = self.apiPost(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, 1, 2, 3, 4),
            {
                'action': 'delete',
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testScreenshotCommentsList(self):
        """Testing the deprecated reviewrequests/s/comments list API"""
        comment = self.testScreenshotCommentsSet()
        screenshot = comment.screenshot
        review_request = screenshot.review_request.get()

        rsp = self.apiGet(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, comment.w, comment.h,
             comment.x, comment.y))

        self.assertEqual(rsp['stat'], 'ok')

        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
        self.assertEqual(len(rsp['comments']), comments.count())

        for i in range(0, len(rsp['comments'])):
            self.assertEqual(rsp['comments'][i]['text'], comments[i].text)
            self.assertEqual(rsp['comments'][i]['x'], comments[i].x)
            self.assertEqual(rsp['comments'][i]['y'], comments[i].y)
            self.assertEqual(rsp['comments'][i]['w'], comments[i].w)
            self.assertEqual(rsp['comments'][i]['h'], comments[i].h)

    def __getTrophyFilename(self):
        return os.path.join(settings.HTDOCS_ROOT,
                            "media", "rb", "images", "trophy.png")
