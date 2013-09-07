from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.attachments.models import FileAttachment
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    draft_file_attachment_item_mimetype)
from reviewboard.webapi.tests.urls import (get_draft_file_attachment_item_url,
                                           get_draft_file_attachment_list_url)


class FileAttachmentDraftResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentDraftResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_post_file_attachments(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API"""
        review_request = self.create_review_request(submitter=self.user)

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_draft_file_attachment_list_url(review_request),
            {'path': f},
            expected_mimetype=draft_file_attachment_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_file_attachments_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with Permission Denied error"""
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(
            get_draft_file_attachment_list_url(review_request),
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
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with a local site"""
        user = self._login_user(local_site=True)

        review_request = self.create_review_request(submitter=user,
                                                    create_repository=True,
                                                    with_local_site=True)

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)

        post_data = {
            'path': f,
            'caption': 'Trophy',
        }

        rsp = self.apiPost(
            get_draft_file_attachment_list_url(review_request,
                                               self.local_site_name),
            post_data,
            expected_mimetype=draft_file_attachment_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft_file_attachment']['caption'], 'Trophy')

        draft = review_request.get_draft(User.objects.get(username='doc'))
        self.assertNotEqual(draft, None)

        return review_request, rsp['draft_file_attachment']['id']

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with a local site and Permission Denied error"""
        review_request = self.create_review_request(with_local_site=True)

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            get_draft_file_attachment_list_url(review_request,
                                               self.local_site_name),
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_file_attachment(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/ API"""
        draft_caption = 'The new caption'

        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)

        # Now modify the caption.
        rsp = self.apiPut(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment.id),
            {'caption': draft_caption},
            expected_mimetype=draft_file_attachment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(self.user)
        self.assertNotEqual(draft, None)

        file_attachment = FileAttachment.objects.get(pk=file_attachment.id)
        self.assertEqual(file_attachment.draft_caption, draft_caption)

    @add_fixtures(['test_site'])
    def test_put_file_attachment_with_site(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/ API with a local site"""
        draft_caption = 'The new caption'
        user = User.objects.get(username='doc')

        review_request, file_attachment_id = \
            self.test_post_file_attachments_with_site()
        review_request.publish(user)

        rsp = self.apiPut(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment_id,
                                               self.local_site_name),
            {'caption': draft_caption},
            expected_mimetype=draft_file_attachment_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft(user)
        self.assertNotEqual(draft, None)

        file_attachment = FileAttachment.objects.get(pk=file_attachment_id)
        self.assertEqual(file_attachment.draft_caption, draft_caption)

    @add_fixtures(['test_site'])
    def test_put_file_attachment_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/ API with a local site and Permission Denied error"""
        review_request, file_attachment_id = \
            self.test_post_file_attachments_with_site()
        review_request.publish(User.objects.get(username='doc'))

        self._login_user()

        rsp = self.apiPut(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment_id,
                                               self.local_site_name),
            {'caption': 'test'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
