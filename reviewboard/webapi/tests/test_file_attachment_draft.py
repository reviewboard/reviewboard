from __future__ import unicode_literals

from django.utils import six
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.attachments.models import FileAttachment
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    draft_file_attachment_item_mimetype,
    draft_file_attachment_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_draft_file_attachment_item_url,
                                           get_draft_file_attachment_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the DraftFileAttachmentResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/file-attachments/'
    resource = resources.draft_file_attachment

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)

        if populate_items:
            items = [self.create_file_attachment(review_request, draft=True)]
        else:
            items = []

        return (get_draft_file_attachment_list_url(review_request,
                                                   local_site_name),
                draft_file_attachment_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)

        if post_valid_data:
            post_data = {
                'path': open(self._getTrophyFilename(), 'r'),
                'caption': 'New caption',
            }
        else:
            post_data = {}

        return (get_draft_file_attachment_list_url(review_request,
                                                   local_site_name),
                draft_file_attachment_item_mimetype,
                post_data,
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        self.assertIn('draft_file_attachment', rsp)
        item_rsp = rsp['draft_file_attachment']

        attachment = FileAttachment.objects.get(pk=item_rsp['id'])
        self.assertIn(attachment, draft.file_attachments.all())
        self.assertNotIn(attachment, review_request.file_attachments.all())
        self.compare_item(item_rsp, attachment)

    def test_post_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API
        with Permission Denied error
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        f = open(self._getTrophyFilename(), "r")
        self.assertTrue(f)
        rsp = self.api_post(
            get_draft_file_attachment_list_url(review_request),
            {
                'caption': 'Trophy',
                'path': f,
            },
            expected_status=403)
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the DraftFileAttachmentResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/file-attachments/<id>/'
    resource = resources.draft_file_attachment

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        return (get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk,
                                                   local_site_name),
                [review_request, file_attachment])

    def check_delete_result(self, user, review_request, file_attachment):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertNotIn(file_attachment,
                         draft.inactive_file_attachments.all())
        self.assertNotIn(file_attachment, draft.file_attachments.all())
        self.assertNotIn(file_attachment,
                         review_request.file_attachments.all())
        self.assertNotIn(file_attachment,
                         review_request.inactive_file_attachments.all())
        with self.assertRaises(FileAttachment.DoesNotExist):
            FileAttachment.objects.get(pk=file_attachment.pk)

    def test_delete_file_with_publish(self):
        """Testing delete the published DraftFileAttachment"""
        review_request = self.create_review_request()
        self._login_user(admin=True)
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)
        review_request.get_draft().publish()
        self.api_delete(get_draft_file_attachment_item_url(review_request,
                                                           file_attachment.pk))
        draft = review_request.get_draft()
        file_attachment = FileAttachment.objects.get(pk=file_attachment.pk)

        self.assertFalse(file_attachment.inactive_review_request.exists())
        self.assertIsNotNone(draft)
        self.assertIn(file_attachment,
                      draft.inactive_file_attachments.all())
        self.assertNotIn(file_attachment, draft.file_attachments.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)

        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        return (get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk,
                                                   local_site_name),
                draft_file_attachment_item_mimetype,
                file_attachment)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk,
                                                   local_site_name),
                draft_file_attachment_item_mimetype,
                {
                    'caption': 'My new caption',
                },
                file_attachment,
                [])

    def check_put_result(self, user, item_rsp, file_attachment):
        file_attachment = FileAttachment.objects.get(pk=file_attachment.pk)
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(file_attachment.draft_caption, 'My new caption')
