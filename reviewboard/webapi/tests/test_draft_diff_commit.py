from __future__ import unicode_literals

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import six, timezone

from reviewboard.diffviewer.models import DiffCommit
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (diff_commit_item_mimetype,
                                                diff_commit_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.test_diff_commit import compare_item
from reviewboard.webapi.tests.urls import (get_draft_diff_commit_item_url,
                                           get_draft_diff_commit_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase, ExtraDataListMixin):
    """Testing the DraftDiffCommitResource list APIs."""
    resource = resources.draft_diff_commit
    sample_api_url = 'review-requests/<id>/draft/diffs/<id>/commits/'
    fixtures = ['test_users', 'test_scmtools']

    compare_item = compare_item

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user)

        diffset = self.create_diffset(review_request=review_request,
                                      revision=1,
                                      repository=repository,
                                      draft=True)

        if post_valid_data:
            diff_file = SimpleUploadedFile('diff',
                                           self.DEFAULT_COMMIT_FILEDIFF_DATA,
                                           content_type='text/x-patch')

            post_data = {
                'path': diff_file,
                'commit_id': 'r1',
                'parent_id': 'r0',
                'author_name': 'Author name',
                'author_email': 'author@example.com',
                'author_date': timezone.now().strftime(DiffCommit.DATE_FORMAT),
                'commit_type': 'change',
                'description': 'description',
            }
        else:
            post_data = {}

        return (get_draft_diff_commit_list_url(review_request,
                                               diffset,
                                               local_site_name),
                diff_commit_item_mimetype,
                post_data,
                [review_request, diffset])

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request=review_request,
                                      repository=repository,
                                      draft=True)

        items = []

        if populate_items:
            commit = self.create_diff_commit(diffset=diffset,
                                             repository=repository,
                                             commit_id='r1',
                                             parent_id='r0')

            items.append(commit)

        return (get_draft_diff_commit_list_url(review_request, diffset,
                                               local_site_name),
                diff_commit_list_mimetype,
                items)

    def check_post_result(self, user, rsp, review_request, diffset):
        self.assertIn('draft_diff_commit', rsp)
        item_rsp = rsp['draft_diff_commit']

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        commit = DiffCommit.objects.get(pk=item_rsp['id'])
        self.assertEqual(diffset, commit.diffset)
        self.compare_item(item_rsp, commit)

    def test_post_with_non_empty_diffset(self):
        """Testing the POST <URL> API with a non-empty parent DiffSet"""
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository,
                                                    submitter=self.user)

        diffset = self.create_diffset(review_request=review_request,
                                      draft=True)

        self.create_filediff(diffset)

        diff_file = SimpleUploadedFile('diff',
                                       self.DEFAULT_COMMIT_FILEDIFF_DATA,
                                       'text/x-patch')
        post_data = {
            'path': diff_file,
            'commit_id': 'r1',
            'parent_id': 'r0',
            'author_name': 'Author name',
            'author_email': 'author@example.com',
            'author_date': timezone.now().strftime(DiffCommit.DATE_FORMAT),
            'commit_type': 'change',
            'description': 'description'
        }

        rsp = self.api_post(get_draft_diff_commit_list_url(review_request,
                                                           diffset),
                            query=post_data,
                            expected_status=400)

        self.assertIn('reason', rsp)
        self.assertIn('err', rsp)
        self.assertIn('code', rsp['err'])
        self.assertEqual(102, rsp['err']['code'])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase, ExtraDataItemMixin):
    resource = resources.draft_diff_commit
    sample_api_url = 'review-requests/<id>/draft/diffs/<id>/commits/<commit>/'
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET', 'PUT')
    basic_put_use_admin = False

    compare_item = compare_item

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request=review_request,
                                      repository=repository,
                                      draft=True)

        commit = self.create_diff_commit(diffset=diffset,
                                         repository=repository,
                                         commit_id='r1',
                                         parent_id='r2')

        return (get_draft_diff_commit_item_url(review_request, diffset,
                                               commit, local_site_name),
                diff_commit_item_mimetype,
                commit)

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            with_local_site=with_local_site,
            submitter=user)

        diffset = self.create_diffset(review_request, draft=True)

        commit = self.create_diff_commit(diffset=diffset,
                                         repository=repository,
                                         commit_id='r1',
                                         parent_id='r2')

        return (get_draft_diff_commit_item_url(review_request, diffset,
                                               commit, local_site_name),
                diff_commit_item_mimetype,
                {},
                commit,
                [])

    def check_put_result(self, user, item_rsp, commit):
        self.compare_item(item_rsp, commit)
