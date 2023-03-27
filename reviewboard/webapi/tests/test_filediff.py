from djblets.features.testing import override_feature_check
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.models import FileDiff
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (filediff_item_mimetype,
                                                filediff_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_extra_data import ExtraDataItemMixin
from reviewboard.webapi.tests.urls import (get_filediff_item_url,
                                           get_filediff_list_url)


def _compare_item(self, item_rsp, filediff):
    self.assertEqual(item_rsp['id'], filediff.pk)
    self.assertEqual(item_rsp['binary'], filediff.binary)
    self.assertEqual(item_rsp['extra_data'], filediff.extra_data)
    self.assertEqual(item_rsp['source_file'], filediff.source_file)
    self.assertEqual(item_rsp['dest_file'], filediff.dest_file)
    self.assertEqual(item_rsp['source_revision'], filediff.source_revision)
    self.assertEqual(item_rsp['dest_detail'], filediff.dest_detail)
    self.assertEqual(item_rsp['status'], filediff.status_string)


class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase,
                        metaclass=BasicTestsMetaclass):
    """Testing the FileDiffResource list APIs."""

    resource = resources.filediff
    sample_api_url = \
        'review-requests/<review-request-id>/diffs/<revision>/files/'

    compare_item = _compare_item
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET',)

    #
    # HTTP GET Tests
    #
    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        repository = self.create_repository(with_local_site)
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request)
        items = []

        if populate_items:
            items.append(self.create_filediff(diffset))

        return (get_filediff_list_url(diffset, review_request,
                                      local_site_name),
                filediff_list_mimetype,
                items)

    def setup_review_request_child_test(self, review_request):
        """Set up the review request child tests.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The test review request.

        Returns:
            tuple:
            A tuple of the API list URL and list mimetype to run tests on.
        """
        review_request.repository = self.create_repository(name='test-repo')
        diffset = self.create_diffset(review_request)
        return (get_filediff_list_url(diffset, review_request),
                filediff_list_mimetype)

    @webapi_test_template
    def test_commit_filter(self):
        """Testing the GET <URL>?commit-id= API filters FileDiffs to the
        requested commit
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            repository = self.create_repository()
            review_request = self.create_review_request(repository=repository,
                                                        submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          repository=repository)
            commit = self.create_diffcommit(diffset=diffset,
                                            repository=repository)

            diffset.finalize_commit_series(
                cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                validation_info=None,
                validate=False,
                save=True)

            rsp = self.api_get(
                '%s?commit-id=%s'
                % (get_filediff_list_url(diffset, review_request),
                   commit.commit_id),
                expected_status=200,
                expected_mimetype=filediff_list_mimetype)

            self.assertIn('stat', rsp)
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('files', rsp)
            self.assertEqual(rsp['total_results'], 1)

            item_rsp = rsp['files'][0]
            filediff = FileDiff.objects.get(pk=item_rsp['id'])
            self.compare_item(item_rsp, filediff)

    @webapi_test_template
    def test_commit_filter_no_results(self):
        """Testing the GET <URL>?commit-id= API with no results"""
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            repository = self.create_repository()
            review_request = self.create_review_request(
                repository=repository,
                submitter=self.user,
                create_with_history=True)
            diffset = self.create_diffset(review_request=review_request,
                                          repository=repository)
            commit = self.create_diffcommit(diffset=diffset,
                                            repository=repository)

            diffset.finalize_commit_series(
                cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                validation_info=None,
                validate=False,
                save=True)

            rsp = self.api_get(
                '%s?commit-id=%s'
                % (get_filediff_list_url(diffset, review_request),
                   commit.parent_id),
                expected_status=200,
                expected_mimetype=filediff_list_mimetype)

            self.assertIn('stat', rsp)
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('files', rsp)
            self.assertEqual(rsp['files'], [])
            self.assertEqual(rsp['total_results'], 0)

    @webapi_test_template
    def test_history_no_commit_filter(self):
        """Testing the GET <URL> API for a diffset with commits only returns
        cumulative files
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            repository = self.create_repository()
            review_request = self.create_review_request(
                repository=repository,
                submitter=self.user,
                create_with_history=True)
            diffset = self.create_diffset(review_request=review_request,
                                          repository=repository)
            commit = self.create_diffcommit(diffset=diffset,
                                            repository=repository)

            diffset.finalize_commit_series(
                cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                validation_info=None,
                validate=False,
                save=True)

            cumulative_filediff = diffset.cumulative_files[0]

            rsp = self.api_get(
                get_filediff_list_url(diffset, review_request),
                expected_mimetype=filediff_list_mimetype)

            self.assertIn('stat', rsp)
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn('files', rsp)
            self.assertEqual(rsp['total_results'], 1)
            self.assertEqual(rsp['files'][0]['id'],
                             cumulative_filediff.pk)

            self.assertNotEqual(commit.files.get().pk,
                                cumulative_filediff.pk)


class ResourceItemTests(ExtraDataItemMixin, ReviewRequestChildItemMixin,
                        BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Testing the FileDiffResource item APIs."""

    resource = resources.filediff
    sample_api_url = (
        'review-requests/<review-request-id>/diffs/<revision>/files/'
        '<file-id>/'
    )

    compare_item = _compare_item
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET',)
    basic_put_use_admin = False

    #
    # HTTP GET Tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(with_local_site)
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        return (get_filediff_item_url(filediff, review_request,
                                      local_site_name),
                filediff_item_mimetype,
                filediff)

    #
    # HTTP PUT Tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        repository = self.create_repository(with_local_site)
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        return (
            get_filediff_item_url(filediff, review_request,
                                  local_site_name),
            filediff_item_mimetype,
            {
                'extra_data.test': 'foo',
            },
            filediff,
            [])

    def setup_review_request_child_test(self, review_request):
        """Set up the review request child tests.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The test review request.

        Returns:
            tuple:
            A tuple of the API list URL and list mimetype to run tests on.
        """
        review_request.repository = self.create_repository(name='test-repo')
        diffset = self.create_diffset(review_request)
        return (get_filediff_list_url(diffset, review_request),
                filediff_list_mimetype)

    @webapi_test_template
    def test_get_with_diff_data(self):
        """Testing the GET <URL> API with diff data result"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            publish=True)

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(
            diffset,
            source_file='newfile.py',
            source_revision=PRE_CREATION,
            dest_file='newfile.py',
            dest_detail='20e43bb7c2d9f3a31768404ac71121804d806f7c',
            diff=(
                b"diff --git a/newfile.py b/newfile.py\n"
                b"new file mode 100644\n"
                b"index 0000000000000000000000000000000000000000.."
                b"8eaa5c1eacb55c43f5e00ed9dcd0c8da901f0c85\n"
                b"--- /dev/null\n"
                b"+++ b/newfile.py\n"
                b"@@ -0,0 +1 @@\n"
                b"+print('hello, world!')\n"
            ))

        rsp = self.api_get(
            get_filediff_item_url(filediff, review_request),
            HTTP_ACCEPT='application/vnd.reviewboard.org.diff.data+json',
            expected_status=200,
            expected_mimetype='application/json')

        self.assertEqual(
            rsp,
            {
                'diff_data': {
                    'binary': False,
                    'changed_chunk_indexes': [0],
                    'chunks': [
                        {
                            'change': 'insert',
                            'collapsable': False,
                            'index': 0,
                            'lines': [
                                [
                                    1,
                                    '',
                                    '',
                                    [],
                                    1,
                                    'print(&#x27;hello, world!&#x27;)',
                                    [],
                                    False,
                                ],
                            ],
                            'meta': {
                                'left_headers': [],
                                'right_headers': [],
                                'whitespace_chunk': False,
                                'whitespace_lines': [],
                            },
                            'numlines': 1,
                        },
                    ],
                    'new_file': True,
                    'num_changes': 1,
                },
                'stat': 'ok',
            })

    @webapi_test_template
    def test_get_with_diff_data_and_syntax_highlighting(self):
        """Testing the GET <URL> API with diff data result and
        ?syntax-highlighting=1
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            publish=True)

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(
            diffset,
            source_file='newfile.py',
            source_revision=PRE_CREATION,
            dest_file='newfile.py',
            dest_detail='20e43bb7c2d9f3a31768404ac71121804d806f7c',
            diff=(
                b"diff --git a/newfile.py b/newfile.py\n"
                b"new file mode 100644\n"
                b"index 0000000000000000000000000000000000000000.."
                b"8eaa5c1eacb55c43f5e00ed9dcd0c8da901f0c85\n"
                b"--- /dev/null\n"
                b"+++ b/newfile.py\n"
                b"@@ -0,0 +1 @@\n"
                b"+print('hello, world!')\n"
            ))

        rsp = self.api_get(
            ('%s?syntax-highlighting=1'
             % get_filediff_item_url(filediff, review_request)),
            HTTP_ACCEPT='application/vnd.reviewboard.org.diff.data+json',
            expected_status=200,
            expected_mimetype='application/json')

        self.assertEqual(
            rsp,
            {
                'diff_data': {
                    'binary': False,
                    'changed_chunk_indexes': [0],
                    'chunks': [
                        {
                            'change': 'insert',
                            'collapsable': False,
                            'index': 0,
                            'lines': [
                                [
                                    1,
                                    '',
                                    '',
                                    [],
                                    1,
                                    '<span class="nb">print</span>'
                                    '<span class="p">(</span>'
                                    '<span class="s1">&#39;hello, '
                                    'world!&#39;</span>'
                                    '<span class="p">)</span>',
                                    [],
                                    False,
                                ],
                            ],
                            'meta': {
                                'left_headers': [],
                                'right_headers': [],
                                'whitespace_chunk': False,
                                'whitespace_lines': [],
                            },
                            'numlines': 1,
                        },
                    ],
                    'new_file': True,
                    'num_changes': 1,
                },
                'stat': 'ok',
            })
