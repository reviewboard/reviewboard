from djblets.testing.decorators import add_fixtures

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (filediff_item_mimetype,
                                                filediff_list_mimetype)
from reviewboard.webapi.tests.urls import (get_draft_filediff_item_url,
                                           get_draft_filediff_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the DraftFileDiffResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_post_method_not_allowed(self):
        """Testing the
        POST review-requests/<id>/draft/diffs/<revision>/files/ API
        gives Method Not Allowed
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request, draft=True)

        self.apiPost(
            get_draft_filediff_list_url(diffset, review_request),
            expected_status=405)

    def test_get(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/ API
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        rsp = self.apiGet(
            get_draft_filediff_list_url(diffset, review_request),
            expected_mimetype=filediff_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['files'][0]['id'], filediff.pk)
        self.assertEqual(rsp['files'][0]['source_file'], filediff.source_file)

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/ API
        with a local site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(create_repository=True,
                                                    with_local_site=True,
                                                    submitter=user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        rsp = self.apiGet(
            get_draft_filediff_list_url(diffset, review_request,
                                        self.local_site_name),
            expected_mimetype=filediff_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['files'][0]['id'], filediff.pk)
        self.assertEqual(rsp['files'][0]['source_file'], filediff.source_file)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/ API
        with a local site and user not on the site
        """
        review_request = self.create_review_request(create_repository=True,
                                                    with_local_site=True)
        self.assertNotEqual(review_request.submitter, self.user)
        diffset = self.create_diffset(review_request, draft=True)
        self.create_filediff(diffset)

        self.apiGet(
            get_draft_filediff_list_url(diffset, review_request,
                                        self.local_site_name),
            expected_status=403)

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
    fixtures = ['test_users', 'test_scmtools']

    def test_delete_method_not_allowed(self):
        """Testing the
        DELETE review-requests/<id>/draft/diffs/<revision>/files/<id>/ API
        gives Method Not Allowed"""
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        self.apiDelete(
            get_draft_filediff_item_url(filediff, review_request),
            expected_status=405)

    def test_get(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/<id>/ API
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        rsp = self.apiGet(
            get_draft_filediff_item_url(filediff, review_request),
            expected_mimetype=filediff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['file']['id'], filediff.pk)
        self.assertEqual(rsp['file']['source_file'], filediff.source_file)

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/<id>/ API
        with a local site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(create_repository=True,
                                                    with_local_site=True,
                                                    submitter=user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        rsp = self.apiGet(
            get_draft_filediff_item_url(filediff, review_request,
                                        self.local_site_name),
            expected_mimetype=filediff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['file']['id'], filediff.pk)
        self.assertEqual(rsp['file']['source_file'], filediff.source_file)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the
        GET review-requests/<id>/draft/diffs/<revision>/files/<id>/ API
        with a local site and user not on the site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(submitter=user,
                                                    create_repository=True,
                                                    with_local_site=True)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        user = self._login_user()

        self.apiGet(
            get_draft_filediff_item_url(filediff, review_request,
                                        self.local_site_name),
            expected_status=403)

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

    def test_put_method_not_allowed(self):
        """Testing the
        PUT review-requests/<id>/draft/diffs/<revision>/files/<id>/ API
        gives Method Not Allowed
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        self.apiPut(
            get_draft_filediff_item_url(filediff, review_request),
            expected_status=405)
