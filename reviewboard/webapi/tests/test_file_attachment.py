from django.core.files import File
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (file_attachment_item_mimetype,
                                                file_attachment_list_mimetype)
from reviewboard.webapi.tests.urls import (get_file_attachment_item_url,
                                           get_file_attachment_list_url)


class FileAttachmentResourceTests(BaseWebAPITestCase):
    """Testing the FileAttachmentResource APIs."""
    fixtures = ['test_users', 'test_scmtools']

    def test_get_file_attachments(self):
        """Testing the GET review-requests/<id>/file-attachments/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        trophy_filename = self._getTrophyFilename()

        # This is the file attachment that should be returned.
        f = open(trophy_filename, "r")
        file_attachment = FileAttachment.objects.create(
            orig_filename='trophy1.png',
            mimetype='image/png')
        file_attachment.file.save('trophy.png', File(f), save=True)
        f.close()
        review_request.file_attachments.add(file_attachment)

        # This attachment shouldn't be shown in the results. It represents
        # a file to be shown in the diff viewer.
        f = open(trophy_filename, "r")
        file_attachment = FileAttachment.objects.create(
            orig_filename='trophy2.png',
            mimetype='image/png',
            repo_path='/trophy.png',
            repo_revision='123',
            repository=review_request.repository)
        file_attachment.file.save('trophy.png', File(f), save=True)
        f.close()
        review_request.file_attachments.add(file_attachment)

        # This attachment shouldn't be shown either, for the same
        # reasons.
        diffset = DiffSet.objects.create(
            name='diffset',
            revision=1,
            history=review_request.diffset_history,
            repository=review_request.repository)
        filediff = FileDiff.objects.create(
            diffset=diffset,
            source_file='/trophy3.png',
            dest_file='/trophy3.png',
            source_revision='123',
            dest_detail='124',
            status=FileDiff.MODIFIED)

        f = open(trophy_filename, "r")
        file_attachment = FileAttachment.objects.create(
            orig_filename='trophy3.png',
            mimetype='image/png',
            added_in_filediff=filediff)
        file_attachment.file.save('trophy.png', File(f), save=True)
        f.close()
        review_request.file_attachments.add(file_attachment)

        review_request.publish(review_request.submitter)

        rsp = self.apiGet(
            get_file_attachment_list_url(review_request),
            expected_mimetype=file_attachment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        file_attachments = rsp['file_attachments']
        self.assertEqual(len(file_attachments), 1)
        self.assertEqual(file_attachments[0]['filename'], 'trophy1.png')

    def test_get_file_attachment_not_modified(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/ API with Not Modified response"""
        self.test_post_file_attachments()

        file_attachment = FileAttachment.objects.all()[0]
        self._testHttpCaching(get_file_attachment_item_url(file_attachment),
                              check_etags=True)

    def test_post_file_attachments(self):
        """Testing the POST review-requests/<id>/file-attachments/ API"""
        rsp = self._postNewReviewRequest()
        self.assertEqual(rsp['stat'], 'ok')
        review_request = \
            ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        file_attachments_url = \
            rsp['review_request']['links']['file_attachments']['href']

        f = open(self._getTrophyFilename(), "r")
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            file_attachments_url,
            {'path': f},
            expected_mimetype=file_attachment_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        review_request.publish(review_request.submitter)

    @add_fixtures(['test_reviewrequests'])
    def test_post_file_attachments_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(
            public=True, local_site=None).exclude(submitter=self.user)[0]

        f = open(self._getTrophyFilename(), "r")
        self.assert_(f)
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

    def _test_review_request_with_site(self):
        self._login_user(local_site=True)

        repo = Repository.objects.get(name='Review Board Git')
        rsp = self._postNewReviewRequest(local_site_name=self.local_site_name,
                                         repository=repo)
        self.assertEqual(rsp['stat'], 'ok')

        return rsp['review_request']['links']['file_attachments']['href']

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with a local site"""
        file_attachments_url = self._test_review_request_with_site()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            file_attachments_url,
            {'path': f},
            expected_mimetype=file_attachment_item_mimetype)
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

    @add_fixtures(['test_site'])
    def test_post_file_attachments_with_site_no_access(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with a local site and Permission Denied error"""
        file_attachments_url = self._test_review_request_with_site()
        self._login_user()

        f = open(self._getTrophyFilename(), 'r')
        self.assertNotEqual(f, None)
        rsp = self.apiPost(
            file_attachments_url,
            {'path': f},
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)
