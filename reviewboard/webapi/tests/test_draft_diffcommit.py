"""Unit tests for the DraftDiffCommitResource."""

from __future__ import unicode_literals

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import six, timezone
from djblets.features.testing import override_feature_checks
from djblets.webapi.errors import INVALID_ATTRIBUTE, INVALID_FORM_DATA
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.diffviewer.commit_utils import serialize_validation_info
from reviewboard.diffviewer.models import DiffCommit
from reviewboard.reviews.models import ReviewRequestDraft
from reviewboard.webapi.errors import DIFF_EMPTY, DIFF_TOO_BIG
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import ExtraDataItemMixin
from reviewboard.webapi.tests.mimetypes import (
    draft_diffcommit_list_mimetype,
    draft_diffcommit_item_mimetype)
from reviewboard.webapi.tests.test_diffcommit import compare_diffcommit
from reviewboard.webapi.tests.urls import (get_draft_diffcommit_item_url,
                                           get_draft_diffcommit_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Tests for DraftDiffCommitResource list resource."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-request/<id>/draft/commits/'
    resource = resources.draft_diffcommit

    compare_item = compare_diffcommit

    _DEFAULT_DIFF_CONTENTS = (
        b'diff --git a/readme b/readme\n'
        b'index d6613f5..5b50866 100644\n'
        b'--- a/readme\n'
        b'+++ b/readme\n'
        b'@@ -1 +1,3 @@\n'
        b' Hello there\n'
        b'+\n'
        b'+Oh hi!\n'
    )

    _DEFAULT_POST_DATA = {
        'author_name': 'Author',
        'author_date': timezone.now().strftime(DiffCommit.ISO_DATE_FORMAT),
        'author_email': 'author@example.com',
        'committer_name': 'Committer',
        'committer_date': timezone.now().strftime(DiffCommit.ISO_DATE_FORMAT),
        'committer_email': 'committer@example.com',
        'commit_message': 'Commit message',
        'commit_id': 'r1',
        'parent_id': 'r0',
    }

    def setup_http_not_allowed_list_test(self, user):
        review_request = self.create_review_request(
            create_repository=True,
            public=True)
        diffset = self.create_diffset(review_request=review_request)
        return get_draft_diffcommit_list_url(review_request, diffset.revision)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=user,
            publish=True,
            with_local_site=with_local_site,
            create_with_history=True)
        diffset = self.create_diffset(review_request, draft=True)
        items = []

        if populate_items:
            items.append(self.create_diffcommit(diffset=diffset,
                                                repository=repository))

        return (
            get_draft_diffcommit_list_url(
                review_request,
                diffset.revision,
                local_site_name=local_site_name),
            draft_diffcommit_list_mimetype,
            items,
        )

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site=False,
                              local_site_name=None, post_valid_data=False):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=user,
            with_local_site=with_local_site,
            create_with_history=True)
        diffset = self.create_diffset(review_request, draft=True)

        if post_valid_data:
            diff = SimpleUploadedFile('diff', self._DEFAULT_DIFF_CONTENTS)
            post_data = dict(self._DEFAULT_POST_DATA,
                             **{'diff': diff})
        else:
            post_data = {}

        return (
            get_draft_diffcommit_list_url(review_request,
                                          diffset.revision,
                                          local_site_name=local_site_name),
            draft_diffcommit_item_mimetype,
            post_data,
            [],
        )

    def check_post_result(self, user, rsp):
        self.assertIn('draft_commit', rsp)
        item = rsp['draft_commit']
        diffcommit = DiffCommit.objects.get(pk=item['id'])

        self.compare_item(item, diffcommit)

    @webapi_test_template
    def test_post_empty(self):
        """Testing the POST <URL> API with an empty diff"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user,
            create_with_history=True)
        diffset = self.create_diffset(review_request, draft=True)

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_draft_diffcommit_list_url(review_request,
                                              diffset.revision),
                dict(self._DEFAULT_POST_DATA, **{
                    'diff': SimpleUploadedFile('diff', b'     ',
                                               content_type='text/x-patch'),
                }),
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_EMPTY.code)

    @webapi_test_template
    def test_post_too_large(self):
        """Testing the POST <URL> API with a diff that is too large"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user,
            create_with_history=True)
        diffset = self.create_diffset(review_request, draft=True)

        diff = SimpleUploadedFile('diff',
                                  self._DEFAULT_DIFF_CONTENTS,
                                  content_type='text/x-patch')

        with self.siteconfig_settings({'diffviewer_max_diff_size': 1},
                                      reload_settings=False):
            with override_feature_checks(self.override_features):
                rsp = self.api_post(
                    get_draft_diffcommit_list_url(review_request,
                                                  diffset.revision),
                    dict(self._DEFAULT_POST_DATA, **{
                        'diff': diff,
                    }),
                    expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_TOO_BIG.code)
        self.assertEqual(rsp['max_size'], 1)

    @webapi_test_template
    def test_post_no_history_allowed(self):
        """Testing the POST <URL> API for a review request created without
        history support
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user,
            create_with_history=False)
        ReviewRequestDraft.create(review_request)
        diffset = self.create_diffset(review_request, draft=True)

        diff = SimpleUploadedFile('diff',
                                  self._DEFAULT_DIFF_CONTENTS,
                                  content_type='text/x-patch')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_draft_diffcommit_list_url(review_request,
                                              diffset.revision),
                dict(self._DEFAULT_POST_DATA, **{
                    'diff': diff,
                }),
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_ATTRIBUTE.code)
        self.assertEqual(
            rsp['reason'],
            'This review request was not created with support for multiple '
            'commits.\n\n'
            'Use the draft_diff resource to upload diffs instead. See the '
            'draft_diff link on the parent resource for the URL.')

    @webapi_test_template
    def test_post_parent_diff(self):
        """Testing the POST <URL> API with a parent diff"""
        parent_diff_contents = (
            b'diff --git a/foo b/foo\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
        )

        diff_contents = (
            b'diff --git a/foo b/foo\n'
            b'index e69ded29..03b37a0 100644\n'
            b'--- a/foo\n'
            b'+++ b/foo\n'
            b'@@ -0,0 +1 @@'
            b'+foo bar baz qux\n'
        )
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user,
            create_with_history=True)
        diffset = self.create_diffset(review_request, draft=True)

        diff = SimpleUploadedFile('diff', diff_contents,
                                  content_type='text/x-patch')
        parent_diff = SimpleUploadedFile('parent_diff',
                                         parent_diff_contents,
                                         content_type='text/x-patch')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_draft_diffcommit_list_url(review_request,
                                              diffset.revision),
                dict(self._DEFAULT_POST_DATA, **{
                    'diff': diff,
                    'parent_diff': parent_diff,
                }),
                expected_mimetype=draft_diffcommit_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('draft_commit', rsp)

        item_rsp = rsp['draft_commit']
        self.compare_item(item_rsp, DiffCommit.objects.get(pk=item_rsp['id']))

        commit = DiffCommit.objects.get(pk=item_rsp['id'])
        self.compare_item(item_rsp, commit)

        files = list(commit.files.all())
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertIsNotNone(f.parent_diff)

    @webapi_test_template
    def test_post_parent_diff_subsequent(self):
        """Testing the POST <URL> API with a parent diff on a subsequent commit
        """
        parent_diff_contents = (
            b'diff --git a/foo b/foo\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
        )

        diff_contents = (
            b'diff --git a/foo b/foo\n'
            b'index e69ded29..03b37a0 100644\n'
            b'--- a/foo\n'
            b'+++ b/foo\n'
            b'@@ -0,0 +1 @@'
            b'+foo bar baz qux\n'
        )

        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user,
            create_with_history=True)

        diffset = self.create_diffset(review_request, draft=True)
        self.create_diffcommit(repository, diffset)

        diff = SimpleUploadedFile('diff', diff_contents,
                                  content_type='text/x-patch')
        parent_diff = SimpleUploadedFile('parent_diff', parent_diff_contents,
                                         content_type='text/x-patch')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_draft_diffcommit_list_url(review_request,
                                              diffset.revision),
                dict(self._DEFAULT_POST_DATA, **{
                    'commit_id': 'r0',
                    'parent_id': 'r1',
                    'diff': diff,
                    'parent_diff': parent_diff,
                }),
                expected_mimetype=draft_diffcommit_item_mimetype,
                expected_status=201)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('draft_commit', rsp)

        item_rsp = rsp['draft_commit']
        commit = DiffCommit.objects.get(pk=item_rsp['id'])
        self.compare_item(item_rsp, commit)

        files = list(commit.files.all())
        self.assertEqual(len(files), 1)

        f = files[0]
        self.assertIsNotNone(f.parent_diff)

    @webapi_test_template
    def test_post_invalid_date_format(self):
        """Testing the POST <URL> API with an invalid date format"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user,
            create_with_history=True)
        diffset = self.create_diffset(review_request, draft=True)

        diff = SimpleUploadedFile('diff',
                                  self._DEFAULT_DIFF_CONTENTS,
                                  content_type='text/x-patch')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_draft_diffcommit_list_url(review_request,
                                              diffset.revision),
                dict(self._DEFAULT_POST_DATA, **{
                    'commit_id': 'r0',
                    'parent_id': 'r1',
                    'diff': diff,
                    'committer_date': 'Jun 1 1990',
                    'author_date': 'Jun 1 1990',
                }),
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)

        err_fields = rsp['fields']
        self.assertIn('author_date', err_fields)
        self.assertIn('committer_date', err_fields)

        self.assertEqual(err_fields['author_date'],
                         ['This date must be in ISO 8601 format.'])
        self.assertEqual(err_fields['committer_date'],
                         ['This date must be in ISO 8601 format.'])

    @webapi_test_template
    def test_post_subsequent(self):
        """Testing the POST <URL> API with a subsequent commit"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user,
            create_with_history=True)
        diffset = self.create_diffset(review_request, draft=True)

        commit = self.create_diffcommit(
            repository,
            diffset,
            diff_contents=self._DEFAULT_DIFF_CONTENTS)

        validation_info = serialize_validation_info({
            commit.commit_id: {
                'parent_id': commit.parent_id,
                'tree': {
                    'added': [],
                    'modified': [{
                        'filename': 'readme',
                        'revision': '5b50866',
                    }],
                    'removed': [],
                },
            },
        })

        diff = SimpleUploadedFile(
            'diff',
            (b'diff --git a/readme b/readme\n'
             b'index 5b50866..f00f00f 100644\n'
             b'--- a/readme\n'
             b'+++ a/readme\n'
             b'@@ -1 +1,4 @@\n'
             b' Hello there\n'
             b' \n'
             b' Oh hi!\n'
             b'+Goodbye!\n'),
            content_type='text/x-patch')

        with override_feature_checks(self.override_features):
            rsp = self.api_post(
                get_draft_diffcommit_list_url(review_request,
                                              diffset.revision),
                dict(self._DEFAULT_POST_DATA, **{
                    'commit_id': 'r2',
                    'parent_id': 'r1',
                    'diff': diff,
                    'validation_info': validation_info,
                }),
                expected_mimetype=draft_diffcommit_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('draft_commit', rsp)

        item_rsp = rsp['draft_commit']
        self.compare_item(item_rsp, DiffCommit.objects.get(pk=item_rsp['id']))

    @webapi_test_template
    def test_post_finalized(self):
        """Testing the POST <URL> API after the parent DiffSet has been
        finalized
        """
        with override_feature_checks(self.override_features):
            review_request = self.create_review_request(
                create_repository=True,
                submitter=self.user,
                create_with_history=True)

            diffset = self.create_diffset(review_request, draft=True)
            diffset.finalize_commit_series(
                cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                validation_info=None,
                validate=False,
                save=True)

            diff = SimpleUploadedFile(
                'diff',
                self._DEFAULT_DIFF_CONTENTS,
                content_type='text/x-patch')

            rsp = self.api_post(
                get_draft_diffcommit_list_url(review_request,
                                              diffset.revision),
                dict(self._DEFAULT_POST_DATA, **{
                    'validation_info': serialize_validation_info({}),
                    'diff': diff,
                }),
                expected_status=400)

            self.assertEqual(rsp, {
                'stat': 'fail',
                'err': {
                    'code': INVALID_ATTRIBUTE.code,
                    'msg': INVALID_ATTRIBUTE.msg,
                },
                'reason': 'The diff has already been finalized.',
            })


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, BaseWebAPITestCase):
    """Tests for DraftDiffCommitResource item resource."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-request/<id>/draft/commits/<commit-id>/'
    resource = resources.draft_diffcommit

    compare_item = compare_diffcommit

    def setup_http_not_allowed_item_test(self, user):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    submitter=user)
        diffset = self.create_diffset(review_request, draft=True)
        commit = self.create_diffcommit(repository=repository,
                                        diffset=diffset)

        return get_draft_diffcommit_item_url(review_request,
                                             diffset.revision,
                                             commit.commit_id)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=user,
            with_local_site=with_local_site)
        diffset = self.create_diffset(review_request, draft=True)
        commit = self.create_diffcommit(repository=repository,
                                        diffset=diffset)

        return (
            get_draft_diffcommit_item_url(review_request,
                                          diffset.revision,
                                          commit.commit_id,
                                          local_site_name=local_site_name),
            draft_diffcommit_item_mimetype,
            commit)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=user,
            with_local_site=with_local_site)
        diffset = self.create_diffset(review_request, draft=True)
        commit = self.create_diffcommit(repository=repository,
                                        diffset=diffset)

        if put_valid_data:
            request_data = {}
        else:
            request_data = {}

        return (
            get_draft_diffcommit_item_url(review_request,
                                          diffset.revision,
                                          commit.commit_id,
                                          local_site_name=local_site_name),
            draft_diffcommit_item_mimetype,
            request_data,
            commit,
            [])

    def check_put_result(self, user, item_rsp, commit):
        commit = DiffCommit.objects.get(pk=commit.pk)
        self.compare_item(item_rsp, commit)
