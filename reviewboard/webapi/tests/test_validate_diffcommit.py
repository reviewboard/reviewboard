"""Unit tests for reviewboard.webapi.resources.validate_diffcommit."""

from __future__ import unicode_literals

import base64
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import six
from djblets.features.testing import override_feature_checks
from djblets.webapi.errors import INVALID_ATTRIBUTE
from djblets.webapi.testing.decorators import webapi_test_template
from kgb import SpyAgency

from reviewboard.diffviewer.commit_utils import serialize_validation_info
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.errors import (DIFF_EMPTY, DIFF_PARSE_ERROR,
                                       DIFF_TOO_BIG, INVALID_REPOSITORY)
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import validate_diffcommit_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_validate_diffcommit_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(SpyAgency, BaseWebAPITestCase):
    """Testing ValidateDiffCommitResource API."""

    resource = resources.validate_diffcommit
    sample_api_url = 'validation/validate-commit/'

    fixtures = ['test_scmtools', 'test_users']

    # The basic GET request *does* return JSON, but it is a singleton resource
    # whose item_result_key is only present in successful POST responses.
    basic_get_returns_json = False
    basic_post_success_status = 200

    def compare_item(self, item_rsp, item):
        """Compare a response to the item.

        This is intentionally a no-op because there will be no created model to
        compare against.

        Args:
            item_rsp (dict):
                The serialized response.

            item (object):
                The item to compare to. This is always ``None``.
        """
        pass

    def setup_http_not_allowed_item_test(self, user):
        return get_validate_diffcommit_url()

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        return (get_validate_diffcommit_url(local_site_name=local_site_name),
                validate_diffcommit_mimetype,
                None)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        repository = self.create_repository(tool_name='Git',
                                            with_local_site=with_local_site)

        post_data = {}

        if post_valid_data:
            self.spy_on(Repository.get_file_exists,
                        owner=Repository,
                        call_fake=lambda *args, **kwargs: True)

            validation_info = serialize_validation_info({
                'r1': {
                    'parent_id': 'r0',
                    'tree': {
                        'added': [{
                            'filename': 'README',
                            'revision': '94bdd3e',
                        }],
                        'modified': [],
                        'removed': [],
                    },
                },
            })
            diff = SimpleUploadedFile('diff',
                                      self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                                      content_type='text/x-patch')
            post_data = {
                'commit_id': 'r2',
                'parent_id': 'r1',
                'diff': diff,
                'validation_info': validation_info,
                'repository': repository.pk,
            }

        return (get_validate_diffcommit_url(local_site_name=local_site_name),
                validate_diffcommit_mimetype,
                post_data,
                [])

    def check_post_result(self, user, rsp):
        self.assertIn('commit_validation', rsp)
        self.assertIn('validation_info', rsp['commit_validation'])

    @webapi_test_template
    def test_post_diff_too_big(self):
        """Testing the POST <URL> API with a diff that is too big"""
        repo = self.create_repository(tool_name='Git')

        with self.siteconfig_settings({'diffviewer_max_diff_size': 1},
                                      reload_settings=False):
            with override_feature_checks(self.override_features):
                rsp = self.api_post(
                    get_validate_diffcommit_url(),
                    {

                        'commit_id': 'r1',
                        'parent_id': 'r0',
                        'diff': SimpleUploadedFile(
                            'diff',
                            self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                            content_type='text/x-patch'),
                        'repository': repo.name,
                    },
                    expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_TOO_BIG.code)
        self.assertEqual(rsp['max_size'], 1)

    @webapi_test_template
    def test_post_diff_empty(self):
        """Testing the POST <URL> API with an empty diff"""
        repo = self.create_repository(tool_name='Git')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {

                    'commit_id': 'r1',
                    'parent_id': 'r0',
                    'diff': SimpleUploadedFile('diff',
                                               b'    ',
                                               content_type='text/x-patch'),
                    'repository': repo.name,
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_EMPTY.code)

    @webapi_test_template
    def test_post_diff_parser_error(self):
        """Testing the POST <URL> API with a diff that does not parse"""
        repo = self.create_repository(tool_name='Git')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {

                    'commit_id': 'r1',
                    'parent_id': 'r0',
                    'diff': SimpleUploadedFile('diff',
                                               b'not a valid diff at all.',
                                               content_type='text/x-patch'),
                    'repository': repo.name,
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_PARSE_ERROR.code)
        self.assertEqual(rsp['linenum'], 0)

    @webapi_test_template
    def test_post_repo_no_history_support(self):
        """Testing the POST <URL> API with a repository that does not support
        history
        """
        repo = self.create_repository(tool_name='Test')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {

                    'commit_id': 'r1',
                    'parent_id': 'r0',
                    'diff': SimpleUploadedFile(
                        'diff',
                        self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                        content_type='text/x-patch'),
                    'repository': repo.name,
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_ATTRIBUTE.code)
        self.assertEqual(
            rsp['reason'],
            'The "%s" repository does not support review requests created '
            'with history.'
            % repo.name)

    @webapi_test_template
    def test_post_repo_does_not_exist(self):
        """Testing the POST <URL> API with a repository that does not exist"""
        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {
                    'commit_id': 'r1',
                    'parent_id': 'r0',
                    'diff': SimpleUploadedFile(
                        'diff',
                        self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                        content_type='text/x-patch'),
                    'repository': 'nope',
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    @webapi_test_template
    def test_post_repo_no_access(self):
        """Testing the POST <URL> API with a repository the user does not have
        access to
        """
        repo = self.create_repository(public=False)

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {
                    'commit_id': 'r1',
                    'parent_id': 'r0',
                    'diff': SimpleUploadedFile(
                        'diff',
                        self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                        content_type='text/x-patch'),
                    'repository': repo.name,
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    @webapi_test_template
    def test_post_repo_multiple(self):
        """Testing the POST <URL> API with multiple matching repositories"""
        repo = self.create_repository(name='repo')
        self.create_repository(name=repo.name)

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {
                    'commit_id': 'r1',
                    'parent_id': 'r0',
                    'diff': SimpleUploadedFile(
                        'diff',
                        self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                        content_type='text/x-patch'),
                    'repository': repo.name,
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)
        self.assertEqual(rsp['err']['msg'],
                         'Too many repositories matched "%s". Try specifying '
                         'the repository by name instead.'
                         % repo.name)

    @webapi_test_template
    def test_post_parent_diff(self):
        """Testing the POST <URL> API with a parent diff"""
        def _exists(repository, filename, revision, *args, **kwargs):
            return filename == 'README' and revision == '94bdd3e'

        repo = self.create_repository(name='repo')
        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    call_fake=_exists)

        parent_diff_contents = (
            b'diff --git a/README b/README\n'
            b'index 94bdd3e..f00f00 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@@ -2 +2 @@\n'
            b'-blah blah\n'
            b'+foo bar\n'
        )
        parent_diff = SimpleUploadedFile('parent_diff', parent_diff_contents,
                                         content_type='text/x-patch')

        diff_contents = (
            b'diff --git a/README b/README\n'
            b'index f00f00..197009f 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@@ -2 +2 @@\n'
            b'-foo bar\n'
            b'+blah!\n'
        )
        diff = SimpleUploadedFile('diff', diff_contents,
                                  content_type='text/x-patch')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {
                    'commit_id': 'r1',
                    'parent_id': 'r0',
                    'diff': diff,
                    'parent_diff': parent_diff,
                    'repository': repo.name,
                },
                expected_mimetype=validate_diffcommit_mimetype,
                expected_status=200)

        self.assertEqual(rsp['stat'], 'ok')

        validation_info = json.loads(base64.b64decode(
            rsp['commit_validation']['validation_info']).decode('utf-8'))
        self.assertEqual(validation_info, {
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [],
                    'modified': [
                        {
                            'filename': 'README',
                            'revision': '197009f',
                        },
                    ],
                    'removed': [],
                },
            },
        })

    @webapi_test_template
    def test_post_added_in_parent(self):
        """Testing the POST <URL> API with a subsequent commit that contains a
        file added in the parent diff
        """
        def _exists(repository, filename, revision, *args, **kwargs):
            return filename == 'README' and revision == '94bdd3e'

        initial_validation_info = {
            'r1': {
                'parent_id': 'r0',
                'tree': {
                    'added': [],
                    'modified': [],
                    'removed': [],
                },
            },
        }

        repo = self.create_repository(name='repo')

        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    call_fake=_exists)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                                  content_type='text/x-patch')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_validate_diffcommit_url(),
                {
                    'commit_id': 'r2',
                    'parent_id': 'r1',
                    'diff': diff,
                    'repository': repo.name,
                    'validation_info': serialize_validation_info(
                        initial_validation_info),
                },
                expected_mimetype=validate_diffcommit_mimetype,
                expected_status=200)

        self.assertEqual(rsp['stat'], 'ok')
