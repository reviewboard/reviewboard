from __future__ import unicode_literals

from django.utils import six
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.attachments.models import FileAttachment
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (file_attachment_item_mimetype,
                                                file_attachment_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.urls import (get_file_attachment_item_url,
                                           get_file_attachment_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    """Testing the FileAttachmentResource list APIs."""
    fixtures = ['test_users']
    basic_get_fixtures = ['test_scmtools']
    sample_api_url = 'review-requests/<id>/file-attachments/'
    resource = resources.file_attachment

    def setup_review_request_child_test(self, review_request):
        return (get_file_attachment_list_url(review_request),
                file_attachment_list_mimetype)

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user)

        if populate_items:
            # This is the file attachment that should be returned.
            items = [
                self.create_file_attachment(review_request,
                                            orig_filename='trophy1.png'),
            ]

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
        else:
            items = []

        return (get_file_attachment_list_url(review_request, local_site_name),
                file_attachment_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        return (get_file_attachment_list_url(review_request, local_site_name),
                file_attachment_item_mimetype,
                {
                    'path': open(self._getTrophyFilename(), 'r'),
                },
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        self.assertIn('file_attachment', rsp)
        item_rsp = rsp['file_attachment']

        attachment = FileAttachment.objects.get(pk=item_rsp['id'])
        self.assertIn(attachment, draft.file_attachments.all())
        self.assertNotIn(attachment, review_request.file_attachments.all())
        self.compare_item(item_rsp, attachment)

    def test_post_not_owner(self):
        """Testing the POST review-requests/<id>/file-attachments/ API
        without owner
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        with open(self._getTrophyFilename(), "r") as f:
            self.assertTrue(f)
            rsp = self.api_post(
                get_file_attachment_list_url(review_request),
                {
                    'caption': 'Trophy',
                    'path': f,
                },
                expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ReviewRequestChildItemMixin, BaseWebAPITestCase):
    """Testing the FileAttachmentResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/file-attachments/<id>/'
    resource = resources.file_attachment

    def setup_review_request_child_test(self, review_request):
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment),
                file_attachment_item_mimetype)

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)
        self.assertEqual(item_rsp['absolute_url'],
                         attachment.get_absolute_url())

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment, local_site_name),
                [review_request, file_attachment])

    def check_delete_result(self, user, review_request, file_attachment):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertIn(file_attachment, draft.inactive_file_attachments.all())
        self.assertNotIn(file_attachment, draft.file_attachments.all())
        self.assertIn(file_attachment, review_request.file_attachments.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment, local_site_name),
                file_attachment_item_mimetype,
                file_attachment)

    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)

        self._testHttpCaching(get_file_attachment_item_url(file_attachment),
                              check_etags=True)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment, local_site_name),
                file_attachment_item_mimetype,
                {
                    'caption': 'My new caption',
                },
                file_attachment,
                [review_request])

    def check_put_result(self, user, item_rsp, file_attachment,
                         review_request):
        file_attachment = FileAttachment.objects.get(pk=file_attachment.pk)
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(file_attachment.draft_caption, 'My new caption')

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        self.assertIn(file_attachment, draft.file_attachments.all())
        self.assertIn(file_attachment, review_request.file_attachments.all())
        self.compare_item(item_rsp, file_attachment)
