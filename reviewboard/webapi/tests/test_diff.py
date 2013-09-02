import os

from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard import scmtools
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.errors import DIFF_TOO_BIG
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


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

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")
        rsp = self.apiPost(
            rsp['review_request']['links']['diffs']['href'],
            {
                'path': f,
                'basedir': '/trunk',
                'base_commit_id': '1234',
            },
            expected_mimetype=self.item_mimetype)
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

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")
        rsp = self.apiPost(
            rsp['review_request']['links']['diffs']['href'],
            {'path': f},
            expected_status=400)
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

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")

        rsp = self.apiPost(
            rsp['review_request']['links']['diffs']['href'],
            {
                'path': f,
                'basedir': "/trunk",
            },
            expected_status=400)

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

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, 'r')
        rsp = self.apiPost(
            rsp['review_request']['links']['diffs']['href'],
            {
                'path': f,
                'basedir': '/trunk',
            },
            expected_mimetype=self.item_mimetype)
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
