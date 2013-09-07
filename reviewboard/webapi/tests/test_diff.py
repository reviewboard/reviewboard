import os

from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard import scmtools
from reviewboard.diffviewer.models import DiffSet
from reviewboard.webapi.errors import DIFF_TOO_BIG
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (diff_item_mimetype,
                                                diff_list_mimetype)
from reviewboard.webapi.tests.urls import (get_diff_item_url,
                                           get_diff_list_url)


class DiffResourceTests(BaseWebAPITestCase):
    """Testing the DiffResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_post_diffs(self):
        """Testing the POST review-requests/<id>/diffs/ API"""
        repository = self.create_repository(tool_name='Subversion')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user)

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")
        rsp = self.apiPost(
            get_diff_list_url(review_request),
            {
                'path': f,
                'basedir': '/trunk',
                'base_commit_id': '1234',
            },
            expected_mimetype=diff_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['basedir'], '/trunk')
        self.assertEqual(rsp['diff']['base_commit_id'], '1234')

        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        self.assertEqual(diffset.basedir, '/trunk')
        self.assertEqual(diffset.base_commit_id, '1234')

    def test_post_diffs_with_missing_data(self):
        """Testing the POST review-requests/<id>/diffs/ API with Invalid Form Data"""
        repository = self.create_repository(tool_name='Subversion')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user)

        rsp = self.apiPost(get_diff_list_url(review_request),
                           expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('path' in rsp['fields'])

        # Now test with a valid path and an invalid basedir.
        # This is necessary because basedir is "optional" as defined by
        # the resource, but may be required by the form that processes the
        # diff.
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user)

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")
        rsp = self.apiPost(
            get_diff_list_url(review_request),
            {'path': f},
            expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('basedir' in rsp['fields'])

    def test_post_diffs_too_big(self):
        """Testing the POST review-requests/<id>/diffs/ API with diff exceeding max size"""
        repository = self.create_repository()

        self.siteconfig.set('diffviewer_max_diff_size', 2)
        self.siteconfig.save()

        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user)

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")

        rsp = self.apiPost(
            get_diff_list_url(review_request),
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
        user = self._login_user(local_site=True)

        repository = self.create_repository(with_local_site=True,
                                            tool_name='Subversion')

        review_request = self.create_review_request(
            with_local_site=True,
            repository=repository,
            submitter=user)

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, 'r')
        rsp = self.apiPost(
            get_diff_list_url(review_request, self.local_site_name),
            {
                'path': f,
                'basedir': '/trunk',
            },
            expected_mimetype=diff_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['name'], 'svn_makefile.diff')

    def test_get_diffs(self):
        """Testing the GET review-requests/<id>/diffs/ API"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        rsp = self.apiGet(get_diff_list_url(review_request),
                          expected_mimetype=diff_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diffs'][0]['id'], diffset.pk)
        self.assertEqual(rsp['diffs'][0]['name'], diffset.name)

    @add_fixtures(['test_site'])
    def test_get_diffs_with_site(self):
        """Testing the GET review-requests/<id>/diffs API with a local site"""
        review_request = self.create_review_request(create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        self._login_user(local_site=True)

        rsp = self.apiGet(get_diff_list_url(review_request,
                                            self.local_site_name),
                          expected_mimetype=diff_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diffs'][0]['id'], diffset.pk)
        self.assertEqual(rsp['diffs'][0]['name'], diffset.name)

    @add_fixtures(['test_site'])
    def test_get_diffs_with_site_no_access(self):
        """Testing the GET review-requests/<id>/diffs API with a local site and Permission Denied error"""
        review_request = self.create_review_request(create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        self.create_diffset(review_request)

        self.apiGet(get_diff_list_url(review_request, self.local_site_name),
                    expected_status=403)

    def test_get_diff(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        rsp = self.apiGet(get_diff_item_url(review_request, diffset.revision),
                          expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['id'], diffset.pk)
        self.assertEqual(rsp['diff']['name'], diffset.name)

    @add_fixtures(['test_site'])
    def test_get_diff_with_site(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API with a local site"""
        review_request = self.create_review_request(create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        self._login_user(local_site=True)

        rsp = self.apiGet(get_diff_item_url(review_request, diffset.revision,
                                            self.local_site_name),
                          expected_mimetype=diff_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['diff']['id'], diffset.id)
        self.assertEqual(rsp['diff']['name'], diffset.name)

    def test_get_diff_not_modified(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API with Not Modified response"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        self._testHttpCaching(
            get_diff_item_url(review_request, diffset.revision),
            check_last_modified=True)

    @add_fixtures(['test_site'])
    def test_get_diff_with_site_no_access(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API with a local site and Permission Denied error"""
        review_request = self.create_review_request(create_repository=True,
                                                    with_local_site=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        self.apiGet(get_diff_item_url(review_request, diffset.revision,
                                      self.local_site_name),
                    expected_status=403)
