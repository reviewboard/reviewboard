from __future__ import unicode_literals

import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import six
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import INVALID_FORM_DATA
from djblets.webapi.testing.decorators import webapi_test_template
from kgb import SpyAgency

from reviewboard import scmtools
from reviewboard.diffviewer.models import DiffSet
from reviewboard.webapi.errors import (DIFF_PARSE_ERROR, INVALID_REPOSITORY,
                                       REPO_FILE_NOT_FOUND)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import validate_diff_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_validate_diff_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(SpyAgency, BaseWebAPITestCase):
    """Testing the ValidateDiffResource APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'validation/diffs/'
    test_http_methods = ('DELETE', 'PUT',)
    resource = resources.validate_diff

    VALID_GIT_DIFF = (
        b'diff --git a/readme b/readme'
        b'index d6613f5..5b50866 100644'
        b'--- a/readme'
        b'+++ b/readme'
        b'@@ -1 +1,3 @@'
        b' Hello there'
        b'+'
        b'+Oh hi!'
    )

    def setup_http_not_allowed_item_test(self, user):
        return get_validate_diff_url()

    #
    # HTTP GET tests
    #

    def test_get(self):
        """Testing the GET validation/diffs/ API"""
        self.api_get(get_validate_diff_url(),
                     expected_mimetype=validate_diff_mimetype)

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET validation/diffs/ API with access to local site"""
        self._login_user(local_site=True)

        self.api_get(get_validate_diff_url(self.local_site_name),
                     expected_mimetype=validate_diff_mimetype)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET validation/diffs/ API
        without access to local site
        """
        self.api_get(get_validate_diff_url(self.local_site_name),
                     expected_status=403)

    #
    # HTTP POST tests
    #

    def test_post(self):
        """Testing the POST validation/diffs/ API"""
        repository = self.create_repository(tool_name='Test')

        diff = SimpleUploadedFile('readme.diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        self.api_post(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': diff,
                'basedir': '/trunk',
            },
            expected_status=200,
            expected_mimetype=validate_diff_mimetype)

    @add_fixtures(['test_site'])
    def test_post_with_site(self):
        """Testing the POST validation/diffs/ API
        with access to a local site
        """
        repository = self.create_repository(with_local_site=True,
                                            tool_name='Test')

        self._login_user(local_site=True)

        diff = SimpleUploadedFile('readme.diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')
        self.api_post(
            get_validate_diff_url(self.local_site_name),
            {
                'repository': repository.pk,
                'path': diff,
                'basedir': '/trunk',
            },
            expected_status=200,
            expected_mimetype=validate_diff_mimetype)

    @add_fixtures(['test_site'])
    def test_post_with_site_no_access(self):
        """Testing the POST validation/diffs/ API
        without access to a local site
        """
        repository = self.create_repository(with_local_site=True,
                                            tool_name='Test')

        diff = SimpleUploadedFile('readme.diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')
        self.api_post(
            get_validate_diff_url(self.local_site_name),
            {
                'repository': repository.pk,
                'path': diff,
                'basedir': '/trunk',
            },
            expected_status=403)

    def test_post_with_base_commit_id(self):
        """Testing the POST validation/diffs/ API with base_commit_id"""
        self.spy_on(DiffSet.objects.create_from_upload, call_original=True)

        repository = self.create_repository(tool_name='Test')

        diff = SimpleUploadedFile('readme.diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        self.api_post(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': diff,
                'basedir': '/trunk',
                'base_commit_id': '1234',
            },
            expected_status=200,
            expected_mimetype=validate_diff_mimetype)

        last_call = DiffSet.objects.create_from_upload.last_call
        self.assertEqual(last_call.kwargs.get('base_commit_id'), '1234')

    def test_post_with_missing_basedir(self):
        """Testing the POST validations/diffs/ API with a missing basedir"""
        repository = self.create_repository(tool_name='Test')

        diff = SimpleUploadedFile('readme.diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')
        rsp = self.api_post(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': diff,
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertIn('basedir', rsp['fields'])

    def test_post_with_files_not_found(self):
        """Testing the POST validation/diffs/ API
        with source files not found
        """
        repository = self.create_repository(tool_name='Test')

        diff = SimpleUploadedFile('readme.diff',
                                  self.DEFAULT_GIT_FILE_NOT_FOUND_DIFF,
                                  content_type='text/x-patch')
        rsp = self.api_post(
            get_validate_diff_url(),
            {
                'repository': repository.pk,
                'path': diff,
                'basedir': '',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], REPO_FILE_NOT_FOUND.code)
        self.assertEqual(rsp['file'], 'missing-file')
        self.assertEqual(rsp['revision'], 'd6613f0')

    def test_post_with_parse_error(self):
        """Testing the POST validation/diffs/ API with a malformed diff file"""
        repository = self.create_repository(tool_name='Test')

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'stunnel.pem')

        with open(diff_filename, 'rb') as f:
            rsp = self.api_post(
                get_validate_diff_url(),
                {
                    'repository': repository.pk,
                    'path': f,
                    'basedir': '/trunk',
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_PARSE_ERROR.code)
        self.assertEqual(rsp['reason'],
                         'This does not appear to be a git diff')
        self.assertEqual(rsp['linenum'], 0)

    def test_post_with_conflicting_repos(self):
        """Testing the POST validations/diffs/ API with conflicting
        repositories
        """
        repository = self.create_repository(tool_name='Test')
        self.create_repository(tool_name='Test',
                               name='Test 2',
                               path='blah',
                               mirror_path=repository.path)

        diff = SimpleUploadedFile('readme.diff', self.VALID_GIT_DIFF,
                                  content_type='text/x-patch')
        rsp = self.api_post(
            get_validate_diff_url(),
            {
                'repository': repository.path,
                'path': diff,
                'basedir': '/trunk',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)
        self.assertEqual(rsp['err']['msg'],
                         'Too many repositories matched "%s". Try '
                         'specifying the repository by name instead.'
                         % repository.path)
        self.assertEqual(rsp['repository'], repository.path)

    @webapi_test_template
    def test_post_repository_private(self):
        """Testing the POST <URL> API without access to the requested
        repository
        """
        repository = self.create_repository(tool_name='Test',
                                            public=False)

        rsp = self.api_post(
            get_validate_diff_url(),
            {
                'repository': repository.path,
                'path': SimpleUploadedFile('readme.diff', self.VALID_GIT_DIFF,
                                           content_type='text/x-patch'),
                'basedir': '/trunk',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)
