import os

from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard import scmtools
from reviewboard.webapi.errors import DIFF_PARSE_ERROR, REPO_FILE_NOT_FOUND
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import validate_diff_mimetype
from reviewboard.webapi.tests.urls import get_validate_diff_url


class ValidateDiffResourceTests(BaseWebAPITestCase):
    """Testing the ValidateDiffResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_post_diff(self):
        """Testing the POST validation/diffs/ API"""
        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, "r")

        self.apiPost(
            get_validate_diff_url(),
            {
                'repository': self.repository.pk,
                'path': f,
                'basedir': '/trunk',
            },
            expected_status=200,
            expected_mimetype=validate_diff_mimetype)

        f.close()

    def test_post_diff_with_missing_basedir(self):
        """Testing the POST validations/diffs/ API with a missing basedir"""
        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'svn_makefile.diff')
        f = open(diff_filename, 'r')

        rsp = self.apiPost(
            get_validate_diff_url(),
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
            get_validate_diff_url(),
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
            get_validate_diff_url(),
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
