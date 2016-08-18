from __future__ import unicode_literals

import os

from django.utils import six
from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard import scmtools
from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (diff_item_mimetype,
                                                filediff_item_mimetype,
                                                filediff_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import ExtraDataItemMixin
from reviewboard.webapi.tests.urls import (get_diff_list_url,
                                           get_draft_filediff_item_url,
                                           get_draft_filediff_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the DraftFileDiffResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/draft/diffs/<revision>/files/'
    resource = resources.draft_filediff

    def compare_item(self, item_rsp, filediff):
        self.assertEqual(item_rsp['id'], filediff.pk)
        self.assertEqual(item_rsp['source_file'], filediff.source_file)
        self.assertEqual(item_rsp['extra_data'], filediff.extra_data)

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

        self.api_get(
            get_draft_filediff_list_url(diffset, review_request),
            expected_status=403)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, BaseWebAPITestCase):
    """Testing the DraftFileDiffResource item APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/draft/diffs/<revision>/files/<id>/'
    resource = resources.draft_filediff
    test_http_methods = ('DELETE', 'GET', 'PUT')

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
        self.assertEqual(item_rsp['extra_data'], filediff.extra_data)

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

        self.api_get(
            get_draft_filediff_item_url(filediff, review_request),
            expected_status=403)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            submitter=user,
            with_local_site=with_local_site,
            create_repository=True)
        diffset = self.create_diffset(review_request, draft=True)
        filediff = self.create_filediff(diffset)

        return (get_draft_filediff_item_url(filediff, review_request,
                                            local_site_name),
                filediff_item_mimetype,
                {},
                filediff,
                [])

    def check_put_result(self, user, item_rsp, filediff):
        filediff = FileDiff.objects.get(pk=filediff.pk)
        self.compare_item(item_rsp, filediff)

    def test_put_with_new_file_and_dest_attachment_file(self):
        """Testing the PUT review-requests/<id>/diffs/<id>/files/<id>/ API
        with new file and dest_attachment_file
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata', 'git_binary_image_new.diff')

        with open(diff_filename, 'r') as f:
            rsp = self.api_post(
                get_diff_list_url(review_request),
                {
                    'path': f,
                    'base_commit_id': '1234',
                },
                expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        filediffs = diffset.files.all()

        self.assertEqual(len(filediffs), 1)
        filediff = filediffs[0]
        self.assertEqual(filediff.source_file, 'logo.png')

        with open(self.get_sample_image_filename(), 'r') as f:
            rsp = self.api_put(
                get_draft_filediff_item_url(filediff, review_request) +
                '?expand=dest_attachment',
                {
                    'dest_attachment_file': f,
                },
                expected_mimetype=filediff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('dest_attachment', rsp['file'])

        attachment = FileAttachment.objects.get(
            pk=rsp['file']['dest_attachment']['id'])

        self.assertTrue(attachment.is_from_diff)
        self.assertEqual(attachment.orig_filename, 'logo.png')
        self.assertEqual(attachment.added_in_filediff, filediff)
        self.assertEqual(attachment.repo_path, None)
        self.assertEqual(attachment.repo_revision, None)
        self.assertEqual(attachment.repository, None)

    def test_put_with_modified_file_and_dest_attachment_file(self):
        """Testing the PUT review-requests/<id>/diffs/<id>/files/<id>/ API
        with modified file and dest_attachment_file
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata',
                                     'git_binary_image_modified.diff')

        with open(diff_filename, 'r') as f:
            rsp = self.api_post(
                get_diff_list_url(review_request),
                {
                    'path': f,
                    'base_commit_id': '1234',
                },
                expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        filediffs = diffset.files.all()

        self.assertEqual(len(filediffs), 1)
        filediff = filediffs[0]
        self.assertEqual(filediff.source_file, 'logo.png')

        with open(self.get_sample_image_filename(), 'r') as f:
            rsp = self.api_put(
                get_draft_filediff_item_url(filediff, review_request) +
                '?expand=dest_attachment',
                {
                    'dest_attachment_file': f,
                },
                expected_mimetype=filediff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('dest_attachment', rsp['file'])

        attachment = FileAttachment.objects.get(
            pk=rsp['file']['dest_attachment']['id'])

        self.assertTrue(attachment.is_from_diff)
        self.assertEqual(attachment.orig_filename, 'logo.png')
        self.assertEqual(attachment.added_in_filediff, None)
        self.assertEqual(attachment.repo_path, 'logo.png')
        self.assertEqual(attachment.repo_revision, '86b520d')
        self.assertEqual(attachment.repository, review_request.repository)

    def test_put_second_dest_attachment_file_disallowed(self):
        """Testing the PUT review-requests/<id>/diffs/<id>/files/<id>/ API
        disallows setting dest_attachment_file twice
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)

        diff_filename = os.path.join(os.path.dirname(scmtools.__file__),
                                     'testdata',
                                     'git_binary_image_modified.diff')

        with open(diff_filename, 'r') as f:
            rsp = self.api_post(
                get_diff_list_url(review_request),
                {
                    'path': f,
                    'base_commit_id': '1234',
                },
                expected_mimetype=diff_item_mimetype)

        diffset = DiffSet.objects.get(pk=rsp['diff']['id'])
        filediff = diffset.files.all()[0]

        url = get_draft_filediff_item_url(filediff, review_request)
        trophy_filename = self.get_sample_image_filename()

        with open(trophy_filename, 'r') as f:
            self.api_put(
                url,
                {
                    'dest_attachment_file': f,
                },
                expected_mimetype=filediff_item_mimetype)

        with open(trophy_filename, 'r') as f:
            rsp = self.api_put(
                url,
                {
                    'dest_attachment_file': f,
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
            self.assertIn('fields', rsp)
            self.assertIn('dest_attachment_file', rsp['fields'])
