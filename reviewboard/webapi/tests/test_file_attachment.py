from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (file_attachment_item_mimetype,
                                                file_attachment_list_mimetype)
from reviewboard.webapi.tests.urls import (get_file_attachment_item_url,
                                           get_file_attachment_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the FileAttachmentResource list APIs."""
    fixtures = ['test_users']

    #
    # HTTP GET tests
    #

    @add_fixtures(['test_scmtools'])
    def test_get_file_attachments(self):
        """Testing the GET review-requests/<id>/file-attachments/ API"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)

        # This is the file attachment that should be returned.
        self.create_file_attachment(review_request,
                                    orig_filename='trophy1.png')

        # This attachment shouldn't be shown in the results. It represents
        # a file to be shown in the diff viewer.
        self.create_file_attachment(review_request,
                                    orig_filename='trophy2.png',
                                    repo_path='/trophy.png',
                                    repo_revision='123',
                                    repository=review_request.repository)

        # This attachment shouldn't be shown either, for the same
        # reasons.
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset,
                                        source_file='/trophy3.png',
                                        dest_file='/trophy3.png',
                                        source_revision='123',
                                        dest_detail='124')
        self.create_file_attachment(review_request,
                                    orig_filename='trophy3.png',
                                    added_in_filediff=filediff)

        rsp = self.apiGet(
            get_file_attachment_list_url(review_request),
            expected_mimetype=file_attachment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        file_attachments = rsp['file_attachments']
        self.assertEqual(len(file_attachments), 1)
        self.assertEqual(file_attachments[0]['filename'], 'trophy1.png')

    #
    # HTTP POST tests
    #

    def test_post_file_attachments(self):
        """Testing the POST review-requests/<id>/file-attachments/ API"""
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_file_attachment_list_url(review_request),
            {'path': f},
            expected_mimetype=file_attachment_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        review_request.publish(review_request.submitter)

    def test_post_file_attachments_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/file-attachments/ API
        with Permission Denied error
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        f = open(self._getTrophyFilename(), "r")
        self.assertTrue(f)
        rsp = self.apiPost(
            get_file_attachment_list_url(review_request),
            {
                'caption': 'Trophy',
                'path': f,
            },
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site(self):
        """Testing the POST review-requests/<id>/file-attachments/ API
        with a local site
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True,
                                                    submitter=user)

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_file_attachment_list_url(review_request, self.local_site_name),
            {'path': f},
            expected_mimetype=file_attachment_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/file-attachments/ API
        with a local site and Permission Denied error
        """
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(with_local_site=True,
                                                    publish=True,
                                                    submitter=user)

        self._login_user()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_file_attachment_list_url(review_request, self.local_site_name),
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the FileAttachmentResource item APIs."""
    fixtures = ['test_users']

    #
    # HTP GET tests
    #

    def test_get_file_attachment_not_modified(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)

        self._testHttpCaching(get_file_attachment_item_url(file_attachment),
                              check_etags=True)
