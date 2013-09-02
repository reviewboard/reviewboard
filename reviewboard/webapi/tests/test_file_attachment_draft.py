from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.tests.base import BaseWebAPITestCase, _build_mimetype
from reviewboard.webapi.tests.test_file_attachment import \
    FileAttachmentResourceTests


class FileAttachmentDraftResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentDraftResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    list_mimetype = _build_mimetype('draft-file-attachments')
    item_mimetype = _build_mimetype('draft-file-attachment')

    def test_post_file_attachments(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        file_attachments_url = \
            rsp['review_request']['links']['file_attachments']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            file_attachments_url,
            {'path': f},
            expected_mimetype=FileAttachmentResourceTests.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_reviewrequests'])
    def test_post_file_attachments_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            public=True, local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(
            self.get_list_url(review_request),
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
        self._login_user(local_site=True)

        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')
        review_request = ReviewRequest.objects.get(
            local_site__name=self.local_site_name,
            local_id=rsp['review_request']['id'])

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)

        post_data = {
            'path': f,
            'caption': 'Trophy',
        }

        rsp = self.apiPost(
            self.get_list_url(review_request, self.local_site_name),
            post_data,
            expected_mimetype=self.item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft_file_attachment']['caption'], 'Trophy')

        draft = review_request.get_draft(User.objects.get(username='doc'))
        self.assertNotEqual(draft, None)

        return review_request, rsp['draft_file_attachment']['id']

    @add_fixtures(['test_reviewrequests', 'test_site'])
    def test_post_file_attachments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API with a local site and Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            local_site__name=self.local_site_name)[0]

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            self.get_list_url(review_request, self.local_site_name),
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_file_attachment(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/ API"""
        draft_caption = 'The new caption'

        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
        rsp = self.apiPost(
            self.get_list_url(review_request),
            {
                'caption': 'Trophy',
                'path': f,
            },
            expected_mimetype=self.item_mimetype)
        f.close()
        review_request.publish(self.user)

        file_attachment = FileAttachment.objects.get(pk=rsp['draft_file_attachment']['id'])

        # Now modify the caption.
        rsp = self.apiPut(
            self.get_item_url(review_request, file_attachment.id),
            {'caption': draft_caption},
            expected_mimetype=self.item_mimetype)

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
            self.get_item_url(review_request, file_attachment_id,
                              self.local_site_name),
            {'caption': draft_caption},
            expected_mimetype=self.item_mimetype)
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
            self.get_item_url(review_request, file_attachment_id,
                              self.local_site_name),
            {'caption': 'test'},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def get_list_url(self, review_request, local_site_name=None):
        return local_site_reverse(
            'draft-file-attachments-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
            })

    def get_item_url(self, review_request, file_attachment_id,
                     local_site_name=None):
        return local_site_reverse(
            'draft-file-attachment-resource',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'file_attachment_id': file_attachment_id,
            })
