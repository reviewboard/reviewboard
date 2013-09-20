import os

from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard import scmtools
from reviewboard.webapi.errors import DIFF_PARSE_ERROR, REPO_FILE_NOT_FOUND
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import validate_diff_mimetype
from reviewboard.webapi.tests.urls import get_validate_diff_url


class ResourceTests(BaseWebAPITestCase):
    """Testing the ValidateDiffResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    #
    # HTTP POST tests
    #

    def test_post(self):
        """Testing the POST validation/diffs/ API"""
        repository = self.create_repository(tool_name='Test')

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'git_readme.diff')
        f = open(diff_filename, "r")

        self.apiPost(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': f,
                'basedir': '/trunk',
            },
            expected_status=200,
            expected_mimetype=validate_diff_mimetype)

        f.close()

    def test_post_with_missing_basedir(self):
        """Testing the POST validations/diffs/ API with a missing basedir"""
        repository = self.create_repository(tool_name='Test')

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'git_readme.diff')
        f = open(diff_filename, 'r')

        rsp = self.apiPost(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': f,
            },
            expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertTrue('basedir' in rsp['fields'])

    def test_post_with_files_not_found(self):
        """Testing the POST validation/diffs/ API
        with source files not found
        """
        repository = self.create_repository(tool_name='Test')

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'git_file_not_found.diff')
        f = open(diff_filename, 'r')

        rsp = self.apiPost(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': f,
                'basedir': '',
            },
            expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_FILE_NOT_FOUND.code)
        self.assertEqual(rsp['file'], 'missing-file')
        self.assertEqual(rsp['revision'], 'd6613f0')

    def test_post_with_parse_error(self):
        """Testing the POST validation/diffs/ API with a malformed diff file"""
        repository = self.create_repository(tool_name='Test')

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'stunnel.pem')
        f = open(diff_filename, 'r')
        rsp = self.apiPost(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': f,
                'basedir': '/trunk',
            },
            expected_status=400)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_PARSE_ERROR.code)
        self.assertEqual(rsp['reason'],
                         'This does not appear to be a git diff')
        self.assertEqual(rsp['linenum'], 0)
