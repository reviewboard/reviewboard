from __future__ import unicode_literals

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (filediff_list_mimetype,
                                                filediff_item_mimetype)
from reviewboard.webapi.tests.urls import (get_filediff_item_url,
                                           get_filediff_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the FileDiffResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_get_list_resource_with_commit_filtering(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files list
        API with commit_id filtering
        """
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request=review_request,
                                      repository=repository)

        commit = self.create_diff_commit(diffset, repository, 'r1', 'r0')

        rsp = self.api_get(get_filediff_list_url(diffset, review_request)
                           + '?commit-id=' + commit.parent_id,
                           expected_status=200,
                           expected_mimetype=filediff_list_mimetype)

        self.assertIn('files', rsp)
        self.assertListEqual(rsp['files'], [])
        self.assertIn('total_results', rsp)
        self.assertEqual(rsp['total_results'], 0)

        rsp = self.api_get(get_filediff_list_url(diffset, review_request)
                           + '?commit-id=' + commit.commit_id,
                           expected_status=200,
                           expected_mimetype=filediff_list_mimetype)

        self.assertIn('files', rsp)
        self.assertEqual(len(rsp['files']), 1)
        self.assertIn('total_results', rsp)
        self.assertEqual(rsp['total_results'], 1)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the FileDiffResource item APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_get_item_resource_with_commit_query_parameter(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/files/ item
        API with commit_id filtering
        """
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository,
                                                    submitter=self.user)

        diffset = self.create_diffset(review_request=review_request,
                                      repository=repository)

        self.create_diff_commit(diffset, repository, 'r1', 'r0')

        filediff = diffset.files.first()

        unfiltered_rsp = self.api_get(get_filediff_item_url(filediff,
                                                            review_request),
                                      expected_status=200,
                                      expected_mimetype=filediff_item_mimetype)

        filtered_rsp = self.api_get(
            get_filediff_item_url(filediff, review_request) + '?commit-id='
            + filediff.diff_commit.commit_id,
            expected_status=200,
            expected_mimetype=filediff_item_mimetype)

        self.assertDictEqual(unfiltered_rsp, filtered_rsp)
        self.assertIn('file', filtered_rsp)
        self.assertIn('id', filtered_rsp['file'])
        self.assertEqual(filtered_rsp['file']['id'], filediff.id)
