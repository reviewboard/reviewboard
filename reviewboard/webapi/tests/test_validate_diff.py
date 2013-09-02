import os

from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard import scmtools
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.errors import DIFF_PARSE_ERROR, REPO_FILE_NOT_FOUND
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype


class ValidateDiffResourceTests(BaseWebAPITestCase):
    """Testing the ValidateDiffResource APIs."""
    fixtures = ['test_users', 'test_scmtools']
    mimetype = _build_mimetype('diff-validation')

    def test_post_diff(self):
        """Testing the POST validation/diffs/ API"""
        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")

        self.apiPost(
            self.get_url(),
            {
                'repository': self.repository.pk,
                'path': f,
                'basedir': '/trunk',
            },
            expected_status=200,
            expected_mimetype=ValidateDiffResourceTests.mimetype)

        f.close()

    def test_post_diff_with_missing_basedir(self):
        """Testing the POST validations/diffs/ API with a missing basedir"""
        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, 'r')

        rsp = self.apiPost(
            self.get_url(),
            {
                'repository': self.repository.pk,
                'path': f,
            },
            expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('basedir' in rsp['fields'])

    def test_post_diff_with_files_not_found(self):
        """Testing the POST validation/diffs/ API with source files not found"""
        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_file_not_found.diff')
        f = open(diff_filename, 'r')

        rsp = self.apiPost(
            self.get_url(),
            {
                'repository': self.repository.pk,
                'path': f,
                'basedir': '/trunk',
            },
            expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_FILE_NOT_FOUND.code)
        self.assertEqual(rsp['file'], '/trunk/doc/misc-docs/Makefile2')
        self.assertEqual(rsp['revision'], '4')

    def test_post_diff_with_parse_error(self):
        """Testing the POST validation/diffs/ API with a malformed diff file"""
        # Post a git diff against the svn repository
        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'git_complex.diff')
        f = open(diff_filename, 'r')
        rsp = self.apiPost(
            self.get_url(),
            {
                'repository': self.repository.pk,
                'path': f,
                'basedir': '/trunk',
            },
            expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_PARSE_ERROR.code)
        self.assertEqual(
            rsp['reason'],
            'No valid separator after the filename was found in the diff header')
        self.assertEqual(rsp['linenum'], 2)

    def get_url(self, local_site_name=None):
        return local_site_reverse('validate-diffs-resource',
                                  local_site_name=local_site_name)
