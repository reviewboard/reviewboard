from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (filediff_item_mimetype,
                                                filediff_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_draft_filediff_item_url,
                                           get_draft_filediff_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the DraftFileDiffResource list APIs."""
    __metaclass__ = BasicTestsMetaclass

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/draft/diffs/<revision>/files/'
    resource = resources.draft_filediff

    def compare_item(self, item_rsp, filediff):
        self.assertEqual(item_rsp['id'], filediff.pk)
        self.assertEqual(item_rsp['source_file'], filediff.source_file)

    def setup_http_not_allowed_list_test(self, user):
        review_request = self.create_review_request(
            create_repository=True,
            submitter=user)
        diffset = self.create_diffset(review_request, draft=True)

        return get_draft_filediff_list_url(diffset, review_request)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user)
        diffset = self.create_diffset(review_request, draft=True)

        if populate_items:
            items = [self.create_filediff(diffset)]
        else:
            items = []

        return (get_draft_filediff_list_url(diffset, review_request,
                                            local_site_name),
                filediff_list_mimetype,
                items)

    def test_get_not_owner(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/ API
        without owner with Permission Denied error
        """
        review_request = self.create_review_request(create_repository=True)
        self.assertNotEqual(review_request.submitter, self.user)
        diffset = self.create_diffset(review_request, draft=True)

        self.apiGet(
            get_draft_filediff_list_url(diffset, review_request),
            expected_status=403)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the DraftFileDiffResource item APIs."""
    __metaclass__ = BasicTestsMetaclass

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/draft/diffs/<revision>/files/<id>/'
    resource = resources.draft_filediff
    test_http_methods = ('DELETE', 'GET')

    def setup_http_not_allowed_item_test(self, user):
        review_request = self.create_review_request(
            create_repository=True,
            submitter=user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        return get_draft_filediff_item_url(filediff, review_request)

    def compare_item(self, item_rsp, filediff):
        self.assertEqual(item_rsp['id'], filediff.pk)
        self.assertEqual(item_rsp['source_file'], filediff.source_file)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        return (get_draft_filediff_item_url(filediff, review_request,
                                            local_site_name),
                filediff_item_mimetype,
                filediff)

    def test_get_not_owner(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/<id>/ API
        without owner with Permission Denied error
        """
        review_request = self.create_review_request(create_repository=True)
        self.assertNotEqual(review_request.submitter, self.user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        self.apiGet(
            get_draft_filediff_item_url(filediff, review_request),
            expected_status=403)
