from __future__ import unicode_literals

from django.utils import six
from djblets.webapi.errors import DUPLICATE_ITEM

from reviewboard.attachments.models import FileAttachment
from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    user_file_attachment_item_mimetype,
    user_file_attachment_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_user_file_attachment_item_url,
                                           get_user_file_attachment_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the UserFileAttachmentResource list APIs."""

    fixtures = ['test_users', 'test_site']
    resource = resources.user_file_attachment
    sample_api_url = 'users/<username>/file-attachments/'

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            local_site = LocalSite.objects.get(name='local-site-1')

            if with_local_site:
                self.create_user_file_attachment(user,
                                                 has_file=True,
                                                 orig_filename='Trophy1.png',
                                                 mimetype='image/png')

                self.create_user_file_attachment(user)

                items = [
                    self.create_user_file_attachment(user,
                                                     local_site=local_site),
                ]
            else:
                self.create_user_file_attachment(user,
                                                 local_site=local_site)

                items = [
                    self.create_user_file_attachment(user,
                                                     has_file=True,
                                                     orig_filename='Trph.png',
                                                     mimetype='image/png'),
                    self.create_user_file_attachment(user),
                ]
        else:
            items = []

        return (get_user_file_attachment_list_url(user, local_site_name),
                user_file_attachment_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        caption = 'My initial caption.'

        return (
            get_user_file_attachment_list_url(user, local_site_name),
            user_file_attachment_item_mimetype,
            {
                'path': open(self.get_sample_image_filename(), 'rb'),
                'caption': caption,
            },
            [caption]
        )

    def check_post_result(self, user, rsp, caption):
        self.assertIn('user_file_attachment', rsp)
        item_rsp = rsp['user_file_attachment']

        attachment = FileAttachment.objects.get(pk=item_rsp['id'])
        self.compare_item(item_rsp, attachment)
        self.assertEqual(attachment.caption, caption)

    def test_post_no_file_attachment(self):
        """Testing the POST users/<username>/file-attachments/ API without a
        file attached
        """
        caption = 'My initial caption.'

        rsp = self.api_post(
            get_user_file_attachment_list_url(self.user),
            {'caption': caption},
            expected_status=201,
            expected_mimetype=user_file_attachment_item_mimetype)

        self.check_post_result(None, rsp, caption)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the UserFileAttachmentResource item APIs."""

    fixtures = ['test_users']
    sample_api_url = 'users/<username>/file-attachments/<id>/'
    resource = resources.user_file_attachment

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        file_attachment = self.create_user_file_attachment(
            user,
            with_local_site=with_local_site,
            local_site_name=local_site_name)

        return (get_user_file_attachment_item_url(user,
                                                  file_attachment,
                                                  local_site_name),
                [file_attachment])

    def check_delete_result(self, user, file_attachment):
        file_attachments = FileAttachment.objects.all()
        self.assertNotIn(file_attachment, file_attachments)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        file_attachment = self.create_user_file_attachment(
            user,
            with_local_site=with_local_site,
            local_site_name=local_site_name)

        return (get_user_file_attachment_item_url(user,
                                                  file_attachment,
                                                  local_site_name),
                user_file_attachment_item_mimetype,
                file_attachment)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        file_attachment = self.create_user_file_attachment(
            user,
            with_local_site=with_local_site,
            local_site_name=local_site_name)

        return (get_user_file_attachment_item_url(user,
                                                  file_attachment,
                                                  local_site_name),
                user_file_attachment_item_mimetype,
                {'caption': 'My new caption'},
                file_attachment,
                [])

    def check_put_result(self, user, item_rsp, file_attachment):
        file_attachment = FileAttachment.objects.get(pk=file_attachment.pk)
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(file_attachment.caption, 'My new caption')
        self.assertEqual(file_attachment.user, user)
        self.compare_item(item_rsp, file_attachment)

    def test_put_file_already_exists(self):
        """Testing the PUT users/<username>/file-attachments/<id>/ API
        attaching file to object that already has a file attached to it
        """
        file_attachment = self.create_user_file_attachment(
            self.user,
            has_file=True,
            orig_filename='Trophy1.png',
            mimetype='image/png')

        with open(self.get_sample_image_filename(), 'rb') as f:
            self.assertTrue(f)
            rsp = self.api_put(
                get_user_file_attachment_item_url(self.user, file_attachment),
                {
                    'caption': 'My new caption.',
                    'path': f,
                },
                expected_status=409)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DUPLICATE_ITEM.code)
